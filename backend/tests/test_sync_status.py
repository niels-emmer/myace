"""Tests for POST /sync/report and GET /sync/status (AGENTS.md rule 33)."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app as fastapi_app
from app.models.artifact import Artifact


async def _register(client: AsyncClient, email: str = "sync-report@example.com") -> None:
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "Sync Report Test"},
    )
    assert res.status_code == 201


async def _create_collection_with_artifact(client: AsyncClient, db_session: AsyncSession) -> str:
    res = await client.post(
        "/api/v1/collections",
        json={"name": "sync-report-collection", "git_url": "https://example.com/repo.git"},
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


async def _create_profile(client: AsyncClient, collection_id: str) -> str:
    res = await client.post(
        "/api/v1/profiles",
        json={"name": "sync-report-profile", "base_collection_id": collection_id},
    )
    assert res.status_code == 201
    return res.json()["id"]


def _report_payload(profile_id: str, **overrides) -> dict:
    payload = {
        "profile_id": profile_id,
        "target": "claude-code",
        "machine_label": "test-machine",
        "in_sync": True,
        "locally_modified_files": [],
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_report_creates_a_row(async_client: AsyncClient, db_session: AsyncSession) -> None:
    await _register(async_client)
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id)

    res = await async_client.post("/api/v1/sync/report", json=_report_payload(profile_id))
    assert res.status_code == 200
    body = res.json()
    assert body["profile_id"] == profile_id
    assert body["profile_name"] == "sync-report-profile"
    assert body["target"] == "claude-code"
    assert body["machine_label"] == "test-machine"
    assert body["in_sync"] is True
    assert body["locally_modified_files"] == []

    list_res = await async_client.get("/api/v1/sync/status")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


@pytest.mark.asyncio
async def test_report_upserts_rather_than_duplicates(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client)
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id)

    first = await async_client.post("/api/v1/sync/report", json=_report_payload(profile_id))
    assert first.status_code == 200
    first_id = first.json()["id"]

    second = await async_client.post(
        "/api/v1/sync/report",
        json=_report_payload(
            profile_id, in_sync=False, locally_modified_files=["CLAUDE.md"],
        ),
    )
    assert second.status_code == 200
    assert second.json()["id"] == first_id
    assert second.json()["in_sync"] is False
    assert second.json()["locally_modified_files"] == ["CLAUDE.md"]

    list_res = await async_client.get("/api/v1/sync/status")
    assert list_res.status_code == 200
    rows = list_res.json()
    assert len(rows) == 1
    assert rows[0]["in_sync"] is False


@pytest.mark.asyncio
async def test_report_different_machine_label_creates_separate_row(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client)
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id)

    await async_client.post(
        "/api/v1/sync/report", json=_report_payload(profile_id, machine_label="laptop"),
    )
    await async_client.post(
        "/api/v1/sync/report", json=_report_payload(profile_id, machine_label="desktop"),
    )

    list_res = await async_client.get("/api/v1/sync/status")
    assert len(list_res.json()) == 2


@pytest.mark.asyncio
async def test_status_list_never_shows_another_users_rows(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client, "owner-sync@example.com")
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id)

    # Make the profile public so a second user can legitimately report against it.
    await async_client.put(
        f"/api/v1/profiles/{profile_id}",
        json={
            "name": "sync-report-profile", "base_collection_id": collection_id, "is_public": True,
        },
    )

    res = await async_client.post("/api/v1/sync/report", json=_report_payload(profile_id))
    assert res.status_code == 200

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as other_client:
        await _register(other_client, "other-sync@example.com")
        other_res = await other_client.post(
            "/api/v1/sync/report",
            json=_report_payload(profile_id, machine_label="other-machine"),
        )
        assert other_res.status_code == 200

        other_list = await other_client.get("/api/v1/sync/status")
        assert other_list.status_code == 200
        assert len(other_list.json()) == 1
        assert other_list.json()[0]["machine_label"] == "other-machine"

    # Original user still only sees their own row.
    own_list = await async_client.get("/api/v1/sync/status")
    assert own_list.status_code == 200
    assert len(own_list.json()) == 1
    assert own_list.json()[0]["machine_label"] == "test-machine"


@pytest.mark.asyncio
async def test_report_rejects_unknown_target(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """`target` is a `CompileTarget` Literal (AGENTS.md rule 10) — an
    unregistered target must 422 at the schema layer, not persist a garbage
    string into the sync_statuses table."""
    await _register(async_client)
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id)

    res = await async_client.post(
        "/api/v1/sync/report",
        json=_report_payload(profile_id, target="nonexistent-target"),
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_report_requires_auth(async_client: AsyncClient) -> None:
    res = await async_client.post(
        "/api/v1/sync/report", json=_report_payload(str(uuid.uuid4())),
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_status_requires_auth(async_client: AsyncClient) -> None:
    res = await async_client.get("/api/v1/sync/status")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_report_404s_for_private_profile_of_another_user(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client, "owner3@example.com")
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id)

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as other_client:
        await _register(other_client, "other3@example.com")
        res = await other_client.post(
            "/api/v1/sync/report", json=_report_payload(profile_id),
        )
        assert res.status_code == 404
