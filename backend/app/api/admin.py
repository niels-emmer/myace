"""Admin routes — system settings, user management, and other admin-only operations."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.core.deps import require_admin
from app.models.system_settings import SystemSettings, SystemSettingsRead, SystemSettingsUpdate
from app.models.user import User

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
    return settings


@router.patch("/settings", response_model=SystemSettingsRead)
async def update_settings(
    data: SystemSettingsUpdate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Update system settings. Admin only. Only provided fields are changed."""
    settings = await _get_or_create_settings(session)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    settings.updated_at = datetime.now(UTC)
    session.add(settings)
    await session.commit()
    await session.refresh(settings)
    return settings
