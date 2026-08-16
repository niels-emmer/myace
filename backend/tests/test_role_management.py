"""Tests for the moderator role model: admin role-management endpoint and
the `require_moderator_or_admin` dependency."""

import uuid

import pytest
from fastapi import APIRouter, Depends
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_user(
    db_session: AsyncSession,
    email: str,
    password: str = "userpass123",
    is_admin: bool = False,
    role: str | None = None,
) -> uuid.UUID:
    from app.core.security import hash_password
    from app.models.user import User

    user = User(
        email=email, display_name=email.split("@")[0],
        password_hash=hash_password(password), is_admin=is_admin,
        role=role if role is not None else ("admin" if is_admin else "user"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user.id


async def _login(async_client: AsyncClient, email: str, password: str = "userpass123") -> None:
    resp = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


class TestSetUserRole:
    @pytest.mark.asyncio
    async def test_admin_can_promote_to_moderator(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        await _create_user(db_session, "admin@test.com", is_admin=True)
        target_id = await _create_user(db_session, "target@test.com")
        await _login(async_client, "admin@test.com")

        resp = await async_client.patch(
            f"/api/v1/auth/users/{target_id}/role", json={"role": "moderator"}
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "moderator"
        assert resp.json()["is_admin"] is False

        from sqlmodel import select

        from app.models.user import User

        await db_session.rollback()
        result = await db_session.execute(select(User).where(User.id == target_id))
        user = result.scalar_one()
        assert user.role == "moderator"
        assert user.is_admin is False

    @pytest.mark.asyncio
    async def test_promoting_to_admin_syncs_is_admin(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        await _create_user(db_session, "admin@test.com", is_admin=True)
        target_id = await _create_user(db_session, "target@test.com")
        await _login(async_client, "admin@test.com")

        resp = await async_client.patch(
            f"/api/v1/auth/users/{target_id}/role", json={"role": "admin"}
        )
        assert resp.status_code == 200
        assert resp.json()["is_admin"] is True

    @pytest.mark.asyncio
    async def test_demoting_admin_syncs_is_admin_false(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        await _create_user(db_session, "admin@test.com", is_admin=True)
        target_id = await _create_user(db_session, "target@test.com", is_admin=True)
        await _login(async_client, "admin@test.com")

        resp = await async_client.patch(
            f"/api/v1/auth/users/{target_id}/role", json={"role": "user"}
        )
        assert resp.status_code == 200
        assert resp.json()["is_admin"] is False

    @pytest.mark.asyncio
    async def test_non_admin_forbidden(self, db_session: AsyncSession, async_client: AsyncClient):
        await _create_user(db_session, "user@test.com")
        target_id = await _create_user(db_session, "target@test.com")
        await _login(async_client, "user@test.com")

        resp = await async_client.patch(
            f"/api/v1/auth/users/{target_id}/role", json={"role": "moderator"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_cannot_change_own_role(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        admin_id = await _create_user(db_session, "admin@test.com", is_admin=True)
        await _login(async_client, "admin@test.com")

        resp = await async_client.patch(
            f"/api/v1/auth/users/{admin_id}/role", json={"role": "user"}
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_unknown_user_404(self, db_session: AsyncSession, async_client: AsyncClient):
        await _create_user(db_session, "admin@test.com", is_admin=True)
        await _login(async_client, "admin@test.com")

        resp = await async_client.patch(
            f"/api/v1/auth/users/{uuid.uuid4()}/role", json={"role": "moderator"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_role_rejected(self, db_session: AsyncSession, async_client: AsyncClient):
        await _create_user(db_session, "admin@test.com", is_admin=True)
        target_id = await _create_user(db_session, "target@test.com")
        await _login(async_client, "admin@test.com")

        resp = await async_client.patch(
            f"/api/v1/auth/users/{target_id}/role", json={"role": "superuser"}
        )
        assert resp.status_code == 422


class TestRoleBackfillMigration:
    @pytest.mark.asyncio
    async def test_backfill_sets_role_admin_for_every_is_admin_row(
        self, db_session: AsyncSession
    ):
        """Runs the exact UPDATE statement from the Epic 1 migration
        (d0e1f2a3b4c5_add_role_to_users.py) against rows simulating the
        pre-migration state (is_admin=True, role still at its 'user'
        default) and confirms every one of them ends up with role='admin'."""
        from sqlalchemy import text
        from sqlmodel import select

        from app.core.security import hash_password
        from app.models.user import User

        for email in ("legacy-admin-1@test.com", "legacy-admin-2@test.com"):
            db_session.add(User(
                email=email, display_name=email.split("@")[0],
                password_hash=hash_password("userpass123"), is_admin=True, role="user",
            ))
        db_session.add(User(
            email="legacy-plain@test.com", display_name="legacy-plain",
            password_hash=hash_password("userpass123"), is_admin=False, role="user",
        ))
        await db_session.commit()

        await db_session.execute(text("UPDATE users SET role = 'admin' WHERE is_admin = true"))
        await db_session.commit()

        result = await db_session.execute(select(User).where(User.is_admin == True))  # noqa: E712
        for user in result.scalars().all():
            assert user.role == "admin"

        result = await db_session.execute(
            select(User).where(User.email == "legacy-plain@test.com")
        )
        assert result.scalar_one().role == "user"


class TestRequireModeratorOrAdmin:
    """Exercises the dependency directly via a throwaway protected route,
    since no production route uses it until Epic 3 lands."""

    @pytest.fixture(autouse=True)
    def _mount_probe_route(self, async_client: AsyncClient):
        from app.core.deps import require_moderator_or_admin
        from app.main import app
        from app.models.user import User

        router = APIRouter()

        @router.get("/_test/moderator-probe")
        async def probe(current_user: User = Depends(require_moderator_or_admin)):
            return {"ok": True, "role": current_user.role}

        app.include_router(router, prefix="/api/v1")
        yield
        app.router.routes = [
            r for r in app.router.routes if getattr(r, "path", "") != "/api/v1/_test/moderator-probe"
        ]

    @pytest.mark.asyncio
    async def test_moderator_allowed(self, db_session: AsyncSession, async_client: AsyncClient):
        await _create_user(db_session, "mod@test.com", role="moderator")
        await _login(async_client, "mod@test.com")

        resp = await async_client.get("/api/v1/_test/moderator-probe")
        assert resp.status_code == 200
        assert resp.json()["role"] == "moderator"

    @pytest.mark.asyncio
    async def test_admin_allowed(self, db_session: AsyncSession, async_client: AsyncClient):
        await _create_user(db_session, "admin@test.com", is_admin=True)
        await _login(async_client, "admin@test.com")

        resp = await async_client.get("/api/v1/_test/moderator-probe")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_plain_user_forbidden(self, db_session: AsyncSession, async_client: AsyncClient):
        await _create_user(db_session, "user@test.com")
        await _login(async_client, "user@test.com")

        resp = await async_client.get("/api/v1/_test/moderator-probe")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_flag_alone_without_role_is_not_sufficient(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        """A legacy row with is_admin=True but role left at the default
        'user' (i.e. the Epic 1 migration backfill didn't run) must NOT
        pass this dependency — role is the only field it reads."""
        await _create_user(db_session, "legacy-admin@test.com", is_admin=True, role="user")
        await _login(async_client, "legacy-admin@test.com")

        resp = await async_client.get("/api/v1/_test/moderator-probe")
        assert resp.status_code == 403
