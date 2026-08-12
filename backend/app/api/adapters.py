"""Adapter routes — list available adapters and preview translations."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.adapters import get_adapter, list_adapters
from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.system_settings import SystemSettings
from app.models.user import User

router = APIRouter()


async def _disabled_adapter_names(session: AsyncSession) -> set[str]:
    result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
    settings = result.scalar_one_or_none()
    if not settings:
        return set()
    return set(json.loads(settings.disabled_adapters))


@router.get("")
async def list_available_adapters(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all registered target adapters."""
    disabled = await _disabled_adapter_names(session)
    adapters = list_adapters()
    return [
        {
            "name": adapter.adapter_name(),
            "description": adapter.__class__.__doc__,
            "targets": adapter.supported_targets(),
            "enabled": adapter.adapter_name() not in disabled,
        }
        for adapter in adapters
    ]


@router.get("/{adapter_name}")
async def get_adapter_info(
    adapter_name: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get information about a specific adapter."""
    adapter = get_adapter(adapter_name)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Adapter '{adapter_name}' not found")
    disabled = await _disabled_adapter_names(session)
    return {
        "name": adapter.adapter_name(),
        "description": adapter.__class__.__doc__,
        "targets": adapter.supported_targets(),
        "enabled": adapter.adapter_name() not in disabled,
    }
