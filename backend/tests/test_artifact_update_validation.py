"""PATCH/POST artifact validation: explicit nulls and out-of-range values 422."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact


async def _setup(client: AsyncClient, db_session: AsyncSession) -> tuple[str, str]:
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": "patch@example.com", "password": "password123", "display_name": "P"},
    )
    assert res.status_code == 201
    res = await client.post(
        "/api/v1/collections", json={"name": "c", "git_url": "https://example.com/r.git"}
    )
    cid = str(res.json()["id"])
    art = Artifact(
        collection_id=uuid.UUID(cid), artifact_type="rule", name="r", priority=50,
        body="body", file_path="AGENTS.md",
    )
    db_session.add(art)
    await db_session.commit()
    return cid, str(art.id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"tags": None},
        {"target_compatibility": None},
        {"body": None},
        {"name": None},
        {"priority": None},
        {"version": None},
        {"file_path": None},
        {"is_enabled": None},
        {"artifact_type": "bogus"},
        {"priority": 101},
        {"priority": -1},
        {"version": "v1"},
        {"name": ""},
        {"name": "x" * 256},
    ],
)
async def test_patch_rejects_invalid_payload(
    async_client: AsyncClient, db_session: AsyncSession, payload: dict[str, object]
) -> None:
    cid, aid = await _setup(async_client, db_session)
    res = await async_client.patch(f"/api/v1/collections/{cid}/artifacts/{aid}", json=payload)
    assert res.status_code == 422
    # The artifact must still be readable afterwards.
    assert (await async_client.get(f"/api/v1/collections/{cid}/artifacts/{aid}")).status_code == 200


@pytest.mark.asyncio
async def test_patch_still_allows_nullable_fields_and_valid_edits(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    cid, aid = await _setup(async_client, db_session)
    res = await async_client.patch(
        f"/api/v1/collections/{cid}/artifacts/{aid}",
        json={"description": None, "handoff_to": None, "priority": 100, "version": "2.1.0",
              "tags": ["a"], "artifact_type": "skill"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["priority"] == 100 and body["version"] == "2.1.0"
    assert body["tags"] == ["a"] and body["artifact_type"] == "skill"
    assert body["description"] is None and body["handoff_to"] is None


@pytest.mark.asyncio
async def test_create_rejects_out_of_range_values(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    cid, _ = await _setup(async_client, db_session)
    base = {"artifact_type": "rule", "name": "n", "body": "b", "file_path": "AGENTS.md"}
    for extra in ({"priority": 500}, {"version": "x"}, {"name": "y" * 300}):
        res = await async_client.post(
            f"/api/v1/collections/{cid}/artifacts", json={**base, **extra}
        )
        assert res.status_code == 422, extra
