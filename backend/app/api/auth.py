"""Authentication routes — email/password, OIDC login, callback, token management."""

import asyncio
import base64
import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from authlib.integrations.starlette_client.apps import StarletteOAuth2App
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.core.authz import authorize_access
from app.core.config import settings
from app.core.database import get_session
from app.core.deps import UNAUTHORIZED, get_current_user, require_admin
from app.core.ratelimit import auth_limiter
from app.core.security import (
    default_token_expiry,
    generate_api_key,
    generate_oidc_state,
    get_oauth_client,
    hash_api_key,
    hash_password,
    verify_password,
)
from app.models.system_settings import SystemSettings
from app.models.token import ApiToken, ApiTokenCreate, ApiTokenCreateResponse, ApiTokenRead
from app.models.user import (
    ForgotPasswordRequest,
    PasswordChange,
    ResetPasswordRequest,
    User,
    UserLogin,
    UserRead,
    UserRegister,
    UserRoleUpdate,
    UserUpdate,
)
from app.services.effective_settings import (
    SmtpConfig,
    get_effective_oauth_config,
    get_effective_smtp_config,
)
from app.services.email import EmailSendError, build_password_reset_email, send_email

logger = logging.getLogger("myace")

router = APIRouter()

RESET_TOKEN_TTL = timedelta(hours=1)


def _auth_limit() -> str:
    return settings.auth_rate_limit


def _mfa_limit() -> str:
    return settings.mfa_rate_limit


# Fire-and-forget email sends. The task holds a strong reference here so the
# event loop cannot garbage-collect it mid-flight; the done-callback drops it.
_background_tasks: set[asyncio.Task[None]] = set()


async def _send_password_reset_email(
    config: SmtpConfig, to: str, subject: str, body: str
) -> None:
    """Send a password-reset email outside the request. Must not touch the
    request's `AsyncSession` — it is closed by the time this runs."""
    try:
        await send_email(config=config, to=to, subject=subject, text_body=body)
    except EmailSendError:
        logger.exception("Failed to send password-reset email to a user.")


class TotpCodeRequest(BaseModel):
    """Body for the TOTP verify/disable routes. A one-time code in a query
    string ends up in access logs and browser history, so it travels in the
    body; the `code` query parameter is still accepted as a deprecated
    fallback for existing clients."""
    code: str


class MfaLoginRequest(BaseModel):
    """Body for POST /auth/login/mfa — same reasoning as `TotpCodeRequest`,
    plus `mfa_token` is a bearer credential for the second login step."""
    mfa_token: str
    code: str


def _body_or_query(body_value: str | None, query_value: str | None, name: str) -> str:
    value = body_value if body_value is not None else query_value
    if value is None:
        raise HTTPException(status_code=422, detail=f"{name} is required")
    return value


async def _registration_allowed(session: AsyncSession) -> bool:
    result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
    sys_settings = result.scalar_one_or_none()
    return not sys_settings or sys_settings.allow_registration


async def _is_bootstrap_admin(session: AsyncSession, email: str) -> bool:
    """First-ever user becomes admin (while ADMIN_BOOTSTRAP_ENABLED); emails in
    ADMIN_EMAILS are always promoted regardless."""
    if email.lower() in settings.admin_email_list:
        return True
    if not settings.admin_bootstrap_enabled:
        return False
    count = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    return count == 0


async def _promote_if_admin_email(session: AsyncSession, user: User) -> None:
    """Promote an account whose address is in ADMIN_EMAILS.

    `.env.example` documents the variable as "auto-promoted to admin on
    register/login", but it was only ever consulted on register and on SSO
    account creation — an operator adding an *existing* user's address got
    nothing, and their fallback (hand-editing the row) can leave `is_admin`
    and `role` out of sync. Both are set here together, as rule 30 requires,
    or the user is an "admin" who still fails `require_moderator_or_admin`.

    Runs once the password has been verified, before the second factor: the
    promotion is the operator's declared intent for that specific address, and
    without a session it grants nothing.
    """
    if user.is_admin and user.role == "admin":
        return
    if user.email.lower() not in settings.admin_email_list:
        return
    user.is_admin = True
    user.role = "admin"
    user.updated_at = datetime.now(UTC)
    session.add(user)
    await session.commit()
    await session.refresh(user)


