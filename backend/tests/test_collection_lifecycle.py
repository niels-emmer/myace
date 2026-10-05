"""Soft-deleted collections are gone; artifact counts and handoff_to survive copies."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact


async def _register(client: AsyncClient, email: str) -> None:
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "Lifecycle"},
    )
    assert res.status_code == 201


async def _make_collection(client: AsyncClient, name: str = "lifecycle") -> str:
    res = await client.post(
        "/api/v1/collections", json={"name": name, "git_url": "https://example.com/r.git"}
    )
    assert res.status_code == 201
    return str(res.json()["id"])


def _artifact(cid: str, name: str, **kwargs: object) -> Artifact:
    return Artifact(
        collection_id=uuid.UUID(cid), artifact_type="agent", name=name,
        priority=50, body=f"{name} body", file_path=f"agents/{name}.md", **kwargs,
    )


@pytest.mark.asyncio
async def test_soft_deleted_collection_is_404_everywhere(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client, "sd-coll@example.com")
    cid = await _make_collection(async_client)
    assert (await async_client.delete(f"/api/v1/collections/{cid}")).status_code == 200

    assert (await async_client.get(f"/api/v1/collections/{cid}")).status_code == 404
    assert (await async_client.get(f"/api/v1/collections/{cid}/artifacts")).status_code == 404
    patch = await async_client.patch(f"/api/v1/collections/{cid}", json={"name": "x"})
    assert patch.status_code == 404
    publish = await async_client.post(
        f"/api/v1/collections/{cid}/publish", json={"category": "testing"}
    )
    assert publish.status_code == 404


@pytest.mark.asyncio
async def test_profile_cannot_use_soft_deleted_base_collection(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client, "sd-prof@example.com")
    cid = await _make_collection(async_client)
    await async_client.delete(f"/api/v1/collections/{cid}")
    res = await async_client.post(
        "/api/v1/profiles", json={"name": "p", "base_collection_id": cid}
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_bulk_delete_decrements_artifact_count(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client, "count@example.com")
    cid = await _make_collection(async_client)
    a, b = _artifact(cid, "one"), _artifact(cid, "two")
    db_session.add_all([a, b])
    await db_session.commit()

    res = await async_client.post(
        f"/api/v1/collections/{cid}/artifacts/bulk-delete", json={"artifact_ids": [str(a.id)]}
    )
    assert res.status_code == 200
    got = await async_client.get(f"/api/v1/collections/{cid}")
    assert got.json()["artifact_count"] == 1


@pytest.mark.asyncio
async def test_bulk_export_preserves_handoff_to_and_counts_live_only(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client, "export@example.com")
    src = await _make_collection(async_client, "src")
    dst = await _make_collection(async_client, "dst")
    agent = _artifact(src, "orchestrator", handoff_to='["builder"]')
    db_session.add(agent)
    await db_session.commit()

    res = await async_client.post(
        f"/api/v1/collections/{src}/artifacts/bulk-export",
        json={"artifact_ids": [str(agent.id)], "target_collection_id": dst},
    )
    assert res.status_code == 200
    arts = await async_client.get(f"/api/v1/collections/{dst}/artifacts")
    assert arts.json()[0]["handoff_to"] == ["builder"]
    assert (await async_client.get(f"/api/v1/collections/{dst}")).json()["artifact_count"] == 1
