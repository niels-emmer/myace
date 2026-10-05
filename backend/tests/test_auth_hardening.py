"""Auth hardening: SSO email linking, registration gate, rate limits, MFA body
params, TOTP re-setup, and admin-only doc-cache deletion."""

from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from starlette.responses import RedirectResponse

from app.core.config import settings
from app.core.ratelimit import auth_limiter
from app.core.security import hash_password
from app.models.doc_cache import DocCacheEntry
from app.models.system_settings import SystemSettings
from app.models.user import User


class FakeOidcClient:
    def __init__(self, userinfo: dict[str, object]) -> None:
        self._userinfo = userinfo

    async def authorize_redirect(self, request, redirect_uri, **kwargs):  # noqa: ANN001
        return RedirectResponse(url="https://idp.example.com/authorize", status_code=302)

    async def authorize_access_token(self, request, **kwargs):  # noqa: ANN001
        return {"access_token": "t", "userinfo": self._userinfo}


async def _sso_login(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, userinfo: dict[str, object]
) -> int:
    fake = FakeOidcClient(userinfo)
    monkeypatch.setattr("app.api.auth.get_oauth_client", lambda provider, config: fake)
    await client.get("/api/v1/auth/login/oidc", follow_redirects=False)
    resp = await client.get(
        "/api/v1/auth/callback/oidc?code=c&state=s", follow_redirects=False
    )
    return resp.status_code


