"""Tests for password-reset via email (forgot/reset-password, SMTP settings)."""

import hashlib
import re
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_user(db_session: AsyncSession, email="user@test.com", password="userpass123", is_active=True) -> str:
    from app.core.security import hash_password
    from app.models.user import User

    user = User(
        email=email, display_name="Test User",
        password_hash=hash_password(password), is_admin=False, is_active=is_active,
    )
    db_session.add(user)
    await db_session.commit()
    return email


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


class _CapturedEmail:
    def __init__(self):
        self.calls: list[dict] = []

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)


class TestCrypto:
    def test_roundtrip(self, monkeypatch: pytest.MonkeyPatch):
        from app.core.config import settings
        from app.core.crypto import decrypt_secret, encrypt_secret

        monkeypatch.setattr(settings, "settings_encryption_key", Fernet.generate_key().decode())
        ciphertext = encrypt_secret("hunter2")
        assert ciphertext != "hunter2"
        assert decrypt_secret(ciphertext) == "hunter2"

    def test_encrypt_without_key_raises(self, monkeypatch: pytest.MonkeyPatch):
        from app.core.config import settings
        from app.core.crypto import SettingsEncryptionKeyError, encrypt_secret

        monkeypatch.setattr(settings, "settings_encryption_key", "")
        with pytest.raises(SettingsEncryptionKeyError):
            encrypt_secret("hunter2")


