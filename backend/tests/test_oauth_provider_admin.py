"""Tests for admin-editable OAuth provider credentials (System Settings UI)."""

import pytest
from cryptography.fernet import Fernet
from httpx import AsyncClient
from pytest_httpx import HTTPXMock
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_admin(db_session: AsyncSession) -> tuple[str, str]:
    from app.core.security import hash_password
    from app.models.user import User

    user = User(
        email="admin@test.com", display_name="Admin",
        password_hash=hash_password("adminpass123"), is_admin=True,
    )
    db_session.add(user)
    await db_session.commit()
    return "admin@test.com", "adminpass123"


async def _login_admin(async_client: AsyncClient, db_session: AsyncSession) -> None:
    email, password = await _create_admin(db_session)
    resp = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


class TestOAuthCredentialStorage:
    @pytest.mark.asyncio
    async def test_saving_client_secret_requires_encryption_key(
        self, db_session: AsyncSession, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "settings_encryption_key", "")
        await _login_admin(async_client, db_session)

        resp = await async_client.patch(
            "/api/v1/admin/settings", json={"github_client_secret": "secret123"}
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_saving_and_reading_provider_credentials(
        self, db_session: AsyncSession, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "settings_encryption_key", Fernet.generate_key().decode())
        await _login_admin(async_client, db_session)

        resp = await async_client.patch("/api/v1/admin/settings", json={
            "github_client_id": "gh-client-id",
            "github_client_secret": "gh-secret",
            "google_client_id": "google-client-id",
            "google_client_secret": "google-secret",
            "oidc_client_id": "oidc-client-id",
            "oidc_client_secret": "oidc-secret",
            "oidc_issuer_url": "https://auth.example.com",
            "oidc_scopes": "openid email",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["github_client_id"] == "gh-client-id"
        assert data["github_client_secret_set"] is True
        assert "github_client_secret" not in data
        assert data["google_client_secret_set"] is True
        assert data["oidc_client_secret_set"] is True
        assert data["oidc_issuer_url"] == "https://auth.example.com"
        assert data["oidc_scopes"] == "openid email"

        resp = await async_client.get("/api/v1/admin/settings")
        data = resp.json()
        assert data["github_client_secret_set"] is True

    @pytest.mark.asyncio
    async def test_clearing_provider_secret(
        self, db_session: AsyncSession, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "settings_encryption_key", Fernet.generate_key().decode())
        await _login_admin(async_client, db_session)

        await async_client.patch(
            "/api/v1/admin/settings",
            json={"github_client_id": "gh-id", "github_client_secret": "gh-secret"},
        )
        resp = await async_client.patch("/api/v1/admin/settings", json={"github_client_secret": ""})
        assert resp.status_code == 200
        assert resp.json()["github_client_secret_set"] is False


class TestDbCredentialsActivateProvider:
    @pytest.mark.asyncio
    async def test_provider_reports_configured_once_saved_via_db(
        self, db_session: AsyncSession, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        """A provider with no env vars set should still be reported as
        configured, and its login route should redirect instead of
        400ing, once an admin saves credentials via System Settings —
        proving DB-saved OAuth credentials take effect without a restart."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "settings_encryption_key", Fernet.generate_key().decode())
        await _login_admin(async_client, db_session)

        resp = await async_client.get("/api/v1/auth/providers")
        assert resp.json()["github"] is False

        resp = await async_client.get("/api/v1/auth/login/github")
        assert resp.status_code == 400
        assert "not configured" in resp.text.lower()

        await async_client.patch(
            "/api/v1/admin/settings",
            json={"github_client_id": "gh-id", "github_client_secret": "gh-secret"},
        )

        resp = await async_client.get("/api/v1/auth/providers")
        assert resp.json()["github"] is True

        resp = await async_client.get("/api/v1/auth/login/github", follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert "github.com" in resp.headers["location"]


class TestOAuthProviderTestEndpoint:
    @pytest.mark.asyncio
    async def test_requires_admin(self, db_session: AsyncSession, async_client: AsyncClient):
        from app.core.security import hash_password
        from app.models.user import User

        user = User(
            email="user@test.com", display_name="User",
            password_hash=hash_password("userpass123"), is_admin=False,
        )
        db_session.add(user)
        await db_session.commit()
        await async_client.post("/api/v1/auth/login", json={"email": "user@test.com", "password": "userpass123"})

        resp = await async_client.post("/api/v1/admin/settings/oauth/github/test", json={})
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unknown_provider(self, db_session: AsyncSession, async_client: AsyncClient):
        await _login_admin(async_client, db_session)
        resp = await async_client.post("/api/v1/admin/settings/oauth/bogus/test", json={})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_credentials(self, db_session: AsyncSession, async_client: AsyncClient):
        await _login_admin(async_client, db_session)
        resp = await async_client.post("/api/v1/admin/settings/oauth/github/test", json={})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_github_reachable(
        self, db_session: AsyncSession, async_client: AsyncClient, httpx_mock: HTTPXMock
    ):
        await _login_admin(async_client, db_session)
        httpx_mock.add_response(status_code=200)

        resp = await async_client.post(
            "/api/v1/admin/settings/oauth/github/test",
            json={"client_id": "gh-id", "client_secret": "gh-secret"},
        )
        assert resp.status_code == 200
        assert "reachable" in resp.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_oidc_requires_issuer_url(self, db_session: AsyncSession, async_client: AsyncClient):
        await _login_admin(async_client, db_session)
        resp = await async_client.post(
            "/api/v1/admin/settings/oauth/oidc/test",
            json={"client_id": "oidc-id", "client_secret": "oidc-secret"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_oidc_discovery_success(
        self, db_session: AsyncSession, async_client: AsyncClient, httpx_mock: HTTPXMock
    ):
        await _login_admin(async_client, db_session)
        httpx_mock.add_response(
            url="https://auth.example.com/.well-known/openid-configuration",
            json={"authorization_endpoint": "https://auth.example.com/authorize",
                  "token_endpoint": "https://auth.example.com/token"},
        )

        resp = await async_client.post(
            "/api/v1/admin/settings/oauth/oidc/test",
            json={
                "client_id": "oidc-id", "client_secret": "oidc-secret",
                "issuer_url": "https://auth.example.com",
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_oidc_discovery_missing_endpoints(
        self, db_session: AsyncSession, async_client: AsyncClient, httpx_mock: HTTPXMock
    ):
        await _login_admin(async_client, db_session)
        httpx_mock.add_response(
            url="https://auth.example.com/.well-known/openid-configuration", json={"issuer": "x"}
        )

        resp = await async_client.post(
            "/api/v1/admin/settings/oauth/oidc/test",
            json={
                "client_id": "oidc-id", "client_secret": "oidc-secret",
                "issuer_url": "https://auth.example.com",
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_connectivity_failure(
        self, db_session: AsyncSession, async_client: AsyncClient, httpx_mock: HTTPXMock
    ):
        import httpx

        await _login_admin(async_client, db_session)
        httpx_mock.add_exception(httpx.ConnectError("boom"))

        resp = await async_client.post(
            "/api/v1/admin/settings/oauth/google/test",
            json={"client_id": "g-id", "client_secret": "g-secret"},
        )
        assert resp.status_code == 400