async def _add_user(
    db: AsyncSession, email: str, *, is_admin: bool = False, **kwargs: object
) -> User:
    user = User(
        email=email, display_name="U", password_hash=hash_password("password123"),
        is_admin=is_admin, role="admin" if is_admin else "user", **kwargs,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_sso_will_not_link_unverified_email_to_existing_account(
    async_client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _add_user(db_session, "victim@example.com")
    status = await _sso_login(
        async_client, monkeypatch,
        {"sub": "attacker-sub", "email": "victim@example.com", "email_verified": False},
    )
    assert status == 403
    user = (await db_session.execute(select(User))).scalar_one()
    await db_session.refresh(user)
    assert user.oidc_sub is None
    assert (await async_client.get("/api/v1/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_sso_links_verified_email_to_existing_account(
    async_client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _add_user(db_session, "me@example.com")
    for verified in (True, "true"):
        status = await _sso_login(
            async_client, monkeypatch,
            {"sub": "s1", "email": "me@example.com", "email_verified": verified},
        )
        assert status == 302
        await async_client.post("/api/v1/auth/logout")
    user = (await db_session.execute(select(User))).scalar_one()
    await db_session.refresh(user)
    assert (user.oidc_sub, user.oidc_provider) == ("s1", "oidc")


@pytest.mark.asyncio
async def test_sso_will_not_repoint_account_linked_to_another_identity(
    async_client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _add_user(
        db_session, "linked@example.com", oidc_sub="original", oidc_provider="google"
    )
    status = await _sso_login(
        async_client, monkeypatch,
        {"sub": "other", "email": "linked@example.com", "email_verified": True},
    )
    assert status == 403
    user = (await db_session.execute(select(User))).scalar_one()
    await db_session.refresh(user)
    assert (user.oidc_sub, user.oidc_provider) == ("original", "google")


@pytest.mark.asyncio
async def test_sso_signup_blocked_when_registration_disabled(
    async_client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_session.add(SystemSettings(id=1, allow_registration=False))
    await db_session.commit()
    status = await _sso_login(
        async_client, monkeypatch,
        {"sub": "new", "email": "new@example.com", "email_verified": True},
    )
    assert status == 403
    assert (await db_session.execute(select(User))).scalars().all() == []


@pytest.mark.asyncio
async def test_sso_signup_still_works_when_registration_enabled(
    async_client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    status = await _sso_login(
        async_client, monkeypatch, {"sub": "new", "email": "new@example.com"}
    )
    assert status == 302


@pytest.mark.asyncio
async def test_login_is_rate_limited_per_client(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth_limiter.enabled = True
    auth_limiter.reset()
    monkeypatch.setattr(settings, "auth_rate_limit", "3/minute")
    body = {"email": "nobody@example.com", "password": "wrong-password"}
    codes = [(await async_client.post("/api/v1/auth/login", json=body)).status_code
             for _ in range(5)]
    assert codes == [401, 401, 401, 429, 429]
    limited = await async_client.post("/api/v1/auth/login", json=body)
    assert "Rate limit exceeded" in limited.json()["detail"]


async def _mfa_user(db: AsyncSession) -> tuple[User, str]:
    secret = pyotp.random_base32()
    user = await _add_user(db, "mfa@example.com", mfa_enabled=True, totp_secret=secret)
    return user, secret


@pytest.mark.asyncio
async def test_mfa_login_accepts_json_body(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, secret = await _mfa_user(db_session)
    login = await async_client.post(
        "/api/v1/auth/login", json={"email": "mfa@example.com", "password": "password123"}
    )
    token = login.json()["mfa_token"]
    res = await async_client.post(
        "/api/v1/auth/login/mfa",
        json={"mfa_token": token, "code": pyotp.TOTP(secret).now()},
    )
    assert res.status_code == 200
    assert (await async_client.get("/api/v1/auth/me")).status_code == 200


@pytest.mark.asyncio
async def test_mfa_login_query_params_still_work_but_are_required_somewhere(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, secret = await _mfa_user(db_session)
    token = (await async_client.post(
        "/api/v1/auth/login", json={"email": "mfa@example.com", "password": "password123"}
    )).json()["mfa_token"]
    assert (await async_client.post("/api/v1/auth/login/mfa")).status_code == 422
    res = await async_client.post(
        "/api/v1/auth/login/mfa", params={"mfa_token": token, "code": pyotp.TOTP(secret).now()}
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_totp_verify_and_disable_accept_json_body(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    secret = pyotp.random_base32()
    await _add_user(db_session, "totp@example.com", totp_secret=secret)
    await async_client.post(
        "/api/v1/auth/login", json={"email": "totp@example.com", "password": "password123"}
    )
    ok = await async_client.post(
        "/api/v1/auth/me/mfa/totp/verify", json={"code": pyotp.TOTP(secret).now()}
    )
    assert ok.status_code == 200
    assert (await async_client.post(
        "/api/v1/auth/me/mfa/totp/verify", json={"code": "000000"}
    )).status_code == 400
    off = await async_client.post(
        "/api/v1/auth/me/mfa/totp/disable", json={"code": pyotp.TOTP(secret).now()}
    )
    assert off.status_code == 200


@pytest.mark.asyncio
async def test_totp_setup_refuses_to_replace_an_enabled_secret(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    user, secret = await _mfa_user(db_session)
    login = await async_client.post(
        "/api/v1/auth/login", json={"email": "mfa@example.com", "password": "password123"}
    )
    token = login.json()["mfa_token"]
    await async_client.post(
        "/api/v1/auth/login/mfa", json={"mfa_token": token, "code": pyotp.TOTP(secret).now()}
    )
    res = await async_client.post("/api/v1/auth/me/mfa/totp/setup")
    assert res.status_code == 400
    await db_session.refresh(user)
    assert user.totp_secret == secret


async def _cache_entry(db: AsyncSession) -> DocCacheEntry:
    now = datetime.now(UTC)
    entry = DocCacheEntry(
        framework="claude-code", url="https://example.com/doc", content_hash="h",
        content="c", expires_at=now + timedelta(days=7),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@pytest.mark.asyncio
async def test_doc_cache_delete_is_admin_only(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    entry = await _cache_entry(db_session)
    await _add_user(db_session, "plain@example.com")
    await _add_user(db_session, "boss@example.com", is_admin=True)

    await async_client.post(
        "/api/v1/auth/login", json={"email": "plain@example.com", "password": "password123"}
    )
    assert (await async_client.delete(f"/api/v1/doc-cache/{entry.id}")).status_code == 403

    await async_client.post("/api/v1/auth/logout")
    await async_client.post(
        "/api/v1/auth/login", json={"email": "boss@example.com", "password": "password123"}
    )
    assert (await async_client.delete(f"/api/v1/doc-cache/{entry.id}")).status_code == 200
