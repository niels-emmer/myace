"""Auth hardening: SSO email linking, registration gate, rate limits, MFA body
params, TOTP re-setup, and admin-only doc-cache deletion."""

from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from httpx import ASGITransport, AsyncClient
from httpx import AsyncClient as _BareClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from starlette.responses import RedirectResponse

from app.core.config import settings
from app.core.ratelimit import auth_limiter
from app.core.security import hash_password
from app.main import app as fastapi_app
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


# ─── L-1: register must not leak account existence ────────────────

REGISTER_BODY = {
    "email": "probe@example.com",
    "password": "password123",
    "display_name": "Probe Name",
}


@pytest.mark.asyncio
async def test_register_response_does_not_leak_account_existence(
    async_client: AsyncClient,
) -> None:
    """The duplicate-email response must be indistinguishable from a real
    registration: echoing `display_name` (rather than hardcoding "") is what
    stops the body being an account-existence oracle."""
    created = await async_client.post("/api/v1/auth/register", json=REGISTER_BODY)
    assert created.status_code == 201

    duplicate = await async_client.post("/api/v1/auth/register", json=REGISTER_BODY)
    fresh = await async_client.post(
        "/api/v1/auth/register", json={**REGISTER_BODY, "email": "other@example.com"}
    )

    assert duplicate.status_code == fresh.status_code == 201
    # `email` differs because the caller sent a different one; `id`/`created_at`
    # are volatile by design. Everything else must match exactly.
    volatile = {"id", "created_at", "email"}
    assert {k: v for k, v in duplicate.json().items() if k not in volatile} == {
        k: v for k, v in fresh.json().items() if k not in volatile
    }
    assert duplicate.json()["display_name"] == REGISTER_BODY["display_name"]


@pytest.mark.asyncio
async def test_register_duplicate_email_still_pays_the_hashing_cost(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The duplicate path skips the insert, so it must still run the same
    bcrypt work — otherwise response latency alone reveals whether the address
    is registered."""
    import app.api.auth as auth_module

    await async_client.post("/api/v1/auth/register", json=REGISTER_BODY)

    seen: list[str] = []
    real_hash = auth_module.hash_password

    def _spy(password: str) -> str:
        seen.append(password)
        return real_hash(password)

    monkeypatch.setattr(auth_module, "hash_password", _spy)

    resp = await async_client.post("/api/v1/auth/register", json=REGISTER_BODY)
    assert resp.status_code == 201
    assert seen == [REGISTER_BODY["password"]]


# ─── L-3: password change is throttled and revokes API tokens ─────


@pytest.mark.asyncio
async def test_change_password_is_rate_limited(
    async_client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`change_password` verifies the current password, so it needs the same
    per-client-IP throttle `/auth/login` has."""
    await _add_user(db_session, "rl@example.com")
    # Log in while the limiter is off so only the password-change calls count.
    await async_client.post(
        "/api/v1/auth/login", json={"email": "rl@example.com", "password": "password123"}
    )

    auth_limiter.enabled = True
    auth_limiter.reset()
    monkeypatch.setattr(settings, "auth_rate_limit", "3/minute")

    body = {"current_password": "wrong-password", "new_password": "newpassword123"}
    codes = [
        (await async_client.post("/api/v1/auth/me/password", json=body)).status_code
        for _ in range(5)
    ]
    assert codes == [403, 403, 403, 429, 429]


@pytest.mark.asyncio
async def test_change_password_invalidates_tokens(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """A password change is the response to a suspected compromise, so API
    tokens minted before it must stop working — while the caller's own session
    keeps working."""
    await _add_user(db_session, "tok@example.com")
    await async_client.post(
        "/api/v1/auth/login", json={"email": "tok@example.com", "password": "password123"}
    )
    api_key = (
        await async_client.post("/api/v1/auth/tokens", json={"name": "cli"})
    ).json()["token"]

    async def _token_is_accepted() -> bool:
        # A cookie-less client, so only the Bearer token can authenticate.
        async with _BareClient(
            transport=ASGITransport(app=fastapi_app), base_url="http://test"
        ) as bare:
            resp = await bare.get(
                "/api/v1/auth/tokens", headers={"Authorization": f"Bearer {api_key}"}
            )
            return resp.status_code == 200

    assert await _token_is_accepted() is True

    changed = await async_client.post(
        "/api/v1/auth/me/password",
        json={"current_password": "password123", "new_password": "newpassword123"},
    )
    assert changed.status_code == 200

    assert await _token_is_accepted() is False
    # The caller's own (re-issued) session still works.
    assert (await async_client.get("/api/v1/auth/me")).status_code == 200


# ─── L-2: forgot-password must not await the SMTP send ────────────


@pytest.mark.asyncio
async def test_forgot_password_does_not_wait_for_the_smtp_send(
    async_client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Awaiting the SMTP round-trip inline made the response time depend on
    whether the account exists — a user-enumeration oracle (L-2). The send must
    happen off the request path."""
    import asyncio

    await _add_user(db_session, "reset@example.com")
    started = asyncio.Event()
    release = asyncio.Event()

    async def _blocked_send(**kwargs: object) -> None:
        started.set()
        await release.wait()

    monkeypatch.setattr("app.api.auth.send_email", _blocked_send)

    # `wait_for` fails the test instead of hanging if the handler awaits the send.
    resp = await asyncio.wait_for(
        async_client.post(
            "/api/v1/auth/forgot-password", json={"email": "reset@example.com"}
        ),
        timeout=2,
    )
    assert resp.status_code == 200
    release.set()
