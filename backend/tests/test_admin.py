"""Tests for admin settings API."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def _create_admin(db_session: AsyncSession) -> tuple[str, str]:
    """Create an admin user and return email/password for login."""
    from app.core.security import hash_password
    from app.models.user import User

    user = User(
        email="admin@test.com",
        display_name="Admin",
        password_hash=hash_password("adminpass123"),
        is_admin=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return "admin@test.com", "adminpass123"


@pytest.mark.asyncio
async def _create_user(db_session: AsyncSession) -> tuple[str, str]:
    """Create a regular user and return email/password for login."""
    from app.core.security import hash_password
    from app.models.user import User

    user = User(
        email="user@test.com",
        display_name="User",
        password_hash=hash_password("userpass123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return "user@test.com", "userpass123"


class TestAdminSettings:
    """Test system settings CRUD via admin API."""

    @pytest.mark.asyncio
    async def test_get_settings_as_admin(self, db_session: AsyncSession, async_client: AsyncClient):
        """Admin should be able to read system settings."""
        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})

        resp = await async_client.get("/api/v1/admin/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["oidc_enabled"] is True
        assert data["github_enabled"] is True
        assert data["google_enabled"] is True
        assert data["allow_registration"] is True
        assert data["mfa_enabled"] is False
        assert data["mfa_forced"] is False
        assert data["doc_cache_ttl_days"] == 7
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_get_settings_as_non_admin(self, db_session: AsyncSession, async_client: AsyncClient):
        """Non-admin should get 403."""
        email, password = await _create_user(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})

        resp = await async_client.get("/api/v1/admin/settings")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_get_settings_unauthenticated(self, async_client: AsyncClient):
        """Unauthenticated request should get 401."""
        resp = await async_client.get("/api/v1/admin/settings")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_update_settings_as_admin(self, db_session: AsyncSession, async_client: AsyncClient):
        """Admin should be able to update system settings."""
        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})

        resp = await async_client.patch("/api/v1/admin/settings", json={
            "oidc_enabled": False,
            "mfa_enabled": True,
            "doc_cache_ttl_days": 14,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["oidc_enabled"] is False
        assert data["mfa_enabled"] is True
        assert data["doc_cache_ttl_days"] == 14
        # Unchanged fields should remain at defaults
        assert data["github_enabled"] is True
        assert data["google_enabled"] is True
        assert data["allow_registration"] is True
        assert data["mfa_forced"] is False

    @pytest.mark.asyncio
    async def test_update_settings_as_non_admin(self, db_session: AsyncSession, async_client: AsyncClient):
        """Non-admin should get 403 when updating settings."""
        email, password = await _create_user(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})

        resp = await async_client.patch("/api/v1/admin/settings", json={"oidc_enabled": False})
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_partial_update(self, db_session: AsyncSession, async_client: AsyncClient):
        """Partial update should only change specified fields."""
        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})

        # First update one field
        resp = await async_client.patch("/api/v1/admin/settings", json={"mfa_enabled": True})
        assert resp.status_code == 200
        assert resp.json()["mfa_enabled"] is True
        assert resp.json()["oidc_enabled"] is True  # unchanged

        # Then update another
        resp = await async_client.patch("/api/v1/admin/settings", json={"oidc_enabled": False})
        assert resp.status_code == 200
        assert resp.json()["oidc_enabled"] is False
        assert resp.json()["mfa_enabled"] is True  # still set from before

    @pytest.mark.asyncio
    async def test_settings_persist_across_reads(self, db_session: AsyncSession, async_client: AsyncClient):
        """Updated settings should persist when read again."""
        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})

        await async_client.patch("/api/v1/admin/settings", json={
            "allow_registration": False,
            "mfa_forced": True,
        })

        resp = await async_client.get("/api/v1/admin/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["allow_registration"] is False
        assert data["mfa_forced"] is True
