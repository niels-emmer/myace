"""Tests for admin-driven user disable/enable/removal."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_user(
    db_session: AsyncSession, email: str, password: str = "userpass123", is_admin: bool = False
) -> uuid.UUID:
    from app.core.security import hash_password
    from app.models.user import User

    user = User(
        email=email, display_name=email.split("@")[0],
        password_hash=hash_password(password), is_admin=is_admin,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user.id


async def _login(async_client: AsyncClient, email: str, password: str = "userpass123") -> None:
    resp = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


class TestSetUserActive:
    @pytest.mark.asyncio
    async def test_admin_can_disable_user(self, db_session: AsyncSession, async_client: AsyncClient):
        await _create_user(db_session, "admin@test.com", is_admin=True)
        target_id = await _create_user(db_session, "target@test.com")
        await _login(async_client, "admin@test.com")

        resp = await async_client.patch(f"/api/v1/auth/users/{target_id}?is_active=false")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

        from sqlmodel import select

        from app.models.user import User

        await db_session.rollback()
        result = await db_session.execute(select(User).where(User.id == target_id))
        assert result.scalar_one().is_active is False

    @pytest.mark.asyncio
    async def test_admin_can_reenable_user(self, db_session: AsyncSession, async_client: AsyncClient):
        await _create_user(db_session, "admin@test.com", is_admin=True)
        target_id = await _create_user(db_session, "target@test.com")
        await _login(async_client, "admin@test.com")

        await async_client.patch(f"/api/v1/auth/users/{target_id}?is_active=false")
        resp = await async_client.patch(f"/api/v1/auth/users/{target_id}?is_active=true")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    @pytest.mark.asyncio
    async def test_disabled_user_cannot_login(self, db_session: AsyncSession, async_client: AsyncClient):
        await _create_user(db_session, "admin@test.com", is_admin=True)
        target_id = await _create_user(db_session, "target@test.com")
        await _login(async_client, "admin@test.com")

        await async_client.patch(f"/api/v1/auth/users/{target_id}?is_active=false")
        await async_client.post("/api/v1/auth/logout")

        resp = await async_client.post(
            "/api/v1/auth/login", json={"email": "target@test.com", "password": "userpass123"}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_non_admin_forbidden(self, db_session: AsyncSession, async_client: AsyncClient):
        await _create_user(db_session, "user@test.com")
        target_id = await _create_user(db_session, "target@test.com")
        await _login(async_client, "user@test.com")

        resp = await async_client.patch(f"/api/v1/auth/users/{target_id}?is_active=false")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_cannot_act_on_own_row(self, db_session: AsyncSession, async_client: AsyncClient):
        admin_id = await _create_user(db_session, "admin@test.com", is_admin=True)
        await _login(async_client, "admin@test.com")

        resp = await async_client.patch(f"/api/v1/auth/users/{admin_id}?is_active=false")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_unknown_user_404(self, db_session: AsyncSession, async_client: AsyncClient):
        await _create_user(db_session, "admin@test.com", is_admin=True)
        await _login(async_client, "admin@test.com")

        resp = await async_client.patch(f"/api/v1/auth/users/{uuid.uuid4()}?is_active=false")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_can_disable_the_only_other_admin(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        """The caller (an active admin distinct from the target, per
        require_admin + the own-account block above) always remains, so
        disabling the only other admin is allowed rather than blocked —
        there's no lockout scenario this endpoint can create."""
        await _create_user(db_session, "admin1@test.com", is_admin=True)
        admin2_id = await _create_user(db_session, "admin2@test.com", is_admin=True)
        await _login(async_client, "admin1@test.com")

        resp = await async_client.patch(f"/api/v1/auth/users/{admin2_id}?is_active=false")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False


class TestRemoveUser:
    @pytest.mark.asyncio
    async def test_admin_can_remove_user(self, db_session: AsyncSession, async_client: AsyncClient):
        await _create_user(db_session, "admin@test.com", is_admin=True)
        target_id = await _create_user(db_session, "target@test.com")
        await _login(async_client, "admin@test.com")

        resp = await async_client.delete(f"/api/v1/auth/users/{target_id}")
        assert resp.status_code == 200

        from sqlmodel import select

        from app.models.user import User

        await db_session.rollback()
        result = await db_session.execute(select(User).where(User.id == target_id))
        user = result.scalar_one()
        assert user.is_active is False
        assert user.deleted_at is not None

    @pytest.mark.asyncio
    async def test_remove_deactivates_owned_collections(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        await _create_user(db_session, "admin@test.com", is_admin=True)
        await _create_user(db_session, "target@test.com")
        await _login(async_client, "target@test.com")
        resp = await async_client.post("/api/v1/collections", json={
            "name": "Target's Collection", "git_url": "https://example.com/repo.git",
        })
        assert resp.status_code == 201
        collection_id = uuid.UUID(resp.json()["id"])

        await async_client.post("/api/v1/auth/logout")
        await _login(async_client, "admin@test.com")

        from sqlmodel import select

        from app.models.collection import Collection
        from app.models.user import User

        result = await db_session.execute(select(User).where(User.email == "target@test.com"))
        target_id = result.scalar_one().id

        resp = await async_client.delete(f"/api/v1/auth/users/{target_id}")
        assert resp.status_code == 200

        await db_session.rollback()
        result = await db_session.execute(select(Collection).where(Collection.id == collection_id))
        coll = result.scalar_one()
        assert coll.is_active is False

    @pytest.mark.asyncio
    async def test_removed_user_cannot_login(self, db_session: AsyncSession, async_client: AsyncClient):
        await _create_user(db_session, "admin@test.com", is_admin=True)
        target_id = await _create_user(db_session, "target@test.com")
        await _login(async_client, "admin@test.com")

        await async_client.delete(f"/api/v1/auth/users/{target_id}")
        await async_client.post("/api/v1/auth/logout")

        resp = await async_client.post(
            "/api/v1/auth/login", json={"email": "target@test.com", "password": "userpass123"}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_non_admin_forbidden(self, db_session: AsyncSession, async_client: AsyncClient):
        await _create_user(db_session, "user@test.com")
        target_id = await _create_user(db_session, "target@test.com")
        await _login(async_client, "user@test.com")

        resp = await async_client.delete(f"/api/v1/auth/users/{target_id}")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_cannot_remove_own_account(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        admin_id = await _create_user(db_session, "admin@test.com", is_admin=True)
        await _login(async_client, "admin@test.com")

        resp = await async_client.delete(f"/api/v1/auth/users/{admin_id}")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_unknown_user_404(self, db_session: AsyncSession, async_client: AsyncClient):
        await _create_user(db_session, "admin@test.com", is_admin=True)
        await _login(async_client, "admin@test.com")

        resp = await async_client.delete(f"/api/v1/auth/users/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_can_remove_the_only_other_admin(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        """Same reasoning as TestSetUserActive.test_can_disable_the_only_other_admin —
        the caller always remains a distinct active admin, so this can't
        create a lockout and isn't blocked."""
        await _create_user(db_session, "admin1@test.com", is_admin=True)
        admin2_id = await _create_user(db_session, "admin2@test.com", is_admin=True)
        await _login(async_client, "admin1@test.com")

        resp = await async_client.delete(f"/api/v1/auth/users/{admin2_id}")
        assert resp.status_code == 200
