"""Authentication routes — email/password, OIDC login, callback, token management."""

import base64
import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
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
from app.models.token import ApiToken, ApiTokenCreate, ApiTokenCreateResponse, ApiTokenRead
from app.models.user import User, UserLogin, UserRead, UserRegister

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


@router.post("/login", response_model=UserRead)
async def login_with_password(
    request: Request,
    data: UserLogin,
    session: AsyncSession = Depends(get_session),
):
    """Log in with email + password."""
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

    request.session["user_id"] = str(user.id)
    return user


@router.post("/logout")
async def logout(request: Request):
    """Clear the current session."""
    request.session.clear()
    return {"message": "Logged out"}


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return current_user


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


@router.get("/providers")
async def get_providers():
    """Report which SSO providers are actually configured server-side."""
    return {
        "oidc": oauth.create_client("oidc") is not None,
        "github": oauth.create_client("github") is not None,
        "google": oauth.create_client("google") is not None,
    }


# ─── OIDC Login ───────────────────────────────────────────────

@router.get("/login/{provider}")
async def login(provider: str, request: Request):
    """Initiate OIDC/OAuth2 login with the specified provider."""
    if provider not in ("oidc", "github", "google"):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

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
