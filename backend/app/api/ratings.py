"""Collection ratings — 1-5 stars, one per user per collection."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.collection import Collection
from app.models.collection_rating import CollectionRating, CollectionRatingRead
from app.models.user import User

router = APIRouter()


async def _get_approved_collection_or_404(
    session: AsyncSession, collection_id: uuid.UUID
) -> Collection:
    result = await session.execute(select(Collection).where(Collection.id == collection_id))
    collection = result.scalar_one_or_none()
    if not collection or collection.moderation_status != "approved":
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


async def _get_rating_row(
    session: AsyncSession, collection_id: uuid.UUID, user_id: uuid.UUID
) -> CollectionRating | None:
    """Look up a rating row regardless of deleted_at — the unique
    constraint on (collection_id, user_id) isn't scoped to live rows, so a
    soft-deleted row must be found and revived rather than colliding with
    an INSERT of a fresh one."""
    result = await session.execute(
        select(CollectionRating).where(
            CollectionRating.collection_id == collection_id,
            CollectionRating.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def _recompute_rating(session: AsyncSession, collection: Collection) -> None:
    """Recompute the denormalized avg_rating/rating_count cache on
    Collection from the live CollectionRating rows (the source of truth)."""
    result = await session.execute(
        select(func.avg(CollectionRating.stars), func.count(CollectionRating.id)).where(
            CollectionRating.collection_id == collection.id,
            CollectionRating.deleted_at == None,  # noqa: E711
        )
    )
    avg_stars, count = result.one()
    collection.avg_rating = round(float(avg_stars), 2) if avg_stars is not None else 0.0
    collection.rating_count = count
    session.add(collection)
    await session.commit()


class RatingRequest(BaseModel):
    """Body for PUT /collections/{collection_id}/rating."""
    stars: int


@router.get("/{collection_id}/rating", response_model=CollectionRatingRead)
async def get_rating(
    collection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return the aggregate rating plus the caller's own rating, if any."""
    collection = await _get_approved_collection_or_404(session, collection_id)

    mine = await _get_rating_row(session, collection_id, current_user.id)
    my_rating = mine.stars if mine and mine.deleted_at is None else None

    return CollectionRatingRead(
        avg_rating=collection.avg_rating,
        rating_count=collection.rating_count,
        my_rating=my_rating,
    )


@router.put("/{collection_id}/rating", response_model=CollectionRatingRead)
async def rate_collection(
    collection_id: uuid.UUID,
    request: RatingRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Upsert the caller's rating for a collection. Self-rating is blocked;
    only approved (public) collections can be rated. Reviving a
    previously-soft-deleted row rather than inserting a new one, since the
    unique constraint on (collection_id, user_id) isn't scoped to live
    rows only."""
    if request.stars < 1 or request.stars > 5:
        raise HTTPException(status_code=422, detail="stars must be between 1 and 5")

    collection = await _get_approved_collection_or_404(session, collection_id)
    if collection.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot rate your own collection")

    rating = await _get_rating_row(session, collection_id, current_user.id)
    if rating:
        rating.stars = request.stars
        rating.deleted_at = None
    else:
        rating = CollectionRating(
            collection_id=collection_id, user_id=current_user.id, stars=request.stars
        )
    session.add(rating)
    await session.commit()

    await _recompute_rating(session, collection)
    await session.refresh(collection)

    return CollectionRatingRead(
        avg_rating=collection.avg_rating, rating_count=collection.rating_count,
        my_rating=request.stars,
    )


@router.delete("/{collection_id}/rating", response_model=CollectionRatingRead)
async def delete_rating(
    collection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Soft-delete the caller's own rating, if any (rule 15 — never
    hard-delete)."""
    collection = await _get_approved_collection_or_404(session, collection_id)

    rating = await _get_rating_row(session, collection_id, current_user.id)
    if rating and rating.deleted_at is None:
        rating.deleted_at = datetime.now(UTC)
        session.add(rating)
        await session.commit()
        await _recompute_rating(session, collection)
        await session.refresh(collection)

    return CollectionRatingRead(
        avg_rating=collection.avg_rating, rating_count=collection.rating_count, my_rating=None
    )
