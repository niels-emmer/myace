"""Collection comments — one thread per collection, soft-deletable."""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.collection import Collection
from app.models.collection_comment import (
    CollectionComment,
    CollectionCommentCreate,
    CollectionCommentRead,
)
from app.models.user import User
from app.services.effective_settings import get_effective_smtp_config
from app.services.email import EmailSendError, build_comment_notification_email, send_email

logger = logging.getLogger("myace")

router = APIRouter()


async def _get_approved_collection_or_404(
    session: AsyncSession, collection_id: uuid.UUID
) -> Collection:
    result = await session.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection or collection.moderation_status != "approved":
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


async def _notify_owner_of_comment(
    session: AsyncSession, collection: Collection, commenter: User
) -> None:
    """Best-effort immediate notification — never blocks comment creation
    on a send failure. Gated by the owner's notify_on_comment preference
    (comments are low-volume, so this is sent immediately rather than
    batched like the download digest)."""
    owner_result = await session.execute(select(User).where(User.id == collection.owner_id))
    owner = owner_result.scalar_one_or_none()
    if not owner or not owner.email or not owner.notify_on_comment:
        return

    subject, body = build_comment_notification_email(collection.name, commenter.display_name)
    try:
        config = await get_effective_smtp_config(session)
        if config.enabled:
            await send_email(config=config, to=owner.email, subject=subject, text_body=body)
    except EmailSendError:
        logger.exception("Failed to send comment-notification email to a collection owner.")


def _comment_to_read(comment: CollectionComment, author_display_name: str) -> CollectionCommentRead:
    return CollectionCommentRead(
        id=comment.id,
        collection_id=comment.collection_id,
        user_id=comment.user_id,
        author_display_name=author_display_name,
        body=comment.body,
        created_at=comment.created_at,
    )


@router.get("/{collection_id}/comments", response_model=list[CollectionCommentRead])
async def list_comments(
    collection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List non-deleted comments on a collection, newest first."""
    await _get_approved_collection_or_404(session, collection_id)

    result = await session.execute(
        select(CollectionComment, User.display_name)
        .join(User, User.id == CollectionComment.user_id)
        .where(
            CollectionComment.collection_id == collection_id,
            CollectionComment.deleted_at == None,  # noqa: E711
        )
        .order_by(CollectionComment.created_at.desc())
    )
    return [_comment_to_read(comment, name) for comment, name in result.all()]


@router.post("/{collection_id}/comments", response_model=CollectionCommentRead, status_code=201)
async def create_comment(
    collection_id: uuid.UUID,
    request: CollectionCommentCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Add a comment to an approved (public) collection."""
    collection = await _get_approved_collection_or_404(session, collection_id)

    comment = CollectionComment(
        collection_id=collection_id, user_id=current_user.id, body=request.body,
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    await _notify_owner_of_comment(session, collection, current_user)

    return _comment_to_read(comment, current_user.display_name)


@router.delete("/{collection_id}/comments/{comment_id}")
async def delete_comment(
    collection_id: uuid.UUID,
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Soft-delete a comment. Allowed for the comment's own author, the
    collection owner, or a moderator/admin."""
    result = await session.execute(
        select(CollectionComment).where(
            CollectionComment.id == comment_id,
            CollectionComment.collection_id == collection_id,
            CollectionComment.deleted_at == None,  # noqa: E711
        )
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    collection_result = await session.execute(
        select(Collection).where(Collection.id == collection_id)
    )
    collection = collection_result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    is_author = comment.user_id == current_user.id
    is_owner = collection.owner_id == current_user.id
    is_moderator = current_user.role in ("moderator", "admin")
    if not (is_author or is_owner or is_moderator):
        raise HTTPException(status_code=403, detail="Not allowed to delete this comment")

    comment.deleted_at = datetime.now(UTC)
    session.add(comment)
    await session.commit()

    return {"message": "Comment deleted"}
