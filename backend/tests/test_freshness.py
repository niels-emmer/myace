"""Tests for the collection freshness queue and verify endpoint
(app/api/freshness.py, app/api/collections.py::verify_collection_freshness)."""

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.collection import Collection
from app.models.user import User


async def _create_user(
    db_session: AsyncSession, email: str, password: str = "userpass123", role: str = "user"
) -> User:
    from app.core.security import hash_password

    user = User(
        email=email, display_name=email.split("@")[0],
        password_hash=hash_password(password), is_admin=(role == "admin"), role=role,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _login(async_client: AsyncClient, email: str, password: str = "userpass123") -> None:
    resp = await async_client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200


async def _create_approved_collection(
    db_session: AsyncSession,
    owner_id: uuid.UUID,
    last_verified_at: date | None,
    moderation_status: str = "approved",
) -> Collection:
    coll = Collection(
        owner_id=owner_id, name="freshness-test", git_url="https://example.com/repo.git",
        moderation_status=moderation_status,
        published=(moderation_status == "approved"),
        visibility="public" if moderation_status == "approved" else "private",
        last_verified_at=last_verified_at,
    )
    db_session.add(coll)
    await db_session.commit()
    await db_session.refresh(coll)
    return coll


class TestFreshnessQueue:
    @pytest.mark.asyncio
    async def test_never_verified_and_expired_collections_appear(
        self, async_client: AsyncClient, db_session: AsyncSession,
    ):
        owner = await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")

        never_verified = await _create_approved_collection(db_session, owner.id, None)
        stale = await _create_approved_collection(
            db_session, owner.id,
            date.today() - timedelta(days=settings.collection_freshness_threshold_days + 5),
        )

        await _login(async_client, "mod@test.com")
        res = await async_client.get("/api/v1/admin/freshness-queue")
        assert res.status_code == 200
        ids = {c["id"] for c in res.json()}
        assert str(never_verified.id) in ids
        assert str(stale.id) in ids

    @pytest.mark.asyncio
    async def test_recently_verified_collection_is_excluded(
        self, async_client: AsyncClient, db_session: AsyncSession,
    ):
        owner = await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")

        fresh = await _create_approved_collection(
            db_session, owner.id, date.today() - timedelta(days=1)
        )

        await _login(async_client, "mod@test.com")
        res = await async_client.get("/api/v1/admin/freshness-queue")
        assert res.status_code == 200
        ids = {c["id"] for c in res.json()}
        assert str(fresh.id) not in ids

    @pytest.mark.asyncio
    async def test_non_approved_collection_is_excluded_even_if_never_verified(
        self, async_client: AsyncClient, db_session: AsyncSession,
    ):
        owner = await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")

        draft = await _create_approved_collection(
            db_session, owner.id, None, moderation_status="draft"
        )

        await _login(async_client, "mod@test.com")
        res = await async_client.get("/api/v1/admin/freshness-queue")
        assert res.status_code == 200
        ids = {c["id"] for c in res.json()}
        assert str(draft.id) not in ids

    @pytest.mark.asyncio
    async def test_plain_user_forbidden(
        self, async_client: AsyncClient, db_session: AsyncSession,
    ):
        await _create_user(db_session, "user@test.com")
        await _login(async_client, "user@test.com")
        res = await async_client.get("/api/v1/admin/freshness-queue")
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_also_see_queue(
        self, async_client: AsyncClient, db_session: AsyncSession,
    ):
        owner = await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "admin@test.com", role="admin")
        never_verified = await _create_approved_collection(db_session, owner.id, None)

        await _login(async_client, "admin@test.com")
        res = await async_client.get("/api/v1/admin/freshness-queue")
        assert res.status_code == 200
        assert any(c["id"] == str(never_verified.id) for c in res.json())


class TestVerifyCollection:
    @pytest.mark.asyncio
    async def test_moderator_verify_sets_both_fields(
        self, async_client: AsyncClient, db_session: AsyncSession,
    ):
        owner = await _create_user(db_session, "owner@test.com")
        mod = await _create_user(db_session, "mod@test.com", role="moderator")
        coll = await _create_approved_collection(db_session, owner.id, None)

        await _login(async_client, "mod@test.com")
        res = await async_client.post(f"/api/v1/collections/{coll.id}/verify")
        assert res.status_code == 200
        data = res.json()
        assert data["last_verified_at"] == date.today().isoformat()
        assert data["verified_by"] == str(mod.id)

        await db_session.refresh(coll)
        assert coll.last_verified_at == date.today()
        assert coll.verified_by == mod.id

    @pytest.mark.asyncio
    async def test_plain_user_forbidden(
        self, async_client: AsyncClient, db_session: AsyncSession,
    ):
        owner = await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "user@test.com")
        coll = await _create_approved_collection(db_session, owner.id, None)

        await _login(async_client, "user@test.com")
        res = await async_client.post(f"/api/v1/collections/{coll.id}/verify")
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_verify_missing_collection_returns_404(
        self, async_client: AsyncClient, db_session: AsyncSession,
    ):
        await _create_user(db_session, "mod@test.com", role="moderator")
        await _login(async_client, "mod@test.com")
        res = await async_client.post(f"/api/v1/collections/{uuid.uuid4()}/verify")
        assert res.status_code == 404
