"""Authentication routes — email/password, OIDC login, callback, token management."""

import base64
import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.core.authz import authorize_access
from app.core.config import settings
from app.core.database import get_session
from app.core.deps import get_current_user, require_admin
from app.core.security import (
    default_token_expiry,
    generate_api_key,
    generate_oidc_state,
    hash_api_key,
    hash_password,
    oauth,
    verify_password,
)
from app.models.system_settings import SystemSettings
from app.models.token import ApiToken, ApiTokenCreate, ApiTokenCreateResponse, ApiTokenRead
from app.models.user import (
    PasswordChange,
    User,
    UserLogin,
    UserRead,
    UserRegister,
    UserUpdate,
)

router = APIRouter()


async def _is_bootstrap_admin(session: AsyncSession, email: str) -> bool:
    """First-ever user becomes admin (while ADMIN_BOOTSTRAP_ENABLED); emails in
    ADMIN_EMAILS are always promoted regardless."""
    if email.lower() in settings.admin_email_list:
        return True
    if not settings.admin_bootstrap_enabled:
        return False
    count = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    return count == 0


# ─── Email + Password Auth ─────────────────────────────────────

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    data: UserRegister,
    session: AsyncSession = Depends(get_session),
):
    """Register a new account with email + password."""
    if len(data.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    # Check if registration is allowed
    result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
    sys_settings = result.scalar_one_or_none()
    if sys_settings and not sys_settings.allow_registration:
        raise HTTPException(status_code=403, detail="Registration is disabled")

    result = await session.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        # Return a generic success response to prevent user enumeration.
        # Do NOT set the session or return the real user — the caller should
        # proceed to login with their password. Returning a fake UserRead
        # avoids leaking whether the email exists while keeping the same
        # response shape.
        return UserRead(
            id=uuid.uuid4(), email=data.email, display_name="",
            is_active=True, is_admin=False,
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )

    is_admin = await _is_bootstrap_admin(session, data.email)
    user = User(
        email=data.email,
        display_name=data.display_name,
        password_hash=hash_password(data.password),
        is_admin=is_admin,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    request.session["user_id"] = str(user.id)
    return user


@router.post("/login")
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

    # Check if MFA is required
    if user.mfa_enabled:
        s = _mfa_serializer()
        mfa_token = s.dumps(str(user.id))
        return {
            "mfa_required": True,
            "mfa_token": mfa_token,
            "message": "MFA code required",
        }

    request.session["user_id"] = str(user.id)
    return UserRead(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
    )


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
async def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Change the current user's password."""
    if not current_user.password_hash:
        raise HTTPException(status_code=400, detail="Cannot change password for OIDC-only accounts")

    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=403, detail="Current password is incorrect")

    if len(data.new_password) < 8:
        raise HTTPException(status_code=422, detail="New password must be at least 8 characters")

    current_user.password_hash = hash_password(data.new_password)
    current_user.updated_at = datetime.now(UTC)
    session.add(current_user)
    await session.commit()
    return {"message": "Password updated"}


@router.delete("/me")
async def delete_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Soft-delete the current user's account and all owned resources."""
    from app.models.collection import Collection
    from app.models.profile import Profile
    from app.models.token import ApiToken

    now = datetime.now(UTC)

    # Soft-delete user
    current_user.is_active = False
    current_user.deleted_at = now
    session.add(current_user)

    # Soft-deactivate all owned collections
    result = await session.execute(
        select(Collection).where(
            Collection.owner_id == current_user.id, Collection.is_active == True
        )
    )
    for collection in result.scalars().all():
        collection.is_active = False
        session.add(collection)

    # Soft-delete all owned profiles
    result = await session.execute(
        select(Profile).where(Profile.owner_id == current_user.id, Profile.deleted_at == None)
    )
    for profile in result.scalars().all():
        profile.deleted_at = now
        session.add(profile)

    # Deactivate all API tokens
    result = await session.execute(
        select(ApiToken).where(ApiToken.user_id == current_user.id, ApiToken.is_active == True)
    )
    for token in result.scalars().all():
        token.is_active = False
        session.add(token)

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
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


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


@router.get("/providers")
async def get_providers(
    session: AsyncSession = Depends(get_session),
):
    """Report which SSO providers are configured and enabled."""
    result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
    settings = result.scalar_one_or_none()

    configured = {
        "oidc": oauth.create_client("oidc") is not None,
        "github": oauth.create_client("github") is not None,
        "google": oauth.create_client("google") is not None,
    }

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

    client = oauth.create_client(provider)
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
    if not await _is_provider_enabled(provider, session):
        raise HTTPException(status_code=403, detail=f"Provider is disabled: {provider}")

    client = oauth.create_client(provider)
    if not client:
        raise HTTPException(status_code=400, detail=f"Provider not configured: {provider}")

    token = await client.authorize_access_token(request)
    user_info = token.get("userinfo") or await client.userinfo(token=token)

    oidc_sub = user_info.get("sub")
    email = user_info.get("email", "")
    display_name = user_info.get("name", user_info.get("preferred_username", email.split("@")[0]))
    avatar_url = user_info.get("picture")

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
            # Link OIDC identity
            user.oidc_sub = oidc_sub
            user.oidc_provider = provider
        else:
            # Create new user
            user = User(
                email=email,
                display_name=display_name,
                oidc_sub=oidc_sub,
                oidc_provider=provider,
                avatar_url=avatar_url,
                is_admin=await _is_bootstrap_admin(session, email),
            )
            session.add(user)

        await session.commit()
        await session.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

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


@router.post("/me/mfa/totp/setup")
async def setup_totp(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Generate a TOTP secret and return the provisioning URI for QR code setup."""
    import pyotp

    # Check if MFA is enabled in system settings
    result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
    sys_settings = result.scalar_one_or_none()
    if sys_settings and not sys_settings.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled on this server")

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
async def verify_totp(
    code: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Verify a TOTP code and enable MFA for the user."""
    import pyotp

    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP not set up. Call setup first.")

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(code):
        raise HTTPException(status_code=400, detail="Invalid verification code")

    current_user.mfa_enabled = True
    session.add(current_user)
    await session.commit()
    return {"message": "MFA enabled", "mfa_enabled": True}


@router.post("/me/mfa/totp/disable")
async def disable_totp(
    code: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Disable MFA. Requires a valid TOTP code or current password."""
    import pyotp

    if not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled")

    # Verify with TOTP code or password
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
async def login_with_mfa(
    request: Request,
    mfa_token: str,
    code: str,
    session: AsyncSession = Depends(get_session),
):
    """Complete MFA-challenged login by verifying a TOTP code."""
    import pyotp

    # Decode the MFA token
    s = _mfa_serializer()
    try:
        user_id_str = s.loads(mfa_token, max_age=MFA_TOKEN_MAX_AGE)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired MFA token")

    user_id = uuid.UUID(user_id_str)
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    if not user.mfa_enabled or not user.totp_secret:
        raise HTTPException(status_code=400, detail="MFA is not enabled for this user")

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(code):
        raise HTTPException(status_code=401, detail="Invalid verification code")

    request.session["user_id"] = str(user.id)
    return {"message": "MFA verified", "user_id": str(user.id)}
