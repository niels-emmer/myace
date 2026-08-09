"""Adapter routes — list available adapters and preview translations."""

from fastapi import APIRouter, Depends, HTTPException

from app.adapters import get_adapter, list_adapters
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("")
async def list_available_adapters(
    current_user: User = Depends(get_current_user),
):
    """List all registered target adapters."""
    adapters = list_adapters()
    return [
        {
            "name": adapter.adapter_name(),
            "description": adapter.__class__.__doc__,
            "targets": adapter.supported_targets(),
        }
        for adapter in adapters
    ]


@router.get("/{adapter_name}")
async def get_adapter_info(
    adapter_name: str,
    current_user: User = Depends(get_current_user),
):
    """Get information about a specific adapter."""
    adapter = get_adapter(adapter_name)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Adapter '{adapter_name}' not found")
    return {
        "name": adapter.adapter_name(),
        "description": adapter.__class__.__doc__,
        "targets": adapter.supported_targets(),
    }
