"""Admin routes — system settings, user management, and other admin-only operations."""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.adapters import get_adapter
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
    if "disabled_adapters" in update_data:
        update_data["disabled_adapters"] = json.dumps(update_data["disabled_adapters"])

    for field, value in update_data.items():
        setattr(settings, field, value)

    settings.updated_at = datetime.now(UTC)
    session.add(settings)
    await session.commit()
    await session.refresh(settings)
    return SystemSettingsRead.from_settings(settings)


@router.patch("/adapters/{adapter_name}")
async def toggle_adapter(
    adapter_name: str,
    enabled: bool,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Enable or disable an adapter system-wide. Admin only."""
    if not get_adapter(adapter_name):
        raise HTTPException(status_code=404, detail=f"Adapter '{adapter_name}' not found")

    settings = await _get_or_create_settings(session)
    disabled = set(json.loads(settings.disabled_adapters))
    if enabled:
        disabled.discard(adapter_name)
    else:
        disabled.add(adapter_name)

    settings.disabled_adapters = json.dumps(sorted(disabled))
    settings.updated_at = datetime.now(UTC)
    session.add(settings)
    await session.commit()
    return {"name": adapter_name, "enabled": enabled}
