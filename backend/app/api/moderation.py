"""Community moderation queue — submit/approve/deny for collection publishing.

Every route here is gated by `require_moderator_or_admin`, not
`authorize_access` — the latter's owner-bypass would let a collection owner
approve their own submission, which is exactly what the moderation state
machine (see app.models.collection) must prevent. Owners never self-approve.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.core.deps import require_moderator_or_admin
from app.models.collection import Collection, CollectionRead
from app.models.user import User
from app.services.effective_settings import get_effective_smtp_config
from app.services.email import (
    EmailSendError,
    build_moderation_approved_email,
    build_moderation_denied_email,
    send_email,
)

logger = logging.getLogger("myace")

router = APIRouter()


class ModerationQueueItem(CollectionRead):
    """CollectionRead plus a minimal owner summary — the queue UI needs to
    show who submitted each collection, which the bare owner_id doesn't
    give it without a second round-trip per row."""
    owner_email: str
    owner_display_name: str


async def _get_submitted_collection_or_404(
    session: AsyncSession, collection_id: uuid.UUID
) -> Collection:
    result = await session.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection or collection.moderation_status != "submitted":
        raise HTTPException(status_code=404, detail="No submitted collection with that ID")
    return collection


async def _notify_owner(
    session: AsyncSession, collection: Collection, subject_body: tuple[str, str]
) -> None:
    """Best-effort email to the submitter — never lets a send failure roll
    back the approve/deny state change (matches the password-reset pattern
    in app.api.auth.forgot_password)."""
    owner_result = await session.execute(select(User).where(User.id == collection.owner_id))
    owner = owner_result.scalar_one_or_none()
    if not owner or not owner.email:
        return

    subject, body = subject_body
    try:
        config = await get_effective_smtp_config(session)
        if config.enabled:
            await send_email(config=config, to=owner.email, subject=subject, text_body=body)
    except EmailSendError:
        logger.exception("Failed to send moderation-decision email to a collection owner.")


def _queue_order_by(sort: Literal["rating", "downloads", "alpha", "submitted_at"]):
    if sort == "rating":
        return (Collection.avg_rating.desc(),)
    if sort == "downloads":
        return (Collection.download_count.desc(),)
    if sort == "alpha":
        return (Collection.name.asc(),)
    return (Collection.submitted_at.asc(),)


@router.get("/queue", response_model=list[ModerationQueueItem])
async def get_moderation_queue(
    sort: Literal["rating", "downloads", "alpha", "submitted_at"] = "submitted_at",
    current_user: User = Depends(require_moderator_or_admin),
    session: AsyncSession = Depends(get_session),
):
    """List collections awaiting review. Defaults to oldest-submitted-first
    (the sane default for a review queue), but accepts the same rating/
    downloads/alpha values as the community listing as an override."""
    result = await session.execute(
        select(Collection, User.email, User.display_name)
        .join(User, User.id == Collection.owner_id)
        .where(Collection.moderation_status == "submitted")
        .order_by(*_queue_order_by(sort))
    )
    return [
        ModerationQueueItem(**collection.model_dump(), owner_email=email, owner_display_name=name)
        for collection, email, name in result.all()
    ]


@router.post("/{collection_id}/approve", response_model=CollectionRead)
async def approve_collection(
    collection_id: uuid.UUID,
    current_user: User = Depends(require_moderator_or_admin),
    session: AsyncSession = Depends(get_session),
):
    """Approve a submitted collection — the only path that flips
    published/visibility to public."""
    collection = await _get_submitted_collection_or_404(session, collection_id)

    collection.moderation_status = "approved"
    collection.published = True
    collection.visibility = "public"
    collection.moderated_by = current_user.id
    collection.moderated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(collection)

    await _notify_owner(session, collection, build_moderation_approved_email(collection.name))
    return collection


class DenyRequest(BaseModel):
    """Body for POST /moderation/{collection_id}/deny."""
    reason: str


@router.post("/{collection_id}/deny", response_model=CollectionRead)
async def deny_collection(
    collection_id: uuid.UUID,
    request: DenyRequest,
    current_user: User = Depends(require_moderator_or_admin),
    session: AsyncSession = Depends(get_session),
):
    """Deny a submitted collection. Leaves published=False; the owner can
    edit and resubmit (moderation_status returns to 'submitted')."""
    if not request.reason.strip():
        raise HTTPException(status_code=422, detail="reason is required")

    collection = await _get_submitted_collection_or_404(session, collection_id)

    collection.moderation_status = "denied"
    collection.moderation_reason = request.reason.strip()
    collection.moderated_by = current_user.id
    collection.moderated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(collection)

    await _notify_owner(
        session, collection,
        build_moderation_denied_email(collection.name, collection.moderation_reason),
    )
    return collection


class CollectionMetaUpdate(BaseModel):
    """Body for PATCH /moderation/{collection_id}/meta — metadata only,
    never git_url/git_branch/artifact content."""
    name: str | None = None
    description: str | None = None
    category: str | None = None


@router.patch("/{collection_id}/meta", response_model=CollectionRead)
async def update_collection_meta(
    collection_id: uuid.UUID,
    request: CollectionMetaUpdate,
    current_user: User = Depends(require_moderator_or_admin),
    session: AsyncSession = Depends(get_session),
):
    """Let a moderator/admin fix a community collection's name, description,
    or category — regardless of moderation_status, so a typo can be fixed
    on an already-approved collection too, not just mid-review. The
    collection's own owner (if not also a moderator/admin) cannot use this
    endpoint; they edit via their own existing PATCH /collections/{id}."""
    result = await session.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    if request.name is not None:
        collection.name = request.name
    if request.description is not None:
        collection.description = request.description
    if request.category is not None:
        collection.category = request.category
    collection.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(collection)

    return collection
