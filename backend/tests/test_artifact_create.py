"""Tests for POST /collections/{collection_id}/artifacts (Epic 3.4)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def _create_user(db_session: AsyncSession, email: str, password: str = "userpass123") -> uuid.UUID:
    from app.core.security import hash_password

    user = User(email=email, display_name=email.split("@")[0], password_hash=hash_password(password))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user.id


async def _login(async_client: AsyncClient, email: str, password: str = "userpass123") -> None:
    resp = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


async def _create_collection(async_client: AsyncClient, name: str = "wizard-target") -> str:
    res = await async_client.post(
        "/api/v1/collections",
        json={"name": name, "git_url": "https://example.com/repo.git"},
    )
    assert res.status_code == 201
    return res.json()["id"]


class TestCreateArtifact:
    @pytest.mark.asyncio
    async def test_create_artifact_succeeds_for_owner(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, "owner@test.com")
        await _login(async_client, "owner@test.com")
        collection_id = await _create_collection(async_client)

        res = await async_client.post(
            f"/api/v1/collections/{collection_id}/artifacts",
            json={
                "artifact_type": "agent",
                "name": "generated-orchestrator",
                "priority": 60,
                "body": "## Handoff\n\nRoutes to builder, then verifier.",
                "file_path": "agents/generated-orchestrator.md",
                "tags": ["mode:primary"],
                "handoff_to": ["builder", "verifier"],
            },
        )
        assert res.status_code == 201
        body = res.json()
        assert body["name"] == "generated-orchestrator"
        assert body["artifact_type"] == "agent"
        assert body["handoff_to"] == ["builder", "verifier"]
        assert body["collection_id"] == collection_id

        # Round-trips through the list endpoint too.
        list_res = await async_client.get(f"/api/v1/collections/{collection_id}/artifacts")
        assert list_res.status_code == 200
        names = [a["name"] for a in list_res.json()]
        assert "generated-orchestrator" in names
        # The frontend reads handoff_to from this list response (the gallery /
        # builder derive recipes from it), so it must survive list serialization
        # as a list[str], not a JSON-encoded string or null.
        listed = next(a for a in list_res.json() if a["name"] == "generated-orchestrator")
        assert listed["handoff_to"] == ["builder", "verifier"]

    @pytest.mark.asyncio
    async def test_create_artifact_without_handoff_to_is_none(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, "owner2@test.com")
        await _login(async_client, "owner2@test.com")
        collection_id = await _create_collection(async_client, name="no-handoff")

        res = await async_client.post(
            f"/api/v1/collections/{collection_id}/artifacts",
            json={
                "artifact_type": "rule",
                "name": "a-rule",
                "body": "Some rule body.",
                "file_path": "rules/a-rule.md",
            },
        )
        assert res.status_code == 201
        assert res.json()["handoff_to"] is None

    @pytest.mark.asyncio
    async def test_create_artifact_404s_for_non_owner(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, "owner3@test.com")
        await _create_user(db_session, "intruder@test.com")
        await _login(async_client, "owner3@test.com")
        collection_id = await _create_collection(async_client, name="private-collection")
        await async_client.post("/api/v1/auth/logout")

        await _login(async_client, "intruder@test.com")
        res = await async_client.post(
            f"/api/v1/collections/{collection_id}/artifacts",
            json={
                "artifact_type": "agent",
                "name": "intruding-agent",
                "body": "body",
                "file_path": "agents/intruding-agent.md",
            },
        )
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_create_artifact_invalid_type_422s(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, "owner4@test.com")
        await _login(async_client, "owner4@test.com")
        collection_id = await _create_collection(async_client, name="type-check")

        res = await async_client.post(
            f"/api/v1/collections/{collection_id}/artifacts",
            json={
                "artifact_type": "not-a-real-type",
                "name": "bad-type-artifact",
                "body": "body",
                "file_path": "x.md",
            },
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_create_artifact_requires_auth(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        res = await async_client.post(
            f"/api/v1/collections/{uuid.uuid4()}/artifacts",
            json={
                "artifact_type": "agent",
                "name": "x",
                "body": "body",
                "file_path": "x.md",
            },
        )
        assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_create_artifact_increments_collection_artifact_count(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, "owner5@test.com")
        await _login(async_client, "owner5@test.com")
        collection_id = await _create_collection(async_client, name="count-check")

        before = await async_client.get(f"/api/v1/collections/{collection_id}")
        assert before.json()["artifact_count"] == 0

        res = await async_client.post(
            f"/api/v1/collections/{collection_id}/artifacts",
            json={
                "artifact_type": "agent",
                "name": "counted-agent",
                "body": "body",
                "file_path": "agents/counted-agent.md",
            },
        )
        assert res.status_code == 201

        after = await async_client.get(f"/api/v1/collections/{collection_id}")
        assert after.json()["artifact_count"] == 1
