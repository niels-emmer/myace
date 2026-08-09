"""OIDC/OAuth2 authentication and API key security."""

import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig

from app.core.config import settings

# ─── OAuth / OIDC ─────────────────────────────────────────────

starlette_config = StarletteConfig(environ={
    "OIDC_CLIENT_ID": settings.oidc_client_id,
    "OIDC_CLIENT_SECRET": settings.oidc_client_secret,
    "GITHUB_CLIENT_ID": settings.github_client_id,
    "GITHUB_CLIENT_SECRET": settings.github_client_secret,
    "GOOGLE_CLIENT_ID": settings.google_client_id,
    "GOOGLE_CLIENT_SECRET": settings.google_client_secret,
})

oauth = OAuth(starlette_config)

# Register OIDC provider
if settings.oidc_issuer_url:
    oauth.register(
        name="oidc",
        server_metadata_url=f"{settings.oidc_issuer_url}/.well-known/openid-configuration",
        client_kwargs={"scope": settings.oidc_scopes},
    )

# Register GitHub
if settings.github_client_id:
    oauth.register(
        name="github",
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        client_kwargs={"scope": "user:email"},
    )

# Register Google
if settings.google_client_id:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


# ─── API Key Management ───────────────────────────────────────

def generate_api_key() -> str:
    """Generate a cryptographically random API key."""
    return secrets.token_urlsafe(settings.api_key_length)


def hash_api_key(api_key: str) -> str:
    """Hash an API key using bcrypt for storage."""
    return bcrypt.hashpw(
        api_key.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_api_key(api_key: str, hashed: str) -> bool:
    """Verify an API key against its stored hash."""
    return bcrypt.checkpw(
        api_key.encode("utf-8"),
        hashed.encode("utf-8"),
    )


def hash_password(password: str) -> str:
    """Hash a user password using bcrypt for storage."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a user password against its stored hash."""
    return bcrypt.checkpw(
        password.encode("utf-8"),
        hashed.encode("utf-8"),
    )


def generate_oidc_state() -> str:
    """Generate a cryptographically random state parameter for OIDC."""
    return secrets.token_urlsafe(32)


# ─── Token Expiry ─────────────────────────────────────────────

def default_token_expiry() -> datetime:
    """Default API key expiry: 365 days from now."""
    return datetime.now(UTC) + timedelta(days=365)
