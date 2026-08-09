"""Documentation cache routes — manage cached framework docs."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.models.doc_cache import DocCacheEntry

router = APIRouter()


@router.get("")
async def list_cache_entries(
    framework: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """List cached documentation entries."""
    query = select(DocCacheEntry)
    if framework:
        query = query.where(DocCacheEntry.framework == framework)

    result = await session.execute(query)
    entries = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "framework": e.framework,
            "url": e.url,
            "content_type": e.content_type,
            "fetched_at": e.fetched_at.isoformat(),
            "expires_at": e.expires_at.isoformat(),
        }
        for e in entries
    ]


@router.delete("/{entry_id}")
async def delete_cache_entry(
    entry_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete a cached documentation entry."""
    result = await session.execute(
        select(DocCacheEntry).where(DocCacheEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Cache entry not found")

    await session.delete(entry)
    await session.commit()
    return {"message": "Cache entry deleted"}
