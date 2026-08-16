"""Collection freshness queue — surfaces community collections whose
manual verification is missing or has expired.

Mounted at the same `/api/v1/admin` prefix as `app.api.admin`, but gated
by `require_moderator_or_admin` rather than `require_admin` — reviewing
and verifying community content is squarely within a moderator's existing
scope (AGENTS.md rule 30), the same reasoning that already applies to the
moderation queue itself. Kept in a separate router file rather than folded
into `admin.py` so that file's routes stay uniformly `require_admin`-gated
— no route there mixes access levels, and no route here grants any
`require_admin`-only capability (user management, system settings,
adapter toggles).
"""

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.database import get_session
from app.core.deps import require_moderator_or_admin
from app.models.collection import Collection, CollectionRead
from app.models.user import User

router = APIRouter()


def freshness_threshold_date() -> date:
    """The cutoff below which last_verified_at counts as expired."""
    return date.today() - timedelta(days=settings.collection_freshness_threshold_days)


def stale_collections_query() -> Any:
    """Shared query for "approved, active community collections whose
    freshness verification is missing or older than the configured
    threshold" — used by both GET /admin/freshness-queue below and
    app/scripts/check_collection_freshness.py, so the two never drift
    apart on what counts as stale.

    The `type: ignore` comments below are a genuine stub gap, not sloppy
    typing: SQLAlchemy's mypy-visible comparison overloads cover
    `datetime`-typed nullable columns fine (see `Artifact.deleted_at ==
    None` elsewhere in this codebase, which mypy accepts) but not bare
    `date`-typed ones — `Collection.last_verified_at: date | None`
    resolves as a plain Python `date | None` rather than a SQLAlchemy
    `ColumnElement`, so `<` and the `or_()`-wrapped `== None` both need an
    ignore even though they're correct at runtime (verified by
    tests/test_freshness.py and tests/test_check_collection_freshness.py).
    """
    threshold_date = freshness_threshold_date()
    return select(Collection).where(
        Collection.moderation_status == "approved",
        Collection.is_active == True,
        or_(
            Collection.last_verified_at == None,  # type: ignore[arg-type]
            Collection.last_verified_at < threshold_date,  # type: ignore[arg-type,operator]
        ),
    )


@router.get("/freshness-queue", response_model=list[CollectionRead])
async def get_freshness_queue(
    current_user: User = Depends(require_moderator_or_admin),
    session: AsyncSession = Depends(get_session),
) -> list[Collection]:
    """List approved, active community collections whose freshness
    verification is missing or older than the configured threshold
    (default 6 months — settings.collection_freshness_threshold_days),
    never-verified first, then oldest-verified first.
    """
    query = stale_collections_query().order_by(
        Collection.last_verified_at.asc().nulls_first()  # type: ignore[union-attr]
    )
    result = await session.execute(query)
    return list(result.scalars().all())
