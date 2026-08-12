"""Admin routes — system settings, user management, and other admin-only operations."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.crypto import SettingsEncryptionKeyError, encrypt_secret
from app.core.database import get_session
from app.core.deps import require_admin
from app.models.system_settings import SystemSettings, SystemSettingsRead, SystemSettingsUpdate
from app.models.user import User
from app.services.effective_settings import SmtpOverrides, get_effective_smtp_config
from app.services.email import EmailSendError, send_email

router = APIRouter()


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

    if "smtp_password" in update_data:
        plaintext = update_data.pop("smtp_password")
        if plaintext:
            try:
                settings.smtp_password_encrypted = encrypt_secret(plaintext)
            except SettingsEncryptionKeyError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        else:
            settings.smtp_password_encrypted = None

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
