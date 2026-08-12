"""Tests for community collection endpoints (publish, list, import)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact
from app.models.collection import Collection


async def _register(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "community-test@example.com",
            "password": "password123",
            "display_name": "Community Test",
        },
    )
    assert res.status_code == 201


async def _create_collection(
    client: AsyncClient,
    db_session: AsyncSession,
    name: str = "test-collection",
    collection_type: str = "base",
    visibility: str = "private",
) -> str:
    res = await client.post(
        "/api/v1/collections",
        json={
            "name": name,
            "git_url": "https://example.com/repo.git",
            "collection_type": collection_type,
            "visibility": visibility,
        },
    )
    assert res.status_code == 201
    collection_id = res.json()["id"]

    # Add an artifact so the collection has content
    db_session.add(
        Artifact(
            collection_id=uuid.UUID(collection_id),
            artifact_type="rule",
            name="test-rule",
            priority=80,
            body="Always use type annotations.",
            file_path="rules/test-rule.md",
        )
    )
    await db_session.commit()

    return collection_id


@pytest.mark.asyncio
async def test_list_community_collections_empty(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Listing community collections when none are published returns empty list."""
    await _register(async_client)
    res = await async_client.get("/api/v1/collections/community")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_list_community_collections_with_published(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Published collections appear in the community listing."""
    await _register(async_client)
    collection_id = await _create_collection(async_client, db_session)

    # Mark the collection as published
    coll = await db_session.get(Collection, uuid.UUID(collection_id))
    assert coll is not None
    coll.published = True
    coll.category = "python"
    await db_session.commit()

    res = await async_client.get("/api/v1/collections/community")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == collection_id
    assert data[0]["published"] is True
    assert data[0]["category"] == "python"


@pytest.mark.asyncio
async def test_list_community_collections_filters_by_category(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Community listing can be filtered by category."""
    await _register(async_client)
    c1 = await _create_collection(async_client, db_session, name="python-coll")
    c2 = await _create_collection(async_client, db_session, name="iac-coll")

    coll1 = await db_session.get(Collection, uuid.UUID(c1))
    coll1.published = True
    coll1.category = "python"
    coll2 = await db_session.get(Collection, uuid.UUID(c2))
    coll2.published = True
    coll2.category = "iac"
    await db_session.commit()

    res = await async_client.get("/api/v1/collections/community?category=python")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["category"] == "python"


@pytest.mark.asyncio
async def test_list_top_community_collections(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Top community collections are ordered by download_count."""
    await _register(async_client)
    c1 = await _create_collection(async_client, db_session, name="popular")
    c2 = await _create_collection(async_client, db_session, name="less-popular")

    coll1 = await db_session.get(Collection, uuid.UUID(c1))
    coll1.published = True
    coll1.download_count = 100
    coll2 = await db_session.get(Collection, uuid.UUID(c2))
    coll2.published = True
    coll2.download_count = 10
    await db_session.commit()

    res = await async_client.get("/api/v1/collections/community/top?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert data[0]["id"] == c1  # Most downloaded first
    assert data[0]["download_count"] == 100


@pytest.mark.asyncio
async def test_list_community_categories(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Categories endpoint returns distinct categories from published collections."""
    await _register(async_client)
    c1 = await _create_collection(async_client, db_session, name="python-coll")
    c2 = await _create_collection(async_client, db_session, name="iac-coll")

    coll1 = await db_session.get(Collection, uuid.UUID(c1))
    coll1.published = True
    coll1.category = "python"
    coll2 = await db_session.get(Collection, uuid.UUID(c2))
    coll2.published = True
    coll2.category = "iac"
    await db_session.commit()

    res = await async_client.get("/api/v1/collections/community/categories")
    assert res.status_code == 200
    categories = res.json()
    assert "python" in categories
    assert "iac" in categories


@pytest.mark.asyncio
async def test_import_community_collection(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Importing a published community collection creates a user-owned copy."""
    await _register(async_client)
    collection_id = await _create_collection(async_client, db_session)

    coll = await db_session.get(Collection, uuid.UUID(collection_id))
    coll.published = True
    coll.visibility = "public"
    await db_session.commit()

    res = await async_client.post(f"/api/v1/collections/{collection_id}/import")
    assert res.status_code == 201
    data = res.json()
    assert data["collection_name"] == "test-collection (imported)"
    assert data["artifacts_imported"] == 1

    # Verify download count was incremented
    await db_session.refresh(coll)
    assert coll.download_count == 1


@pytest.mark.asyncio
async def test_import_non_published_collection_fails(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Importing a non-published collection returns 400."""
    await _register(async_client)
    collection_id = await _create_collection(async_client, db_session)

    res = await async_client.post(f"/api/v1/collections/{collection_id}/import")
    assert res.status_code == 400
    assert "published" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_publish_is_immediate_and_self_serve(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Publishing sets published=True and visibility=public on the caller's own
    row immediately — no admin approval step, no GitHub round-trip."""
    await _register(async_client)
    collection_id = await _create_collection(async_client, db_session, visibility="private")

    res = await async_client.post(
        f"/api/v1/collections/{collection_id}/publish",
        json={
            "category": "python",
            "publish_name": "Published Display Name",
            "publish_description": "A public-facing description.",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["published"] is True
    assert data["visibility"] == "public"
    assert data["category"] == "python"
    assert data["name"] == "Published Display Name"
    assert data["description"] == "A public-facing description."

    # Immediately visible in the community listing, no extra step.
    res = await async_client.get("/api/v1/collections/community")
    assert res.status_code == 200
    assert any(c["id"] == collection_id for c in res.json())


@pytest.mark.asyncio
async def test_publish_requires_enabled_artifacts(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Publishing a collection with no enabled artifacts returns 400."""
    await _register(async_client)
    res = await async_client.post(
        "/api/v1/collections",
        json={
            "name": "empty-collection",
            "git_url": "https://example.com/repo.git",
            "collection_type": "base",
            "visibility": "private",
        },
    )
    assert res.status_code == 201
    collection_id = res.json()["id"]

    res = await async_client.post(
        f"/api/v1/collections/{collection_id}/publish",
        json={"category": "python"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_publish_requires_category(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Publishing without a category returns 422."""
    await _register(async_client)
    collection_id = await _create_collection(async_client, db_session)

    res = await async_client.post(
        f"/api/v1/collections/{collection_id}/publish",
        json={"category": ""},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_publish_requires_auth(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Publishing without authentication returns 401."""
    res = await async_client.post(
        "/api/v1/collections/00000000-0000-0000-0000-000000000000/publish",
        json={"category": "python"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_community_endpoints_require_auth(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Community listing endpoints require authentication."""
    res = await async_client.get("/api/v1/collections/community")
    assert res.status_code == 401

    res = await async_client.get("/api/v1/collections/community/top")
    assert res.status_code == 401

    res = await async_client.get("/api/v1/collections/community/categories")
    assert res.status_code == 401

    res = await async_client.post(
        "/api/v1/collections/00000000-0000-0000-0000-000000000000/import"
    )
    assert res.status_code == 401
