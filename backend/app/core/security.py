"""OIDC/OAuth2 authentication and API key security."""

import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client.apps import StarletteOAuth2App

from app.core.config import settings
from app.services.effective_settings import OAuthProviderConfig

# ─── OAuth / OIDC ─────────────────────────────────────────────
#
# Each provider's Authlib remote app is built from its *effective* config
# (a DB override in system_settings, merged over the env var default — see
# app/services/effective_settings.py) and cached by a fingerprint of that
# config. A credential saved via System Settings takes effect on the next
# login/callback request, without a restart — see ADR-0006.

_client_cache: dict[str, tuple[str, StarletteOAuth2App]] = {}


def _fingerprint(config: OAuthProviderConfig) -> str:
    return f"{config.client_id}:{config.client_secret}:{config.issuer_url}:{config.scopes}"


def get_oauth_client(provider: str, config: OAuthProviderConfig) -> StarletteOAuth2App | None:
    """Return the Authlib remote app for a provider, rebuilding it if the
    effective config has changed since it was last built. Returns None if
    the provider isn't configured (no client ID), or — for OIDC — has no
    issuer URL to discover metadata from."""
    if not config.client_id:
        return None
    if provider == "oidc" and not config.issuer_url:
        return None

    fingerprint = _fingerprint(config)
    cached = _client_cache.get(provider)
    if cached and cached[0] == fingerprint:
        return cached[1]

    registry = OAuth()
    if provider == "oidc":
        registry.register(
            name="oidc",
            client_id=config.client_id,
            client_secret=config.client_secret,
            server_metadata_url=f"{config.issuer_url}/.well-known/openid-configuration",
            client_kwargs={"scope": config.scopes},
        )
    elif provider == "github":
        registry.register(
            name="github",
            client_id=config.client_id,
            client_secret=config.client_secret,
            access_token_url="https://github.com/login/oauth/access_token",
            authorize_url="https://github.com/login/oauth/authorize",
            # GitHub isn't OIDC — there's no discovery document to supply
            # userinfo_endpoint, so it must be set explicitly or
            # client.userinfo() 500s with KeyError: 'userinfo_endpoint'.
            api_base_url="https://api.github.com/",
            userinfo_endpoint="https://api.github.com/user",
            client_kwargs={"scope": "user:email"},
        )
    elif provider == "google":
        registry.register(
            name="google",
            client_id=config.client_id,
            client_secret=config.client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
    else:
        return None

    client = registry.create_client(provider)
    _client_cache[provider] = (fingerprint, client)
    return client


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
