"""Compile-time authorization and soft-delete filtering (AGENTS.md rules 13, 15)."""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app as fastapi_app
from app.models.artifact import Artifact
from app.models.collection import Collection


async def _register(client: AsyncClient, email: str) -> None:
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "Compile Authz"},
    )
    assert res.status_code == 201


async def _make_collection(client: AsyncClient, visibility: str = "private") -> str:
    res = await client.post(
        "/api/v1/collections",
        json={"name": "authz-collection", "git_url": "https://example.com/r.git",
              "visibility": visibility},
    )
    assert res.status_code == 201
    return str(res.json()["id"])


def _artifact(collection_id: str, name: str, **kwargs: object) -> Artifact:
    return Artifact(
        collection_id=uuid.UUID(collection_id), artifact_type="rule", name=name,
        priority=50, body=f"{name} body", file_path=f"rules/{name}.md", **kwargs,
    )


async def _profile(client: AsyncClient, collection_id: str, is_public: bool = False) -> str:
    res = await client.post(
        "/api/v1/profiles",
        json={"name": "authz-profile", "base_collection_id": collection_id,
              "is_public": is_public},
    )
    assert res.status_code == 201
    return str(res.json()["id"])


@pytest.mark.asyncio
async def test_compile_excludes_soft_deleted_artifacts(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client, "owner-sd@example.com")
    cid = await _make_collection(async_client)
    db_session.add(_artifact(cid, "live-rule"))
    db_session.add(_artifact(cid, "gone-rule", deleted_at=datetime.now(UTC)))
    await db_session.commit()
    pid = await _profile(async_client, cid)

    res = await async_client.post(
        "/api/v1/profiles/compile", json={"profile_id": pid, "target": "claude-code"}
    )
    assert res.status_code == 200
    assert res.json()["artifact_count"] == 1
    assert "gone-rule" not in "".join(res.json()["files"].values())


@pytest.mark.asyncio
async def test_compile_skips_inactive_collection(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client, "owner-ia@example.com")
    cid = await _make_collection(async_client)
    db_session.add(_artifact(cid, "rule-a"))
    await db_session.commit()
    # Create the profile while the collection is still live (a profile can't
    # be built on an inactive one), then soft-delete the collection.
    pid = await _profile(async_client, cid)
    coll = await db_session.get(Collection, uuid.UUID(cid))
    assert coll is not None
    coll.is_active = False
    await db_session.commit()

    res = await async_client.post(
        "/api/v1/profiles/compile", json={"profile_id": pid, "target": "claude-code"}
    )
    assert res.status_code == 200
    assert res.json()["artifact_count"] == 0


@pytest.mark.asyncio
async def test_public_profile_does_not_leak_private_collection_to_other_user(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client, "owner-leak@example.com")
    cid = await _make_collection(async_client, visibility="private")
    db_session.add(_artifact(cid, "secret-rule"))
    await db_session.commit()
    pid = await _profile(async_client, cid, is_public=True)

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as other:
        await _register(other, "other-leak@example.com")
        res = await other.post(
            "/api/v1/profiles/compile", json={"profile_id": pid, "target": "claude-code"}
        )
        assert res.status_code == 200
        assert res.json()["artifact_count"] == 0
        assert "secret-rule" not in "".join(res.json()["files"].values())

    owner_res = await async_client.post(
        "/api/v1/profiles/compile", json={"profile_id": pid, "target": "claude-code"}
    )
    assert owner_res.json()["artifact_count"] == 1


@pytest.mark.asyncio
async def test_include_disabled_ignored_for_non_owner(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client, "owner-dis@example.com")
    cid = await _make_collection(async_client, visibility="public")
    db_session.add(_artifact(cid, "on-rule"))
    db_session.add(_artifact(cid, "off-rule", is_enabled=False))
    await db_session.commit()
    pid = await _profile(async_client, cid, is_public=True)

    owner_res = await async_client.post(
        "/api/v1/profiles/compile",
        json={"profile_id": pid, "target": "claude-code", "include_disabled": True},
    )
    assert owner_res.json()["artifact_count"] == 2

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as other:
        await _register(other, "other-dis@example.com")
        res = await other.post(
            "/api/v1/profiles/compile",
            json={"profile_id": pid, "target": "claude-code", "include_disabled": True},
        )
        assert res.json()["artifact_count"] == 1