class TestForgotPassword:
    @pytest.mark.asyncio
    async def test_existing_user_sets_token_and_sends_email(
        self, db_session: AsyncSession, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        from sqlmodel import select

        from app.models.user import User

        captured = _CapturedEmail()
        monkeypatch.setattr("app.api.auth.send_email", captured)

        email = await _create_user(db_session)
        resp = await async_client.post("/api/v1/auth/forgot-password", json={"email": email})
        assert resp.status_code == 200
        assert "sent" in resp.json()["message"].lower()

        assert len(captured.calls) == 1
        assert captured.calls[0]["to"] == email

        await db_session.rollback()
        result = await db_session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        assert user.reset_token_hash is not None
        assert user.reset_token_expires_at is not None

    @pytest.mark.asyncio
    async def test_nonexistent_email_returns_generic_200(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        captured = _CapturedEmail()
        monkeypatch.setattr("app.api.auth.send_email", captured)

        resp = await async_client.post(
            "/api/v1/auth/forgot-password", json={"email": "nobody@test.com"}
        )
        assert resp.status_code == 200
        assert "sent" in resp.json()["message"].lower()
        assert len(captured.calls) == 0

    @pytest.mark.asyncio
    async def test_inactive_user_gets_no_token(
        self, db_session: AsyncSession, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        from sqlmodel import select

        from app.models.user import User

        captured = _CapturedEmail()
        monkeypatch.setattr("app.api.auth.send_email", captured)

        email = await _create_user(db_session, email="inactive@test.com", is_active=False)
        resp = await async_client.post("/api/v1/auth/forgot-password", json={"email": email})
        assert resp.status_code == 200
        assert len(captured.calls) == 0

        await db_session.rollback()
        result = await db_session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        assert user.reset_token_hash is None

    @pytest.mark.asyncio
    async def test_email_send_failure_still_returns_generic_200(
        self, db_session: AsyncSession, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        from app.services.email import EmailSendError

        async def _boom(**kwargs):
            raise EmailSendError("smtp down")

        monkeypatch.setattr("app.api.auth.send_email", _boom)

        email = await _create_user(db_session)
        resp = await async_client.post("/api/v1/auth/forgot-password", json={"email": email})
        assert resp.status_code == 200


class TestResetPassword:
    async def _request_reset_and_get_token(
        self, db_session: AsyncSession, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch, email: str
    ) -> str:
        captured = _CapturedEmail()
        monkeypatch.setattr("app.api.auth.send_email", captured)
        resp = await async_client.post("/api/v1/auth/forgot-password", json={"email": email})
        assert resp.status_code == 200
        body = captured.calls[0]["text_body"]
        match = re.search(r"token=([A-Za-z0-9_\-]+)", body)
        assert match, f"No token found in email body: {body}"
        return match.group(1)

    @pytest.mark.asyncio
    async def test_valid_token_resets_password(
        self, db_session: AsyncSession, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        email = await _create_user(db_session)
        token = await self._request_reset_and_get_token(db_session, async_client, monkeypatch, email)

        resp = await async_client.post(
            "/api/v1/auth/reset-password", json={"token": token, "new_password": "brandnewpass123"}
        )
        assert resp.status_code == 200

        resp = await async_client.post(
            "/api/v1/auth/login", json={"email": email, "password": "brandnewpass123"}
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_token_is_single_use(
        self, db_session: AsyncSession, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        email = await _create_user(db_session)
        token = await self._request_reset_and_get_token(db_session, async_client, monkeypatch, email)

        resp = await async_client.post(
            "/api/v1/auth/reset-password", json={"token": token, "new_password": "brandnewpass123"}
        )
        assert resp.status_code == 200

        resp = await async_client.post(
            "/api/v1/auth/reset-password", json={"token": token, "new_password": "anotherpass456"}
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"token": "not-a-real-token", "new_password": "brandnewpass123"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self, db_session: AsyncSession, async_client: AsyncClient):
        from app.models.user import User

        token = "a-known-plaintext-token"
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        user = User(
            email="expired@test.com", display_name="Expired",
            reset_token_hash=token_hash,
            reset_token_expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        db_session.add(user)
        await db_session.commit()

        resp = await async_client.post(
            "/api/v1/auth/reset-password", json={"token": token, "new_password": "brandnewpass123"}
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_new_password_too_short(
        self, db_session: AsyncSession, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        email = await _create_user(db_session)
        token = await self._request_reset_and_get_token(db_session, async_client, monkeypatch, email)

        resp = await async_client.post(
            "/api/v1/auth/reset-password", json={"token": token, "new_password": "short"}
        )
        assert resp.status_code == 422


class TestSmtpTestEndpoint:
    @pytest.mark.asyncio
    async def test_requires_admin(self, db_session: AsyncSession, async_client: AsyncClient):
        email = await _create_user(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": email, "password": "userpass123"})

        resp = await async_client.post("/api/v1/admin/settings/smtp/test", json={})
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_missing_host_returns_400(self, db_session: AsyncSession, async_client: AsyncClient):
        admin_email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": admin_email, "password": password})

        resp = await async_client.post("/api/v1/admin/settings/smtp/test", json={})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_sends_with_overrides(
        self, db_session: AsyncSession, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        captured = _CapturedEmail()
        monkeypatch.setattr("app.api.admin.send_email", captured)

        admin_email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": admin_email, "password": password})

        resp = await async_client.post(
            "/api/v1/admin/settings/smtp/test",
            json={"host": "smtp.example.com", "port": 587, "from_email": "noreply@example.com"},
        )
        assert resp.status_code == 200
        assert len(captured.calls) == 1
        assert captured.calls[0]["to"] == admin_email


class TestAdminSettingsSmtpFields:
    @pytest.mark.asyncio
    async def test_update_smtp_password_requires_encryption_key(
        self, db_session: AsyncSession, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "settings_encryption_key", "")
        admin_email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": admin_email, "password": password})

        resp = await async_client.patch(
            "/api/v1/admin/settings", json={"smtp_password": "hunter2"}
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_smtp_password_encrypts_and_hides_it(
        self, db_session: AsyncSession, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "settings_encryption_key", Fernet.generate_key().decode())
        admin_email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": admin_email, "password": password})

        resp = await async_client.patch(
            "/api/v1/admin/settings",
            json={"smtp_host": "smtp.example.com", "smtp_password": "hunter2"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["smtp_password_set"] is True
        assert "smtp_password" not in data
        assert data["smtp_host"] == "smtp.example.com"

        resp = await async_client.get("/api/v1/admin/settings")
        assert resp.json()["smtp_password_set"] is True

    @pytest.mark.asyncio
    async def test_clearing_smtp_password(
        self, db_session: AsyncSession, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "settings_encryption_key", Fernet.generate_key().decode())
        admin_email, password = await _create_admin(db_session)
        await async_client.post("/api/v1/auth/login", json={"email": admin_email, "password": password})

        await async_client.patch("/api/v1/admin/settings", json={"smtp_password": "hunter2"})
        resp = await async_client.patch("/api/v1/admin/settings", json={"smtp_password": ""})
        assert resp.status_code == 200
        assert resp.json()["smtp_password_set"] is False
