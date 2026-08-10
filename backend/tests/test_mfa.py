"""Tests for TOTP MFA support."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def _create_user(db_session: AsyncSession, email="user@test.com", password="userpass123") -> tuple[str, str]:
    """Create a regular user and return email/password."""
    from app.core.security import hash_password
    from app.models.user import User

    user = User(
        email=email,
        display_name="Test User",
        password_hash=hash_password(password),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return email, password


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


class TestMfaSetup:
    """Test MFA setup flow."""

    @pytest.mark.asyncio
    async def test_setup_totp(self, db_session: AsyncSession, async_client: AsyncClient):
        """Should generate TOTP secret and provisioning URI."""
        # Enable MFA in system settings
        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
        await async_client.patch("/api/v1/admin/settings", json={"mfa_enabled": True})

        # Login as regular user
        user_email, user_pass = await _create_user(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": user_email, "password": user_pass})

        resp = await async_client.post("/api/v1/auth/me/mfa/totp/setup")
        assert resp.status_code == 200
        data = resp.json()
        assert "secret" in data
        assert len(data["secret"]) > 10
        assert "provisioning_uri" in data
        assert data["provisioning_uri"].startswith("otpauth://")

    @pytest.mark.asyncio
    async def test_setup_totp_mfa_disabled_in_settings(self, db_session: AsyncSession, async_client: AsyncClient):
        """Should reject setup when MFA is disabled in system settings."""
        # Ensure MFA is disabled
        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
        await async_client.patch("/api/v1/admin/settings", json={"mfa_enabled": False})

        user_email, user_pass = await _create_user(db_session, "user2@test.com")
        await async_client.post("/api/v1/auth/login", json={"email": user_email, "password": user_pass})

        resp = await async_client.post("/api/v1/auth/me/mfa/totp/setup")
        assert resp.status_code == 400
        assert "not enabled" in resp.text.lower()

    @pytest.mark.asyncio
    async def test_verify_totp(self, db_session: AsyncSession, async_client: AsyncClient):
        """Should verify TOTP code and enable MFA."""
        import pyotp

        # Enable MFA in system settings
        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
        await async_client.patch("/api/v1/admin/settings", json={"mfa_enabled": True})

        user_email, user_pass = await _create_user(db_session, "user3@test.com")
        await async_client.post("/api/v1/auth/login", json={"email": user_email, "password": user_pass})

        # Setup TOTP
        resp = await async_client.post("/api/v1/auth/me/mfa/totp/setup")
        secret = resp.json()["secret"]

        # Generate valid TOTP code
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        resp = await async_client.post("/api/v1/auth/me/mfa/totp/verify", params={"code": valid_code})
        assert resp.status_code == 200
        data = resp.json()
        assert data["mfa_enabled"] is True

    @pytest.mark.asyncio
    async def test_verify_totp_invalid_code(self, db_session: AsyncSession, async_client: AsyncClient):
        """Should reject invalid TOTP code."""
        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
        await async_client.patch("/api/v1/admin/settings", json={"mfa_enabled": True})

        user_email, user_pass = await _create_user(db_session, "user4@test.com")
        await async_client.post("/api/v1/auth/login", json={"email": user_email, "password": user_pass})

        await async_client.post("/api/v1/auth/me/mfa/totp/setup")

        resp = await async_client.post("/api/v1/auth/me/mfa/totp/verify", params={"code": "000000"})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_verify_without_setup(self, db_session: AsyncSession, async_client: AsyncClient):
        """Should reject verify if setup was not called."""
        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
        await async_client.patch("/api/v1/admin/settings", json={"mfa_enabled": True})

        user_email, user_pass = await _create_user(db_session, "user5@test.com")
        await async_client.post("/api/v1/auth/login", json={"email": user_email, "password": user_pass})

        resp = await async_client.post("/api/v1/auth/me/mfa/totp/verify", params={"code": "123456"})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_disable_totp(self, db_session: AsyncSession, async_client: AsyncClient):
        """Should disable MFA with valid TOTP code."""
        import pyotp

        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
        await async_client.patch("/api/v1/admin/settings", json={"mfa_enabled": True})

        user_email, user_pass = await _create_user(db_session, "user6@test.com")
        await async_client.post("/api/v1/auth/login", json={"email": user_email, "password": user_pass})

        # Setup and verify
        resp = await async_client.post("/api/v1/auth/me/mfa/totp/setup")
        secret = resp.json()["secret"]
        totp = pyotp.TOTP(secret)
        await async_client.post("/api/v1/auth/me/mfa/totp/verify", params={"code": totp.now()})

        # Disable with TOTP code
        resp = await async_client.post("/api/v1/auth/me/mfa/totp/disable", params={"code": totp.now()})
        assert resp.status_code == 200
        assert resp.json()["message"] == "MFA disabled"

    @pytest.mark.asyncio
    async def test_disable_without_code(self, db_session: AsyncSession, async_client: AsyncClient):
        """Should reject disable without valid TOTP code."""
        import pyotp

        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
        await async_client.patch("/api/v1/admin/settings", json={"mfa_enabled": True})

        user_email, user_pass = await _create_user(db_session, "user7@test.com")
        await async_client.post("/api/v1/auth/login", json={"email": user_email, "password": user_pass})

        # Setup and verify
        resp = await async_client.post("/api/v1/auth/me/mfa/totp/setup")
        secret = resp.json()["secret"]
        totp = pyotp.TOTP(secret)
        await async_client.post("/api/v1/auth/me/mfa/totp/verify", params={"code": totp.now()})

        # Try to disable without code
        resp = await async_client.post("/api/v1/auth/me/mfa/totp/disable")
        assert resp.status_code == 403


class TestMfaLogin:
    """Test MFA-challenged login flow."""

    @pytest.mark.asyncio
    async def test_login_requires_mfa_when_enabled(self, db_session: AsyncSession, async_client: AsyncClient):
        """Login should return mfa_required when user has MFA enabled."""
        import pyotp

        # Enable MFA in system settings
        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
        await async_client.patch("/api/v1/admin/settings", json={"mfa_enabled": True})

        # Create user and enable MFA
        user_email, user_pass = await _create_user(db_session, "mfa_user@test.com")
        await async_client.post("/api/v1/auth/login", json={"email": user_email, "password": user_pass})
        resp = await async_client.post("/api/v1/auth/me/mfa/totp/setup")
        secret = resp.json()["secret"]
        totp = pyotp.TOTP(secret)
        await async_client.post("/api/v1/auth/me/mfa/totp/verify", params={"code": totp.now()})

        # Logout
        await async_client.post("/api/v1/auth/logout")

        # Login again - should require MFA
        resp = await async_client.post("/api/v1/auth/login", json={"email": user_email, "password": user_pass})
        assert resp.status_code == 200
        data = resp.json()
        assert data["mfa_required"] is True
        assert "mfa_token" in data

    @pytest.mark.asyncio
    async def test_login_mfa_verify(self, db_session: AsyncSession, async_client: AsyncClient):
        """Should complete login with valid MFA code."""
        import pyotp

        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
        await async_client.patch("/api/v1/admin/settings", json={"mfa_enabled": True})

        user_email, user_pass = await _create_user(db_session, "mfa_user2@test.com")
        await async_client.post("/api/v1/auth/login", json={"email": user_email, "password": user_pass})
        resp = await async_client.post("/api/v1/auth/me/mfa/totp/setup")
        secret = resp.json()["secret"]
        totp = pyotp.TOTP(secret)
        await async_client.post("/api/v1/auth/me/mfa/totp/verify", params={"code": totp.now()})

        await async_client.post("/api/v1/auth/logout")

        # Login to get MFA token
        resp = await async_client.post("/api/v1/auth/login", json={"email": user_email, "password": user_pass})
        mfa_token = resp.json()["mfa_token"]

        # Verify with TOTP code
        resp = await async_client.post("/api/v1/auth/login/mfa", params={
            "mfa_token": mfa_token,
            "code": totp.now(),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "MFA verified"

        # Should now be authenticated
        resp = await async_client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        assert resp.json()["email"] == user_email

    @pytest.mark.asyncio
    async def test_login_mfa_invalid_code(self, db_session: AsyncSession, async_client: AsyncClient):
        """Should reject invalid MFA code."""
        import pyotp

        email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
        await async_client.patch("/api/v1/admin/settings", json={"mfa_enabled": True})

        user_email, user_pass = await _create_user(db_session, "mfa_user3@test.com")
        await async_client.post("/api/v1/auth/login", json={"email": user_email, "password": user_pass})
        resp = await async_client.post("/api/v1/auth/me/mfa/totp/setup")
        secret = resp.json()["secret"]
        totp = pyotp.TOTP(secret)
        await async_client.post("/api/v1/auth/me/mfa/totp/verify", params={"code": totp.now()})

        await async_client.post("/api/v1/auth/logout")

        resp = await async_client.post("/api/v1/auth/login", json={"email": user_email, "password": user_pass})
        mfa_token = resp.json()["mfa_token"]

        # Verify with wrong code
        resp = await async_client.post("/api/v1/auth/login/mfa", params={
            "mfa_token": mfa_token,
            "code": "000000",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_without_mfa_works_normally(self, db_session: AsyncSession, async_client: AsyncClient):
        """Login without MFA should work normally."""
        user_email, user_pass = await _create_user(db_session, "normal@test.com")
        resp = await async_client.post("/api/v1/auth/login", json={"email": user_email, "password": user_pass})
        assert resp.status_code == 200
        data = resp.json()
        assert "mfa_required" not in data
        assert data["email"] == user_email
