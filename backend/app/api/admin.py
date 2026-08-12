"""Admin routes — system settings, user management, and other admin-only operations."""

from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.crypto import SettingsEncryptionKeyError, encrypt_secret
from app.core.database import get_session
from app.core.deps import require_admin
from app.models.system_settings import SystemSettings, SystemSettingsRead, SystemSettingsUpdate
from app.models.user import User
from app.services.effective_settings import (
    OAuthOverrides,
    SmtpOverrides,
    get_effective_oauth_config,
    get_effective_smtp_config,
)
from app.services.email import EmailSendError, send_email

router = APIRouter()

OAUTH_PROVIDERS = ("oidc", "github", "google")

# Maps a plaintext write-only field on SystemSettingsUpdate to the encrypted
# column it's stored in — see ADR-0006.
_SECRET_FIELD_MAP = {
    "smtp_password": "smtp_password_encrypted",
    "oidc_client_secret": "oidc_client_secret_encrypted",
    "github_client_secret": "github_client_secret_encrypted",
    "google_client_secret": "google_client_secret_encrypted",
}


async def _get_or_create_settings(session: AsyncSession) -> SystemSettings:
    """Get the single system settings row, creating it if it doesn't exist."""
    result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = SystemSettings(id=1)
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
    return settings


@router.get("/settings", response_model=SystemSettingsRead)
async def get_settings(
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get current system settings. Admin only."""
    settings = await _get_or_create_settings(session)
    return SystemSettingsRead.from_settings(settings)


@router.patch("/settings", response_model=SystemSettingsRead)
async def update_settings(
    data: SystemSettingsUpdate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Update system settings. Admin only. Only provided fields are changed."""
    settings = await _get_or_create_settings(session)

    update_data = data.model_dump(exclude_unset=True)

    for plaintext_field, encrypted_field in _SECRET_FIELD_MAP.items():
        if plaintext_field not in update_data:
            continue
        plaintext = update_data.pop(plaintext_field)
        if plaintext:
            try:
                setattr(settings, encrypted_field, encrypt_secret(plaintext))
            except SettingsEncryptionKeyError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        else:
            setattr(settings, encrypted_field, None)

    for field, value in update_data.items():
        setattr(settings, field, value)

    settings.updated_at = datetime.now(UTC)
    session.add(settings)
    await session.commit()
    await session.refresh(settings)
    return SystemSettingsRead.from_settings(settings)


@router.post("/settings/smtp/test")
async def test_smtp(
    overrides: SmtpOverrides | None = None,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Send a real test email to the requesting admin's own address.

    Accepts optional overrides (host/port/username/password/from_email/
    from_name/use_tls) so an admin can validate settings before saving them.
    Unset overrides fall back to the saved/effective config.
    """
    config = await get_effective_smtp_config(session, overrides=overrides or {})
    try:
        await send_email(
            config=config,
            to=current_user.email,
            subject="MyACE SMTP test",
            text_body="This is a test email from your MyACE System Settings page. "
            "If you received this, SMTP is configured correctly.",
        )
    except EmailSendError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": f"Test email sent to {current_user.email}"}


@router.post("/settings/oauth/{provider}/test")
async def test_oauth_provider(
    provider: str,
    overrides: OAuthOverrides | None = None,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Validate an OAuth provider's config (format + reachability).

    This is NOT a full login test — that requires an actual browser
    redirect through the provider. It checks that the client ID/secret are
    present and that the provider's discovery/authorize endpoint is
    reachable, using request overrides or the saved/effective config.
    """
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    config = await get_effective_oauth_config(provider, session, overrides=overrides or {})
    if not config.client_id or not config.client_secret:
        raise HTTPException(status_code=400, detail="Client ID and secret are both required")

    # follow_redirects=True: GitHub's authorize endpoint always redirects an
    # unauthenticated server-to-server request to its login page (302) —
    # that's a normal, reachable response, not a failure. Reachability is
    # judged on the final status code after following redirects, not on
    # whether a redirect happened at all.
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            if provider == "oidc":
                if not config.issuer_url:
                    raise HTTPException(
                        status_code=400, detail="Issuer URL is required for OIDC"
                    )
                resp = await client.get(
                    f"{config.issuer_url.rstrip('/')}/.well-known/openid-configuration"
                )
                if resp.status_code >= 400:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Discovery endpoint returned HTTP {resp.status_code}",
                    )
                metadata = resp.json()
                if "authorization_endpoint" not in metadata or "token_endpoint" not in metadata:
                    raise HTTPException(
                        status_code=400,
                        detail="Discovery document is missing required OIDC endpoints",
                    )
                summary = "OIDC discovery document is reachable and valid"
            elif provider == "github":
                resp = await client.get(
                    "https://github.com/login/oauth/authorize",
                    params={"client_id": config.client_id},
                )
                if resp.status_code >= 400:
                    raise HTTPException(
                        status_code=400,
                        detail=f"GitHub's OAuth endpoint returned HTTP {resp.status_code}",
                    )
                summary = "GitHub's OAuth authorize endpoint is reachable"
            else:  # google
                resp = await client.get(
                    "https://accounts.google.com/.well-known/openid-configuration"
                )
                if resp.status_code >= 400:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Google's discovery endpoint returned HTTP {resp.status_code}",
                    )
                summary = "Google's OAuth discovery endpoint is reachable"
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=400, detail=f"Connectivity check failed: {exc}"
            ) from exc

    return {
        "message": f"{summary}. This checks reachability and format only — save your changes "
        f"and use 'Sign in with {provider}' to fully verify sign-in works.",
    }
