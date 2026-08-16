"""Collection ratings — 1-5 stars, one per user per collection."""

import uuid

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


async def _recompute_rating(session: AsyncSession, collection: Collection) -> None:
    """Recompute the denormalized avg_rating/rating_count cache on
    Collection from the CollectionRating rows (the source of truth)."""
    result = await session.execute(
        select(func.avg(CollectionRating.stars), func.count(CollectionRating.id)).where(
            CollectionRating.collection_id == collection.id
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

    my_result = await session.execute(
        select(CollectionRating).where(
            CollectionRating.collection_id == collection_id,
            CollectionRating.user_id == current_user.id,
        )
    )
    mine = my_result.scalar_one_or_none()

    return CollectionRatingRead(
        avg_rating=collection.avg_rating,
        rating_count=collection.rating_count,
        my_rating=mine.stars if mine else None,
    )


@router.put("/{collection_id}/rating", response_model=CollectionRatingRead)
async def rate_collection(
    collection_id: uuid.UUID,
    request: RatingRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Upsert the caller's rating for a collection. Self-rating is blocked;
    only approved (public) collections can be rated."""
    if request.stars < 1 or request.stars > 5:
        raise HTTPException(status_code=422, detail="stars must be between 1 and 5")

    collection = await _get_approved_collection_or_404(session, collection_id)
    if collection.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot rate your own collection")

    result = await session.execute(
        select(CollectionRating).where(
            CollectionRating.collection_id == collection_id,
            CollectionRating.user_id == current_user.id,
        )
    )
    rating = result.scalar_one_or_none()
    if rating:
        rating.stars = request.stars
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
    """Remove the caller's own rating, if any."""
    collection = await _get_approved_collection_or_404(session, collection_id)

    result = await session.execute(
        select(CollectionRating).where(
            CollectionRating.collection_id == collection_id,
            CollectionRating.user_id == current_user.id,
        )
    )
    rating = result.scalar_one_or_none()
    if rating:
        await session.delete(rating)
        await session.commit()
        await _recompute_rating(session, collection)
        await session.refresh(collection)

    return CollectionRatingRead(
        avg_rating=collection.avg_rating, rating_count=collection.rating_count, my_rating=None
    )
