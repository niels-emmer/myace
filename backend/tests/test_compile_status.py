"""Tests for compiled-output hashing (compute_compiled_hash) and the
GET /profiles/{id}/compile-status endpoint."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app as fastapi_app
from app.models.artifact import Artifact
from app.services.compiler import compute_compiled_hash


def test_compute_compiled_hash_is_stable_for_identical_input() -> None:
    files = {"CLAUDE.md": "hello world", "agents/foo.md": "an agent"}
    assert compute_compiled_hash(files) == compute_compiled_hash(dict(files))


def test_compute_compiled_hash_is_stable_regardless_of_dict_order() -> None:
    files_a = {"a.md": "1", "b.md": "2"}
    files_b = {"b.md": "2", "a.md": "1"}
    assert compute_compiled_hash(files_a) == compute_compiled_hash(files_b)


def test_compute_compiled_hash_changes_when_content_changes() -> None:
    original = {"CLAUDE.md": "hello world"}
    changed = {"CLAUDE.md": "hello world!"}
    assert compute_compiled_hash(original) != compute_compiled_hash(changed)


def test_compute_compiled_hash_changes_when_filename_changes() -> None:
    original = {"CLAUDE.md": "hello world"}
    changed = {"CLAUDE2.md": "hello world"}
    assert compute_compiled_hash(original) != compute_compiled_hash(changed)


async def _register(client: AsyncClient, email: str = "sync-test@example.com") -> None:
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "Sync Test"},
    )
    assert res.status_code == 201


async def _create_collection_with_artifact(
    client: AsyncClient, db_session: AsyncSession, visibility: str = "private"
) -> str:
    res = await client.post(
        "/api/v1/collections",
        json={
            "name": "compile-status-collection",
            "git_url": "https://example.com/repo.git",
            "visibility": visibility,
        },
    )
    assert res.status_code == 201
    collection_id = res.json()["id"]

    db_session.add(
        Artifact(
            collection_id=uuid.UUID(collection_id),
            artifact_type="rule",
            name="test-rule",
            priority=50,
            body="Some rule body.",
            file_path="rules/test-rule.md",
        )
    )
    await db_session.commit()
    return collection_id


async def _create_profile(client: AsyncClient, collection_id: str, is_public: bool = False) -> str:
    res = await client.post(
        "/api/v1/profiles",
        json={
            "name": "compile-status-profile",
            "base_collection_id": collection_id,
            "is_public": is_public,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


@pytest.mark.asyncio
async def test_compile_status_matches_full_compile_hash(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client)
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id)

    compile_res = await async_client.post(
        "/api/v1/profiles/compile",
        json={"profile_id": profile_id, "target": "claude-code"},
    )
    assert compile_res.status_code == 200
    full_hash = compile_res.json()["compiled_hash"]
    assert full_hash

    status_res = await async_client.get(
        f"/api/v1/profiles/{profile_id}/compile-status", params={"target": "claude-code"},
    )
    assert status_res.status_code == 200
    body = status_res.json()
    assert body["compiled_hash"] == full_hash
    assert "updated_at" in body
    # The status response never includes file content.
    assert "files" not in body


@pytest.mark.asyncio
async def test_compile_status_changes_when_artifact_changes(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client)
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id)

    first = await async_client.get(
        f"/api/v1/profiles/{profile_id}/compile-status", params={"target": "claude-code"},
    )
    assert first.status_code == 200
    first_hash = first.json()["compiled_hash"]

    # Mutate the artifact's body directly in the DB, simulating a server-side change.
    result = await db_session.execute(
        Artifact.__table__.select().where(Artifact.collection_id == uuid.UUID(collection_id))
    )
    row = result.first()
    await db_session.execute(
        Artifact.__table__.update()
        .where(Artifact.id == row.id)
        .values(body="A completely different rule body.")
    )
    await db_session.commit()

    second = await async_client.get(
        f"/api/v1/profiles/{profile_id}/compile-status", params={"target": "claude-code"},
    )
    assert second.status_code == 200
    assert second.json()["compiled_hash"] != first_hash


@pytest.mark.asyncio
async def test_compile_status_requires_auth(async_client: AsyncClient) -> None:
    res = await async_client.get(
        f"/api/v1/profiles/{uuid.uuid4()}/compile-status", params={"target": "claude-code"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_compile_status_404s_for_private_profile_of_another_user(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client, "owner@example.com")
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id, is_public=False)

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as other_client:
        await _register(other_client, "other@example.com")
        res = await other_client.get(
            f"/api/v1/profiles/{profile_id}/compile-status", params={"target": "claude-code"},
        )
        # Matches /compile's convention: 404, not 403, for a resource the
        # caller isn't allowed to see (AGENTS.md rule 13).
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_compile_status_readable_for_public_profile_by_another_user(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client, "owner2@example.com")
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id, is_public=True)

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as other_client:
        await _register(other_client, "other2@example.com")
        res = await other_client.get(
            f"/api/v1/profiles/{profile_id}/compile-status", params={"target": "claude-code"},
        )
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_compile_status_rejects_unknown_target(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client)
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id)

    res = await async_client.get(
        f"/api/v1/profiles/{profile_id}/compile-status", params={"target": "nonexistent-target"},
    )
    assert res.status_code == 422
