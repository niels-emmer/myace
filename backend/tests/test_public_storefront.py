"""Public storefront reads (ADR-0014) — the anonymous allowlist.

Pins the security boundary, not just the happy path:
- the five anonymous read routes work without a session,
- a neighbouring authenticated route still 401s,
- only approved + published + active packs are visible,
- no write path is reachable anonymously, and
- the per-IP rate limit actually fires.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ratelimit import storefront_limiter
from app.models.artifact import Artifact
from app.models.collection import Collection


async def _seed_pack(
    session: AsyncSession,
    *,
    published: bool = True,
    moderation_status: str = "approved",
    is_active: bool = True,
    name: str = "Public Pack",
) -> Collection:
    collection = Collection(
        owner_id=uuid.uuid4(),
        name=name,
        description="A public test pack",
        git_url="https://example.com/pack.git",
        collection_type="base",
        visibility="public",
        is_active=is_active,
        published=published,
        moderation_status=moderation_status,
        category="Testing",
    )
    session.add(collection)
    await session.commit()
    await session.refresh(collection)
    return collection


async def _seed_artifact(
    session: AsyncSession, collection_id: uuid.UUID, name: str, *, enabled: bool = True
) -> Artifact:
    artifact = Artifact(
        collection_id=collection_id,
        artifact_type="rule",
        name=name,
        priority=50,
        body="A rule body.",
        file_path="AGENTS.md",
        is_enabled=enabled,
    )
    session.add(artifact)
    await session.commit()
    await session.refresh(artifact)
    return artifact


@pytest.mark.asyncio
async def test_anonymous_can_read_the_storefront_lists(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    public = await _seed_pack(db_session, name="Public Pack")
    await _seed_pack(
        db_session,
        name="Draft Pack",
        published=False,
        moderation_status="draft",
    )
    await _seed_pack(
        db_session,
        name="Denied Pack",
        published=False,
        moderation_status="denied",
    )
    await _seed_pack(
        db_session,
        name="Inactive Pack",
        published=False,
        moderation_status="approved",
        is_active=False,
    )

    listed = await async_client.get("/api/v1/collections/community")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [str(public.id)]

    top = await async_client.get("/api/v1/collections/community/top")
    assert top.status_code == 200
    assert [item["id"] for item in top.json()] == [str(public.id)]

    categories = await async_client.get("/api/v1/collections/community/categories")
    assert categories.status_code == 200
    assert categories.json() == ["Testing"]


@pytest.mark.asyncio
async def test_anonymous_can_read_one_public_pack_and_its_contents(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    public = await _seed_pack(db_session, name="Readable Pack")
    await _seed_artifact(db_session, public.id, "Visible rule")
    await _seed_artifact(db_session, public.id, "Disabled rule", enabled=False)

    detail = await async_client.get(f"/api/v1/collections/community/{public.id}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "Readable Pack"

    contents = await async_client.get(
        f"/api/v1/collections/community/{public.id}/artifacts"
    )
    assert contents.status_code == 200
    assert [item["name"] for item in contents.json()] == ["Visible rule"]

    filtered = await async_client.get(
        f"/api/v1/collections/community/{public.id}/artifacts?type=skill"
    )
    assert filtered.status_code == 200
    assert filtered.json() == []


@pytest.mark.asyncio
async def test_public_pack_shape_does_not_leak_source_or_moderation_fields(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """The public schema is sanitized, not `CollectionRead` (ADR-0014)."""
    public = await _seed_pack(db_session)
    public.git_url = "https://private.example.com/secret-pack.git"
    public.moderation_reason = "internal moderator note"
    await db_session.commit()

    detail = await async_client.get(f"/api/v1/collections/community/{public.id}")
    assert detail.status_code == 200
    body = detail.json()
    for leaked in ("git_url", "git_branch", "visibility", "moderation_reason", "moderated_by"):
        assert leaked not in body, leaked
    assert body["license"] is None
    assert body["moderation_status"] == "approved"

    listed = await async_client.get("/api/v1/collections/community")
    assert listed.status_code == 200
    for leaked in ("git_url", "git_branch", "visibility", "moderation_reason"):
        assert leaked not in listed.json()["items"][0], leaked


@pytest.mark.asyncio
async def test_anonymous_cannot_read_unpublished_packs(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    draft = await _seed_pack(
        db_session, name="Secret Draft", published=False, moderation_status="draft"
    )

    for path in (
        f"/api/v1/collections/community/{draft.id}",
        f"/api/v1/collections/community/{draft.id}/artifacts",
    ):
        res = await async_client.get(path)
        assert res.status_code == 404
        assert res.json()["detail"] == "Collection not found"


@pytest.mark.asyncio
async def test_neighbouring_authenticated_routes_still_require_auth(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """The allowlist is narrow — not a general collections auth change."""
    public = await _seed_pack(db_session)

    for path in (
        "/api/v1/collections",
        f"/api/v1/collections/{public.id}",
        f"/api/v1/collections/{public.id}/artifacts",
        "/api/v1/profiles",
    ):
        res = await async_client.get(path)
        assert res.status_code == 401, path


@pytest.mark.asyncio
async def test_no_write_path_is_reachable_anonymously(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    public = await _seed_pack(db_session)

    use = await async_client.post(f"/api/v1/collections/{public.id}/use")
    assert use.status_code == 401

    publish = await async_client.post(
        f"/api/v1/collections/{public.id}/publish", json={"category": "Testing"}
    )
    assert publish.status_code == 401

    unpublish = await async_client.post(f"/api/v1/collections/{public.id}/unpublish")
    assert unpublish.status_code == 401

    patch = await async_client.patch(
        f"/api/v1/collections/{public.id}", json={"name": "Hijacked"}
    )
    assert patch.status_code == 401

    # And the public URL family has no write routes at all.
    extra = await async_client.post(
        f"/api/v1/collections/community/{public.id}/use"
    )
    assert extra.status_code in (404, 405, 422)


async def _register(client: AsyncClient, email: str) -> None:
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "Storefront Owner"},
    )
    assert res.status_code == 201


@pytest.mark.asyncio
async def test_license_publish_flow_controls_public_visibility(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """PATCH license → publish (submitted) → approve → anonymous read."""
    await _register(async_client, "storefront-owner@example.com")
    created = await async_client.post(
        "/api/v1/collections",
        json={
            "name": "Licensed Pack",
            "git_url": "https://example.com/licensed.git",
            "collection_type": "base",
            "visibility": "private",
        },
    )
    assert created.status_code == 201
    collection_id = created.json()["id"]
    await _seed_artifact(db_session, uuid.UUID(collection_id), "Visible rule")

    patched = await async_client.patch(
        f"/api/v1/collections/{collection_id}",
        json={"license": "MIT", "category": "Testing"},
    )
    assert patched.status_code == 200
    assert patched.json()["license"] == "MIT"

    published = await async_client.post(
        f"/api/v1/collections/{collection_id}/publish",
        json={"category": "Testing"},
    )
    assert published.status_code == 200
    assert published.json()["moderation_status"] == "submitted"

    # Submitted is not public yet.
    hidden = await async_client.get(f"/api/v1/collections/community/{collection_id}")
    assert hidden.status_code == 404

    # Simulate the moderator approval (the only path that sets published).
    collection = await db_session.get(Collection, uuid.UUID(collection_id))
    assert collection is not None
    collection.published = True
    collection.visibility = "public"
    collection.moderation_status = "approved"
    await db_session.commit()

    public = await async_client.get(f"/api/v1/collections/community/{collection_id}")
    assert public.status_code == 200
    assert public.json()["license"] == "MIT"


@pytest.mark.asyncio
async def test_public_reads_create_no_session_cookie(async_client: AsyncClient) -> None:
    res = await async_client.get("/api/v1/collections/community")
    assert res.status_code == 200
    assert res.headers.get("set-cookie") is None


@pytest.mark.asyncio
async def test_public_reads_are_rate_limited(async_client: AsyncClient) -> None:
    """The 121st anonymous read from one IP in a minute is a 429."""
    storefront_limiter.reset()
    storefront_limiter.enabled = True
    try:
        last = None
        for _ in range(121):
            last = await async_client.get("/api/v1/collections/community")
        assert last is not None
        assert last.status_code == 429
        assert last.json()["detail"].startswith("Rate limit exceeded")
    finally:
        storefront_limiter.enabled = False
        storefront_limiter.reset()
