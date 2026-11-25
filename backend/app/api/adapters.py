"""Adapter routes — list available adapters and preview translations."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import get_adapter, list_adapters
from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.services.effective_settings import get_disabled_adapter_names

router = APIRouter()


@router.get("")
async def list_available_adapters(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all registered target adapters."""
    disabled = await get_disabled_adapter_names(session)
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
    disabled = await get_disabled_adapter_names(session)
    return {
        "name": adapter.adapter_name(),
        "description": adapter.__class__.__doc__,
        "targets": adapter.supported_targets(),
        "enabled": adapter.adapter_name() not in disabled,
    }
