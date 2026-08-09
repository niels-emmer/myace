"""Documentation cache verifier — periodically refreshes framework documentation."""

import hashlib
import logging
from datetime import UTC, datetime, timedelta

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.models.doc_cache import DocCacheEntry

logger = logging.getLogger(__name__)

# Framework documentation sources
FRAMEWORK_DOCS: dict[str, list[dict[str, str]]] = {
    "claude-code": [
        {"url": "https://docs.anthropic.com/en/docs/claude-code/overview", "type": "overview"},
        {"url": "https://docs.anthropic.com/en/docs/claude-code/settings", "type": "schema"},
    ],
    "opencode": [
        {"url": "https://github.com/opencode-ai/opencode", "type": "overview"},
    ],
    "cursor": [
        {"url": "https://docs.cursor.com/get-started/overview", "type": "overview"},
        {"url": "https://docs.cursor.com/guides/rules", "type": "schema"},
    ],
}


async def refresh_framework_docs(session: AsyncSession) -> dict[str, int]:
    """
    Refresh all cached framework documentation that has expired.
    Returns a dict of {framework: count_updated}.
    """
    results: dict[str, int] = {}

    for framework, sources in FRAMEWORK_DOCS.items():
        updated = 0
        for source in sources:
            try:
                changed = await _refresh_single_source(session, framework, source)
                if changed:
                    updated += 1
            except Exception as e:
                logger.warning("Failed to refresh %s doc %s: %s", framework, source["url"], e)
        results[framework] = updated

    return results


async def _refresh_single_source(
    session: AsyncSession,
    framework: str,
    source: dict[str, str],
) -> bool:
    """Refresh a single documentation source if expired or missing."""
    url = source["url"]
    content_type = source["type"]

    # Check if we have a valid cached entry
    result = await session.execute(
        select(DocCacheEntry).where(
            DocCacheEntry.framework == framework,
            DocCacheEntry.url == url,
            DocCacheEntry.content_type == content_type,
        )
    )
    existing = result.scalar_one_or_none()

    if existing and existing.expires_at > datetime.now(UTC):
        return False  # Still valid

    # Fetch fresh content
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

    content = response.text
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    if existing and existing.content_hash == content_hash:
        # Content unchanged, just update expiry
        existing.expires_at = datetime.now(UTC) + timedelta(
            days=settings.doc_cache_ttl_days
        )
        existing.fetched_at = datetime.now(UTC)
        await session.commit()
        return True

    # Parse with BeautifulSoup for structured storage
    soup = BeautifulSoup(content, "html.parser")
    # Extract main content, strip scripts/styles
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    clean_text = soup.get_text(separator="\n", strip=True)

    if existing:
        # Update existing
        existing.content = clean_text
        existing.content_hash = content_hash
        existing.fetched_at = datetime.now(UTC)
        existing.expires_at = datetime.now(UTC) + timedelta(
            days=settings.doc_cache_ttl_days
        )
    else:
        # Create new
        entry = DocCacheEntry(
            framework=framework,
            url=url,
            content_hash=content_hash,
            content=clean_text,
            content_type=content_type,
            ttl_days=settings.doc_cache_ttl_days,
            fetched_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(
                days=settings.doc_cache_ttl_days
            ),
        )
        session.add(entry)

    await session.commit()
    return True


async def get_cached_doc(
    session: AsyncSession,
    framework: str,
    content_type: str | None = None,
) -> DocCacheEntry | None:
    """Get a cached documentation entry, returning None if expired."""
    query = select(DocCacheEntry).where(
        DocCacheEntry.framework == framework,
        DocCacheEntry.expires_at > datetime.now(UTC),
    )
    if content_type:
        query = query.where(DocCacheEntry.content_type == content_type)

    result = await session.execute(query)
    return result.scalar_one_or_none()
