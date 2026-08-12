"""Resolve "effective" runtime config by layering DB overrides over env vars.

For any setting an admin can also edit via the System Settings UI (SMTP,
OAuth provider credentials), a non-empty value saved in `system_settings`
wins; otherwise the env var (`Settings`) default applies. This mirrors the
existing enabled/disabled toggle precedence, extended to secrets.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings as env_settings
from app.core.crypto import decrypt_secret
from app.models.system_settings import SystemSettings

Overrides = dict[str, str | int | bool | None]
SmtpOverrides = Overrides
OAuthOverrides = Overrides


@dataclass
class SmtpConfig:
    enabled: bool
    host: str
    port: int
    username: str
    password: str
    from_email: str
    from_name: str
    use_tls: bool


async def _get_settings_row(session: AsyncSession) -> SystemSettings | None:
    result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
    return result.scalar_one_or_none()


def _str_override(overrides: Overrides, key: str, db_value: str | None, env_value: str) -> str:
    override = overrides.get(key)
    if override not in (None, ""):
        return str(override)
    if db_value:
        return db_value
    return env_value


def _int_override(overrides: Overrides, key: str, db_value: int | None, env_value: int) -> int:
    override = overrides.get(key)
    if override not in (None, ""):
        return int(override)
    if db_value is not None:
        return db_value
    return env_value


def _bool_override(
    overrides: Overrides, key: str, db_value: bool | None, env_value: bool
) -> bool:
    override = overrides.get(key)
    if override is not None:
        return bool(override)
    if db_value is not None:
        return db_value
    return env_value


async def get_effective_smtp_config(
    session: AsyncSession, overrides: SmtpOverrides | None = None
) -> SmtpConfig:
    """Merge overrides > DB (system_settings) > env, for SMTP config."""
    overrides = overrides or {}
    row = await _get_settings_row(session)

    password_override = overrides.get("password")
    if password_override:
        password = str(password_override)
    elif row and row.smtp_password_encrypted:
        password = decrypt_secret(row.smtp_password_encrypted)
    else:
        password = env_settings.smtp_password

    return SmtpConfig(
        enabled=_bool_override(overrides, "enabled", row.smtp_enabled if row else None, True),
        host=_str_override(
            overrides, "host", row.smtp_host if row else None, env_settings.smtp_host
        ),
        port=_int_override(
            overrides, "port", row.smtp_port if row else None, env_settings.smtp_port
        ),
        username=_str_override(
            overrides, "username", row.smtp_username if row else None, env_settings.smtp_username
        ),
        password=password,
        from_email=_str_override(
            overrides, "from_email", row.smtp_from_email if row else None,
            env_settings.smtp_from_email,
        ),
        from_name=_str_override(
            overrides, "from_name", row.smtp_from_name if row else None,
            env_settings.smtp_from_name,
        ),
        use_tls=_bool_override(
            overrides, "use_tls", row.smtp_use_tls if row else None, env_settings.smtp_use_tls
        ),
    )


@dataclass
class OAuthProviderConfig:
    client_id: str
    client_secret: str
    issuer_url: str  # OIDC only — empty for github/google
    scopes: str  # OIDC only — empty for github/google


async def get_effective_oauth_config(
    provider: str, session: AsyncSession, overrides: OAuthOverrides | None = None
) -> OAuthProviderConfig:
    """Merge overrides > DB (system_settings) > env, for one OAuth provider."""
    overrides = overrides or {}
    row = await _get_settings_row(session)

    if provider == "oidc":
        db_client_id = row.oidc_client_id if row else None
        db_secret_encrypted = row.oidc_client_secret_encrypted if row else None
        env_client_id, env_secret = env_settings.oidc_client_id, env_settings.oidc_client_secret
        issuer_url = _str_override(
            overrides, "issuer_url", row.oidc_issuer_url if row else None,
            env_settings.oidc_issuer_url,
        )
        scopes = _str_override(
            overrides, "scopes", row.oidc_scopes if row else None, env_settings.oidc_scopes
        )
    elif provider == "github":
        db_client_id = row.github_client_id if row else None
        db_secret_encrypted = row.github_client_secret_encrypted if row else None
        env_client_id = env_settings.github_client_id
        env_secret = env_settings.github_client_secret
        issuer_url, scopes = "", ""
    elif provider == "google":
        db_client_id = row.google_client_id if row else None
        db_secret_encrypted = row.google_client_secret_encrypted if row else None
        env_client_id = env_settings.google_client_id
        env_secret = env_settings.google_client_secret
        issuer_url, scopes = "", ""
    else:
        raise ValueError(f"Unknown OAuth provider: {provider}")

    client_id = _str_override(overrides, "client_id", db_client_id, env_client_id)

    secret_override = overrides.get("client_secret")
    if secret_override:
        client_secret = str(secret_override)
    elif db_secret_encrypted:
        client_secret = decrypt_secret(db_secret_encrypted)
    else:
        client_secret = env_secret

    return OAuthProviderConfig(
        client_id=client_id, client_secret=client_secret, issuer_url=issuer_url, scopes=scopes
    )
