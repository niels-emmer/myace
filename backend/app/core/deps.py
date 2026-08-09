"""Auth dependencies — resolve the authenticated user from a session cookie or API token."""

import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.core.security import verify_api_key
from app.models.token import ApiToken
from app.models.user import User

UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def _user_from_session(request: Request, session: AsyncSession) -> User | None:
    raw_user_id = request.session.get("user_id")
    if not raw_user_id:
        return None
    try:
        user_id = uuid.UUID(raw_user_id)
    except ValueError:
        return None
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user if user and user.is_active else None


async def _user_from_bearer_token(request: Request, session: AsyncSession) -> User | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    raw_key = auth_header[7:].strip()
    if not raw_key:
        return None

    token_prefix = raw_key[:8]
    result = await session.execute(
        select(ApiToken).where(
            ApiToken.token_prefix == token_prefix,
            ApiToken.is_active == True,
        )
    )
    candidates = result.scalars().all()

    for token in candidates:
        if token.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            continue
        if not verify_api_key(raw_key, token.token_hash):
            continue

        token.last_used_at = datetime.now(UTC)
        await session.commit()

        user_result = await session.execute(select(User).where(User.id == token.user_id))
        user = user_result.scalar_one_or_none()
        return user if user and user.is_active else None

    return None


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Resolve the authenticated user from a session cookie (web UI) or a
    Bearer API token (CLI). Raises 401 if neither yields an active user."""
    user = await _user_from_session(request, session)
    if user:
        return user

    user = await _user_from_bearer_token(request, session)
    if user:
        return user

    raise UNAUTHORIZED


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency variant that additionally requires admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user
