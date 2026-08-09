"""Adapter routes — list available adapters and preview translations."""

from fastapi import APIRouter, HTTPException

from app.adapters import get_adapter, list_adapters

router = APIRouter()


@router.get("")
async def list_available_adapters():
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
async def get_adapter_info(adapter_name: str):
    """Get information about a specific adapter."""
    adapter = get_adapter(adapter_name)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Adapter '{adapter_name}' not found")
    return {
        "name": adapter.adapter_name(),
        "description": adapter.__class__.__doc__,
        "targets": adapter.supported_targets(),
    }
