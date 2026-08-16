"""Tests for collection ratings."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact
from app.models.collection import Collection
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


async def _create_approved_collection(
    async_client: AsyncClient, db_session: AsyncSession, owner_email: str, name: str = "rate-me"
) -> str:
    await _login(async_client, owner_email)
    res = await async_client.post(
        "/api/v1/collections",
        json={"name": name, "git_url": "https://example.com/repo.git"},
    )
    collection_id = res.json()["id"]
    db_session.add(Artifact(
        collection_id=uuid.UUID(collection_id), artifact_type="rule",
        name="r", priority=50, body="body", file_path="rules/r.md",
    ))
    await db_session.commit()
    await async_client.post(
        f"/api/v1/collections/{collection_id}/publish", json={"category": "python"}
    )
    coll = await db_session.get(Collection, uuid.UUID(collection_id))
    coll.moderation_status = "approved"
    coll.published = True
    coll.visibility = "public"
    await db_session.commit()
    await async_client.post("/api/v1/auth/logout")
    return collection_id


class TestRating:
    @pytest.mark.asyncio
    async def test_rate_collection(self, async_client: AsyncClient, db_session: AsyncSession):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "rater@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "rater@test.com")
        res = await async_client.put(f"/api/v1/collections/{collection_id}/rating", json={"stars": 4})
        assert res.status_code == 200
        data = res.json()
        assert data["avg_rating"] == 4.0
        assert data["rating_count"] == 1
        assert data["my_rating"] == 4

    @pytest.mark.asyncio
    async def test_rating_upsert_changes_not_duplicates(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "rater@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "rater@test.com")
        await async_client.put(f"/api/v1/collections/{collection_id}/rating", json={"stars": 3})
        res = await async_client.put(f"/api/v1/collections/{collection_id}/rating", json={"stars": 5})
        assert res.status_code == 200
        data = res.json()
        assert data["avg_rating"] == 5.0
        assert data["rating_count"] == 1  # not 2 — upsert, not a new row

    @pytest.mark.asyncio
    async def test_avg_across_multiple_raters(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "rater1@test.com")
        await _create_user(db_session, "rater2@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "rater1@test.com")
        await async_client.put(f"/api/v1/collections/{collection_id}/rating", json={"stars": 2})
        await async_client.post("/api/v1/auth/logout")

        await _login(async_client, "rater2@test.com")
        res = await async_client.put(f"/api/v1/collections/{collection_id}/rating", json={"stars": 4})
        assert res.status_code == 200
        data = res.json()
        assert data["avg_rating"] == 3.0
        assert data["rating_count"] == 2

    @pytest.mark.asyncio
    async def test_self_rating_blocked(self, async_client: AsyncClient, db_session: AsyncSession):
        await _create_user(db_session, "owner@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "owner@test.com")
        res = await async_client.put(f"/api/v1/collections/{collection_id}/rating", json={"stars": 5})
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_rating_non_approved_collection_404s(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "rater@test.com")
        await _login(async_client, "owner@test.com")
        res = await async_client.post(
            "/api/v1/collections",
            json={"name": "draft-coll", "git_url": "https://example.com/repo.git"},
        )
        draft_id = res.json()["id"]
        await async_client.post("/api/v1/auth/logout")

        await _login(async_client, "rater@test.com")
        res = await async_client.put(f"/api/v1/collections/{draft_id}/rating", json={"stars": 5})
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_out_of_range_stars_422(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "rater@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "rater@test.com")
        res = await async_client.put(f"/api/v1/collections/{collection_id}/rating", json={"stars": 6})
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_delete_rating_recomputes(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "rater@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "rater@test.com")
        await async_client.put(f"/api/v1/collections/{collection_id}/rating", json={"stars": 3})
        res = await async_client.delete(f"/api/v1/collections/{collection_id}/rating")
        assert res.status_code == 200
        data = res.json()
        assert data["avg_rating"] == 0.0
        assert data["rating_count"] == 0
        assert data["my_rating"] is None

    @pytest.mark.asyncio
    async def test_get_rating_shows_my_rating(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "rater@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "rater@test.com")
        await async_client.put(f"/api/v1/collections/{collection_id}/rating", json={"stars": 3})
        res = await async_client.get(f"/api/v1/collections/{collection_id}/rating")
        assert res.status_code == 200
        assert res.json()["my_rating"] == 3

    @pytest.mark.asyncio
    async def test_requires_auth(self, async_client: AsyncClient, db_session: AsyncSession):
        res = await async_client.put(
            f"/api/v1/collections/{uuid.uuid4()}/rating", json={"stars": 3}
        )
        assert res.status_code == 401