# Session key for the short-lived "enrolment session" issued when `mfa_forced`
# blocks a login. It is deliberately *not* `user_id`: `get_current_user()`
# (core/deps.py) resolves only `user_id`, so this authenticates nothing in the
# app except the two TOTP enrolment routes below.
_MFA_ENROLL_SESSION_KEY = "mfa_enroll_user_id"


async def _mfa_forced(session: AsyncSession) -> bool:
    """Whether an admin has made MFA mandatory for every account.

    Requires `mfa_enabled` *and* `mfa_forced`: `setup_totp()` refuses to run
    when the feature is off, so enforcing `mfa_forced` alone would lock every
    unenrolled account out with no way to comply. The admin UI only offers the
    Force MFA toggle when `mfa_enabled` is on, so this matches what an operator
    can actually configure.
    """
    result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
    sys_settings = result.scalar_one_or_none()
    return bool(sys_settings and sys_settings.mfa_enabled and sys_settings.mfa_forced)


async def _enrolling_user(request: Request, session: AsyncSession) -> User | None:
    """Resolve the caller from the enrolment session, if one is present."""
    raw_user_id = request.session.get(_MFA_ENROLL_SESSION_KEY)
    if not raw_user_id:
        return None
    try:
        user_id = uuid.UUID(raw_user_id)
    except ValueError:
        return None
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user if user and user.is_active else None


