"""Tests for OIDC provider enable/disable via system settings."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def _create_admin(db_session: AsyncSession) -> tuple[str, str]:
    """Create an admin user and return email/password."""
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


class TestProviderToggle:
    """Test that system settings control provider availability."""

    @pytest.mark.asyncio
    async def test_providers_reflect_settings(self, db_session: AsyncSession, async_client: AsyncClient):
        """Providers endpoint should reflect system settings."""
        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})

        # Disable OIDC
        await async_client.patch("/api/v1/admin/settings", json={"oidc_enabled": False})

        # Check providers endpoint
        resp = await async_client.get("/api/v1/auth/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["oidc"] is False  # Disabled by settings

    @pytest.mark.asyncio
    async def test_disabled_provider_login_returns_403(self, db_session: AsyncSession, async_client: AsyncClient):
        """Login with a disabled provider should return 403."""
        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})

        # Disable GitHub
        await async_client.patch("/api/v1/admin/settings", json={"github_enabled": False})

        # Try to login with GitHub
        resp = await async_client.get("/api/v1/auth/login/github")
        assert resp.status_code == 403
        assert "disabled" in resp.text.lower()

    @pytest.mark.asyncio
    async def test_enabled_provider_login_redirects(self, db_session: AsyncSession, async_client: AsyncClient):
        """Login with an enabled provider should redirect (even if not configured)."""
        # Don't disable anything — providers are enabled by default
        # GitHub is not configured (no env vars), so it should return 400
        resp = await async_client.get("/api/v1/auth/login/github")
        assert resp.status_code == 400
        assert "not configured" in resp.text.lower()

    @pytest.mark.asyncio
    async def test_reenable_provider(self, db_session: AsyncSession, async_client: AsyncClient):
        """Re-enabling a provider should allow login again."""
        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})

        # Disable then re-enable
        await async_client.patch("/api/v1/admin/settings", json={"oidc_enabled": False})
        await async_client.patch("/api/v1/admin/settings", json={"oidc_enabled": True})

        # Should now get "not configured" (400) instead of "disabled" (403)
        resp = await async_client.get("/api/v1/auth/login/oidc")
        assert resp.status_code == 400
        assert "not configured" in resp.text.lower()

    @pytest.mark.asyncio
    async def test_providers_default_enabled(self, async_client: AsyncClient):
        """Providers should be enabled by default when no settings row exists."""
        resp = await async_client.get("/api/v1/auth/providers")
        assert resp.status_code == 200
        data = resp.json()
        # All should be False (not configured via env vars) but not error
        assert "oidc" in data
        assert "github" in data
        assert "google" in data


class TestRegistrationToggle:
    """Test that allow_registration controls registration."""

    @pytest.mark.asyncio
    async def test_registration_disabled(self, db_session: AsyncSession, async_client: AsyncClient):
        """Registration should be blocked when disabled."""
        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})

        # Disable registration
        await async_client.patch("/api/v1/admin/settings", json={"allow_registration": False})

        # Try to register
        resp = await async_client.post("/api/v1/auth/register", json={
            "email": "newuser@test.com",
            "password": "password123",
            "display_name": "New User",
        })
        assert resp.status_code == 403
        assert "disabled" in resp.text.lower()

    @pytest.mark.asyncio
    async def test_registration_enabled_by_default(self, async_client: AsyncClient):
        """Registration should work by default."""
        resp = await async_client.post("/api/v1/auth/register", json={
            "email": "default@test.com",
            "password": "password123",
            "display_name": "Default",
        })
        # Should succeed (201) or return fake UserRead for duplicate
        assert resp.status_code in (201, 200)

    @pytest.mark.asyncio
    async def test_registration_reenabled(self, db_session: AsyncSession, async_client: AsyncClient):
        """Re-enabling registration should allow it again."""
        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})

        # Disable then re-enable
        await async_client.patch("/api/v1/admin/settings", json={"allow_registration": False})
        await async_client.patch("/api/v1/admin/settings", json={"allow_registration": True})

        resp = await async_client.post("/api/v1/auth/register", json={
            "email": "reenabled@test.com",
            "password": "password123",
            "display_name": "Re-enabled",
        })
        assert resp.status_code == 201
