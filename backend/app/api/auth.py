"""Authentication routes — OIDC login, callback, token management."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.core.security import (
    oauth, generate_api_key, hash_api_key, verify_api_key,
    generate_oidc_state, default_token_expiry,
)
from app.models.user import User
from app.models.token import ApiToken, ApiTokenCreate, ApiTokenRead

router = APIRouter()


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
    return await client.authorize_redirect(request, redirect_uri, state=state)


@router.get("/callback/{provider}")
async def auth_callback(
    provider: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """OIDC/OAuth2 callback — create or authenticate user."""
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
            )
            session.add(user)

        await session.commit()
        await session.refresh(user)

    return {
        "user_id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "message": "Authentication successful",
    }


# ─── API Token Management ─────────────────────────────────────

@router.post("/tokens", response_model=ApiTokenRead)
async def create_token(
    token_data: ApiTokenCreate,
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Create a new API token for CLI authentication."""
    api_key = generate_api_key()
    token_prefix = api_key[:8]

    db_token = ApiToken(
        user_id=user_id,
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
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """List all active tokens for a user."""
    result = await session.execute(
        select(ApiToken).where(
            ApiToken.user_id == user_id,
            ApiToken.is_active == True,
        )
    )
    return result.scalars().all()


@router.delete("/tokens/{token_id}")
async def revoke_token(
    token_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Revoke an API token."""
    result = await session.execute(
        select(ApiToken).where(
            ApiToken.id == token_id,
            ApiToken.user_id == user_id,
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    token.is_active = False
    await session.commit()
    return {"message": "Token revoked"}