async def _current_user_or_enrolling(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Auth for the TOTP enrolment routes.

    Accepts a normal session cookie or Bearer API token (unchanged), or — when
    `mfa_forced` blocked the login — the enrolment session issued by
    `login_with_password()`/`auth_callback()`. That session carries no
    `user_id`, so it reaches only these two routes; everything else in the app
    still 401s until enrolment is complete.
    """
    try:
        return await get_current_user(request, session)
    except HTTPException:
        pass

    user = await _enrolling_user(request, session)
    if user is None:
        raise UNAUTHORIZED
    return user


# ─── Email + Password Auth ─────────────────────────────────────

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@auth_limiter.limit(_auth_limit)
async def register(
    request: Request,
    data: UserRegister,
    session: AsyncSession = Depends(get_session),
):
    """Register a new account with email + password."""
    if len(data.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    if not await _registration_allowed(session):
        raise HTTPException(status_code=403, detail="Registration is disabled")

    result = await session.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        # Return a generic success response to prevent user enumeration.
        # Do NOT set the session or return the real user — the caller should
        # proceed to login with their password. Returning a fake UserRead
        # avoids leaking whether the email exists while keeping the same
        # response shape.
        #
        # It must be indistinguishable in *body* and *latency*, or it becomes
        # an account-existence oracle (rule 6 of the review's L-1):
        #  - echo `data.display_name` — hardcoding "" leaked the answer, since
        #    the real path echoes whatever the caller supplied; and
        #  - pay the same bcrypt cost, since this path skips the insert.
        hash_password(data.password)
        return UserRead(
            id=uuid.uuid4(), email=data.email, display_name=data.display_name,
            is_active=True, is_admin=False,
            created_at=datetime.now(UTC),
        )

    is_admin = await _is_bootstrap_admin(session, data.email)
    user = User(
        email=data.email,
        display_name=data.display_name,
        password_hash=hash_password(data.password),
        is_admin=is_admin,
        role="admin" if is_admin else "user",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    request.session["user_id"] = str(user.id)
    return user


@router.post("/login")
@auth_limiter.limit(_auth_limit)
async def login_with_password(
    request: Request,
    data: UserLogin,
    session: AsyncSession = Depends(get_session),
):
    """Log in with email + password.

    If the user has MFA enabled, returns an mfa_token instead of setting the
    session. The caller must then POST to /api/v1/auth/login/mfa with the
    token and a TOTP code to complete authentication.
    """
    result = await session.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if (
        not user
        or not user.password_hash
        or not verify_password(data.password, user.password_hash)
        or not user.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    await _promote_if_admin_email(session, user)

    # Check if MFA is required
    if user.mfa_enabled:
        return {
            "mfa_required": True,
            "mfa_token": _issue_mfa_token(user),
            "message": "MFA code required",
        }

    # An admin can make MFA mandatory for every account. An unenrolled user is
    # blocked here — no session — and given a session that can only reach the
    # TOTP enrolment routes, so they can comply rather than being locked out.
    if await _mfa_forced(session):
        request.session[_MFA_ENROLL_SESSION_KEY] = str(user.id)
        return {
            "mfa_enrollment_required": True,
            "message": (
                "MFA is required on this server. Set up an authenticator app to continue."
            ),
        }

    request.session["user_id"] = str(user.id)
    # This route has no response_model (it also returns the mfa_required
    # dict above), so returning `user` directly would serialize the raw
    # ORM row via jsonable_encoder — including password_hash, totp_secret,
    # and reset_token_hash. Must go through UserRead explicitly to filter
    # to public fields, same as every other user-serializing route.
    return UserRead.model_validate(user)


@router.post("/logout")
async def logout(request: Request):
    """Clear the current session."""
    request.session.clear()
    return {"message": "Logged out"}


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update the current user's profile (display_name, email)."""
    update_data = data.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] != current_user.email:
        # Check email uniqueness
        result = await session.execute(
            select(User).where(User.email == update_data["email"], User.id != current_user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already in use")

    for field, value in update_data.items():
        setattr(current_user, field, value)

    current_user.updated_at = datetime.now(UTC)
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return current_user


@router.post("/me/password")
@auth_limiter.limit(_auth_limit)
async def change_password(
    request: Request,
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Change the current user's password.

    Rate-limited like the other credential-checking routes: the current
    password is verified here, so unbounded attempts would be the same
    guessing primitive `/auth/login` is throttled against.

    A successful change deactivates the user's API tokens (a password change
    is what you do after a suspected compromise) and re-issues the caller's
    own session cookie. Outstanding *other* session cookies cannot be revoked
    — sessions are stateless signed cookies (the accepted trade-off recorded
    in docs/invariants.md), which is why the token revocation matters.
    """
    if not current_user.password_hash:
        raise HTTPException(status_code=400, detail="Cannot change password for OIDC-only accounts")

    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=403, detail="Current password is incorrect")

    if len(data.new_password) < 8:
        raise HTTPException(status_code=422, detail="New password must be at least 8 characters")

    current_user.password_hash = hash_password(data.new_password)
    current_user.updated_at = datetime.now(UTC)
    session.add(current_user)

    result = await session.execute(
        select(ApiToken).where(ApiToken.user_id == current_user.id, ApiToken.is_active == True)
    )
    for token in result.scalars().all():
        token.is_active = False
        session.add(token)

    await session.commit()

    # Re-issue the caller's own session so the cookie reflects the change.
    request.session.clear()
    request.session["user_id"] = str(current_user.id)
    return {"message": "Password updated"}


@router.post("/forgot-password")
@auth_limiter.limit(_auth_limit)
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_session),
):
    """Request a password-reset email.

    Always returns a generic 200 regardless of whether the email exists or
    the account has no password (OIDC-only) — same enumeration-prevention
    convention as /auth/register. The reset link is only emailed, and the
    token is only stored hashed, mirroring the API-token pattern.
    """
    generic_response = {
        "message": "If that email is registered, a password reset link has been sent."
    }

    result = await session.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return generic_response

    token = secrets.token_urlsafe(32)
    user.reset_token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    user.reset_token_expires_at = datetime.now(UTC) + RESET_TOKEN_TTL
    session.add(user)
    await session.commit()

    reset_link = f"{settings.frontend_base_url.rstrip('/')}/reset-password?token={token}"
    subject, body = build_password_reset_email(reset_link)
    # Resolve the effective SMTP config on the request path (a cheap DB read),
    # then hand the actual send to a background task. Awaiting the SMTP
    # round-trip here made the response time depend on whether the address
    # exists — a user-enumeration oracle — and held a worker for its duration.
    config = await get_effective_smtp_config(session)
    if config.enabled:
        task = asyncio.create_task(
            _send_password_reset_email(config, user.email, subject, body)
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    else:
        logger.warning("Password reset requested but SMTP is disabled in System Settings.")

    return generic_response


@router.post("/reset-password")
@auth_limiter.limit(_auth_limit)
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
):
    """Complete a password reset using a token from /auth/forgot-password."""
    if len(data.new_password) < 8:
        raise HTTPException(status_code=422, detail="New password must be at least 8 characters")

    token_hash = hashlib.sha256(data.token.encode("utf-8")).hexdigest()
    result = await session.execute(select(User).where(User.reset_token_hash == token_hash))
    user = result.scalar_one_or_none()

    now = datetime.now(UTC)
    if (
        not user
        or not user.is_active
        or not user.reset_token_expires_at
        or user.reset_token_expires_at.replace(tzinfo=UTC) < now
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.password_hash = hash_password(data.new_password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    user.updated_at = now
    session.add(user)
    await session.commit()
    return {"message": "Password has been reset. You can now log in."}


async def _deactivate_owned_resources(session: AsyncSession, user: User, now: datetime) -> None:
    """Soft-deactivate everything a user owns — shared by the self-service
    DELETE /me and the admin-triggered DELETE /users/{id}."""
    from app.models.collection import Collection
    from app.models.profile import Profile
    from app.models.token import ApiToken

    result = await session.execute(
        select(Collection).where(Collection.owner_id == user.id, Collection.is_active == True)
    )
    for collection in result.scalars().all():
        collection.is_active = False
        session.add(collection)

    result = await session.execute(
        select(Profile).where(Profile.owner_id == user.id, Profile.deleted_at == None)
    )
    for profile in result.scalars().all():
        profile.deleted_at = now
        session.add(profile)

    result = await session.execute(
        select(ApiToken).where(ApiToken.user_id == user.id, ApiToken.is_active == True)
    )
    for token in result.scalars().all():
        token.is_active = False
        session.add(token)


@router.delete("/me")
async def delete_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Soft-delete the current user's account and all owned resources."""
    now = datetime.now(UTC)

    current_user.is_active = False
    current_user.deleted_at = now
    session.add(current_user)

    await _deactivate_owned_resources(session, current_user, now)
    await session.commit()

    # Clear session
    request.session.clear()
    return {"message": "Account deleted"}


@router.get("/users")
async def list_users(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """List all registered users. Admin only."""
    result = await session.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "display_name": u.display_name,
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "role": u.role,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.patch("/users/{user_id}")
async def set_user_active(
    user_id: uuid.UUID,
    is_active: bool,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Enable or disable another user's account. Admin only.

    Acting on your own account is rejected — use the self-service Settings
    page (DELETE /me) for that. That restriction is also what makes this
    endpoint safe from an accidental admin lockout: the caller is always a
    distinct, active admin (enforced by `require_admin` +
    `get_current_user`'s active-only filter), so at least one admin always
    remains regardless of what happens to the target account.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400, detail="Use your own account settings to change your own status"
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = is_active
    user.updated_at = datetime.now(UTC)
    session.add(user)
    await session.commit()
    return {"id": str(user.id), "is_active": user.is_active}


@router.patch("/users/{user_id}/role")
async def set_user_role(
    user_id: uuid.UUID,
    body: UserRoleUpdate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Change another user's role (user/moderator/admin). Admin only.

    Acting on your own account is rejected for the same admin-lockout
    reason documented on set_user_active() above. `is_admin` is kept in
    sync one-directionally from `role` in this same transaction — `role`
    is the only field `require_moderator_or_admin` reads, but `is_admin`
    must keep gating every existing `require_admin`/`authorize_access`
    bypass unchanged.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400, detail="Use your own account settings to change your own role"
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = body.role
    user.is_admin = body.role == "admin"
    user.updated_at = datetime.now(UTC)
    session.add(user)
    await session.commit()
    return {"id": str(user.id), "role": user.role, "is_admin": user.is_admin}


@router.delete("/users/{user_id}")
async def remove_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Soft-delete another user's account and all owned resources. Admin only.

    Mirrors DELETE /me's cascade exactly (minus the session-clear, which
    only applies to the caller's own session). Acting on your own account
    is rejected — use DELETE /me for that; see set_user_active() above for
    why that alone is sufficient to prevent an admin lockout.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400, detail="Use your own account settings to delete your own account"
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(UTC)
    user.is_active = False
    user.deleted_at = now
    session.add(user)

    await _deactivate_owned_resources(session, user, now)
    await session.commit()
    return {"message": "User removed"}


async def _is_provider_enabled(provider: str, session: AsyncSession) -> bool:
    """Check if an auth provider is enabled in system settings."""
    result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
    settings = result.scalar_one_or_none()
    if not settings:
        return True  # Default: enabled if no settings row yet
    field_map = {
        "oidc": settings.oidc_enabled,
        "github": settings.github_enabled,
        "google": settings.google_enabled,
    }
    return field_map.get(provider, True)


async def _fetch_github_primary_email(client: StarletteOAuth2App, token: dict) -> str:
    """GitHub's /user endpoint returns a null `email` unless the user made
    one public, even with the user:email scope granted — the actual address
    (and whether it's verified) lives at /user/emails instead."""
    resp = await client.get("https://api.github.com/user/emails", token=token)
    resp.raise_for_status()
    emails = resp.json()
    primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
    if primary:
        return str(primary["email"])
    verified = next((e for e in emails if e.get("verified")), None)
    return str(verified["email"]) if verified else ""


@router.get("/providers")
async def get_providers(
    session: AsyncSession = Depends(get_session),
):
    """Report which SSO providers are configured and enabled."""
    result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
    settings = result.scalar_one_or_none()

    configured = {}
    for provider in ("oidc", "github", "google"):
        config = await get_effective_oauth_config(provider, session)
        configured[provider] = get_oauth_client(provider, config) is not None

    if settings:
        return {
            "oidc": configured["oidc"] and settings.oidc_enabled,
            "github": configured["github"] and settings.github_enabled,
            "google": configured["google"] and settings.google_enabled,
        }
    return configured


# ─── OIDC Login ───────────────────────────────────────────────

@router.get("/login/{provider}")
async def login(
    provider: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Initiate OIDC/OAuth2 login with the specified provider."""
    if provider not in ("oidc", "github", "google"):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    if not await _is_provider_enabled(provider, session):
        raise HTTPException(status_code=403, detail=f"Provider is disabled: {provider}")

    config = await get_effective_oauth_config(provider, session)
    client = get_oauth_client(provider, config)
    if not client:
        raise HTTPException(status_code=400, detail=f"Provider not configured: {provider}")

    redirect_uri = request.url_for("auth_callback", provider=provider)
    state = generate_oidc_state()

    # PKCE: generate code_verifier and code_challenge (S256) to prevent
    # authorization code interception attacks.
    code_verifier = secrets.token_urlsafe(64)
    code_challenge_digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge_digest).rstrip(b"=").decode("ascii")
    request.session["code_verifier"] = code_verifier

    return await client.authorize_redirect(
        request, redirect_uri, state=state, code_challenge=code_challenge,
        code_challenge_method="S256",
    )


@router.get("/callback/{provider}")
async def auth_callback(
    provider: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """OIDC/OAuth2 callback — create or authenticate user, establish a session."""
    if provider not in ("oidc", "github", "google"):
        # Same guard as login(): without it an unknown provider falls through
        # to get_effective_oauth_config()'s ValueError and 500s.
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    if not await _is_provider_enabled(provider, session):
        raise HTTPException(status_code=403, detail=f"Provider is disabled: {provider}")

    config = await get_effective_oauth_config(provider, session)
    client = get_oauth_client(provider, config)
    if not client:
        raise HTTPException(status_code=400, detail=f"Provider not configured: {provider}")

    # PKCE: authlib only auto-manages code_verifier when code_challenge_method
    # is set on the client at registration time — since login() passes it
    # per-request instead (get_oauth_client() builds clients generically for
    # all three providers), authlib's own session-backed state_data never
    # contains it. Retrieve the one login() stored ourselves and forward it
    # explicitly, or the token exchange 500s with the provider's PKCE error
    # ("A code_verifier was not included, but the authorization request
    # included a code_challenge").
    code_verifier = request.session.pop("code_verifier", None)
    token = await client.authorize_access_token(request, code_verifier=code_verifier)
    user_info = token.get("userinfo") or await client.userinfo(token=token)

    if provider == "github":
        # GitHub is plain OAuth2, not OIDC — its /user response has no `sub`/
        # `preferred_username`/`picture` claims, and `email` is null unless
        # the user made one public, even with the user:email scope granted.
        oidc_sub = str(user_info["id"])
        # Both sources are verified-only: the public profile email must be
        # verified to be shown, and _fetch_github_primary_email filters on
        # `verified`.
        email_verified = True
        email = user_info.get("email") or await _fetch_github_primary_email(client, token)
        display_name = user_info.get("name") or user_info.get("login") or email.split("@")[0]
        avatar_url = user_info.get("avatar_url")
    else:
        oidc_sub = user_info.get("sub")
        # OIDC `email_verified` — some IdPs send the string "true".
        email_verified = user_info.get("email_verified") in (True, "true")
        email = user_info.get("email", "")
        display_name = (
            user_info.get("name") or user_info.get("preferred_username") or email.split("@")[0]
        )
        avatar_url = user_info.get("picture")

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Your GitHub account has no verified email address. Add and "
            "verify an email on GitHub, then try signing in again.",
        )

    # Find or create user
    result = await session.execute(
        select(User).where(User.oidc_sub == oidc_sub, User.oidc_provider == provider)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Check if user exists by email
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            # Linking an SSO identity to an existing account by email is only
            # safe if the provider vouches for that email: registration here
            # is unverified, so without this an attacker could pre-register a
            # victim's address, then have it linked to their own SSO login
            # (or the reverse) and keep a working password on the account.
            if not email_verified:
                raise HTTPException(
                    status_code=403,
                    detail="Your sign-in provider has not verified this email address, so it "
                    "can't be linked to the existing account. Verify it with your provider, "
                    "or sign in with your password.",
                )
            # Never silently re-point an account at a different identity.
            if user.oidc_sub and (user.oidc_sub != oidc_sub or user.oidc_provider != provider):
                raise HTTPException(
                    status_code=403,
                    detail="This account is already linked to a different sign-in identity.",
                )
            user.oidc_sub = oidc_sub
            user.oidc_provider = provider
        else:
            if not await _registration_allowed(session):
                raise HTTPException(status_code=403, detail="Registration is disabled")
            is_admin = await _is_bootstrap_admin(session, email)
            user = User(
                email=email,
                display_name=display_name,
                oidc_sub=oidc_sub,
                oidc_provider=provider,
                avatar_url=avatar_url,
                is_admin=is_admin,
                role="admin" if is_admin else "user",
            )
            session.add(user)

        await session.commit()
        await session.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Same `mfa_forced` gate as password login. A user who already has MFA
    # enabled is *not* challenged here: the SSO flow has no second-factor step
    # (a pre-existing gap, out of scope for this change) — but they must at
    # least have enrolled, which is what `mfa_forced` is about.
    if not user.mfa_enabled and await _mfa_forced(session):
        request.session[_MFA_ENROLL_SESSION_KEY] = str(user.id)
        return RedirectResponse(url="/login?enroll=1", status_code=status.HTTP_302_FOUND)

    request.session["user_id"] = str(user.id)
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


# ─── API Token Management ─────────────────────────────────────

@router.post("/tokens", response_model=ApiTokenCreateResponse)
async def create_token(
    token_data: ApiTokenCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a new API token for CLI authentication."""
    api_key = generate_api_key()
    token_prefix = api_key[:8]

    db_token = ApiToken(
        user_id=current_user.id,
        name=token_data.name,
        token_prefix=token_prefix,
        token_hash=hash_api_key(api_key),
        expires_at=token_data.expires_at or default_token_expiry(),
    )
    session.add(db_token)
    await session.commit()
    await session.refresh(db_token)

    return {
        **db_token.model_dump(),
        "token": api_key,  # Return full key only on creation
    }


@router.get("/tokens", response_model=list[ApiTokenRead])
async def list_tokens(
    user_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List active tokens — your own, or (admin only) another user's."""
    target_id = current_user.id
    if user_id is not None and user_id != current_user.id:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        target_id = user_id

    result = await session.execute(
        select(ApiToken).where(
            ApiToken.user_id == target_id,
            ApiToken.is_active == True,
        )
    )
    return result.scalars().all()


@router.delete("/tokens/{token_id}")
async def revoke_token(
    token_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Revoke an API token (owner or admin)."""
    result = await session.execute(select(ApiToken).where(ApiToken.id == token_id))
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    authorize_access(
        owner_id=token.user_id, current_user=current_user, write=True, resource_name="Token"
    )

    token.is_active = False
    await session.commit()
    return {"message": "Token revoked"}


# ─── MFA / TOTP ───────────────────────────────────────────────

MFA_TOKEN_MAX_AGE = 300  # 5 minutes


def _mfa_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.app_secret_key, salt="mfa-verify")


def _issue_mfa_token(user: User) -> str:
    """Serialize an MFA login token for `user`.

    The payload carries a random nonce so two tokens issued in the same second
    are still distinct: itsdangerous' timestamp only has one-second resolution,
    so without it the single-use check (which compares token hashes) would
    reject a token minted moments after a previous login.
    """
    return _mfa_serializer().dumps({"uid": str(user.id), "nonce": secrets.token_urlsafe(16)})


def _mfa_token_user_id(token: str) -> uuid.UUID | None:
    """Decode an MFA login token, or return None if invalid/expired."""
    try:
        payload = _mfa_serializer().loads(token, max_age=MFA_TOKEN_MAX_AGE)
    except Exception:
        return None
    # Tokens issued before the nonce existed carried the bare user id.
    raw = payload.get("uid") if isinstance(payload, dict) else payload
    if not isinstance(raw, str):
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


def _totp_counter(secret: str, code: str) -> int | None:
    """Return the TOTP time-step `code` matches, or None if it matches none.

    Mirrors pyotp's default `valid_window=0` (only the current step counts)
    while also reporting *which* step matched, so the caller can record it and
    reject a replay of the same code.
    """
    import pyotp

    totp = pyotp.TOTP(secret)
    if not totp.verify(code):
        return None
    return int(totp.timecode(datetime.now(UTC)))


@router.post("/me/mfa/totp/setup")
async def setup_totp(
    current_user: User = Depends(_current_user_or_enrolling),
    session: AsyncSession = Depends(get_session),
):
    """Generate a TOTP secret and return the provisioning URI for QR code setup."""
    import pyotp

    # Check if MFA is enabled in system settings
    result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
    sys_settings = result.scalar_one_or_none()
    if sys_settings and not sys_settings.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled on this server")

    # Re-running setup would silently replace the secret of an account that
    # already requires it, locking the owner out (or, for a hijacked
    # session, swapping in the attacker's authenticator). Disable first.
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=400, detail="MFA is already enabled. Disable it before setting it up again."
        )

    secret = pyotp.random_base32()
    current_user.totp_secret = secret
    session.add(current_user)
    await session.commit()

    provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name=settings.app_name,
    )
    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
    }


@router.post("/me/mfa/totp/verify")
@auth_limiter.limit(_mfa_limit)
async def verify_totp(
    request: Request,
    body: TotpCodeRequest | None = None,
    code: str | None = None,
    current_user: User = Depends(_current_user_or_enrolling),
    session: AsyncSession = Depends(get_session),
):
    """Verify a TOTP code (JSON body `{"code": ...}`) and enable MFA for the user.

    Reachable with a normal session *or* the `mfa_forced` enrolment session —
    in the latter case, completing enrolment also completes the login.
    """
    import pyotp

    code = _body_or_query(body.code if body else None, code, "code")

    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP not set up. Call setup first.")

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(code):
        raise HTTPException(status_code=400, detail="Invalid verification code")

    current_user.mfa_enabled = True
    session.add(current_user)
    await session.commit()

    # Promote a pending enrolment session into a real one (no-op for callers
    # that already had one) so a forced-enrolment login ends authenticated.
    request.session.pop(_MFA_ENROLL_SESSION_KEY, None)
    request.session["user_id"] = str(current_user.id)
    return {"message": "MFA enabled", "mfa_enabled": True}


@router.post("/me/mfa/totp/disable")
@auth_limiter.limit(_mfa_limit)
async def disable_totp(
    request: Request,
    body: TotpCodeRequest | None = None,
    code: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Disable MFA. Requires a valid TOTP code (JSON body `{"code": ...}`)."""
    import pyotp

    if not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled")

    if body is not None:
        code = body.code
    verified = False
    if code and current_user.totp_secret:
        totp = pyotp.TOTP(current_user.totp_secret)
        verified = totp.verify(code)

    if not verified:
        raise HTTPException(status_code=403, detail="Valid TOTP code required to disable MFA")

    current_user.mfa_enabled = False
    current_user.totp_secret = None
    session.add(current_user)
    await session.commit()
    return {"message": "MFA disabled"}


@router.post("/login/mfa")
@auth_limiter.limit(_mfa_limit)
async def login_with_mfa(
    request: Request,
    body: MfaLoginRequest | None = None,
    mfa_token: str | None = None,
    code: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Complete MFA-challenged login by verifying a TOTP code (JSON body
    `{"mfa_token": ..., "code": ...}`)."""
    mfa_token = _body_or_query(body.mfa_token if body else None, mfa_token, "mfa_token")
    code = _body_or_query(body.code if body else None, code, "code")

    # Decode the MFA token
    user_id = _mfa_token_user_id(mfa_token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired MFA token")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    if not user.mfa_enabled or not user.totp_secret:
        raise HTTPException(status_code=400, detail="MFA is not enabled for this user")

    # Single-use token: a captured mfa_token must not be replayable inside its
    # 5-minute window. Checked before the code so a reused token is rejected
    # for that reason, not incidentally.
    token_hash = hashlib.sha256(mfa_token.encode("utf-8")).hexdigest()
    if user.mfa_token_used_hash == token_hash:
        raise HTTPException(status_code=401, detail="Invalid or expired MFA token")

    counter = _totp_counter(user.totp_secret, code)
    if counter is None:
        raise HTTPException(status_code=401, detail="Invalid verification code")
    # A code is valid for its whole 30-second step; reject a replay of a step
    # that has already completed a login.
    if user.last_totp_counter is not None and counter <= user.last_totp_counter:
        raise HTTPException(
            status_code=401, detail="This verification code has already been used"
        )

    user.last_totp_counter = counter
    user.mfa_token_used_hash = token_hash
    session.add(user)
    await session.commit()

    request.session["user_id"] = str(user.id)
    return {"message": "MFA verified", "user_id": str(user.id)}
