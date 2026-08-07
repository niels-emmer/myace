"""Target adapters — translate Canonical IR into framework-specific formats."""

from typing import Optional
from app.adapters.base import BaseAdapter
from app.adapters.claude_code import ClaudeCodeAdapter
from app.adapters.opencode import OpenCodeAdapter
from app.adapters.cursor import CursorAdapter

_registry: dict[str, BaseAdapter] = {}


def register_adapter(adapter: BaseAdapter) -> None:
    """Register an adapter in the global registry."""
    _registry[adapter.adapter_name()] = adapter


def get_adapter(name: str) -> Optional[BaseAdapter]:
    """Get an adapter by name."""
    return _registry.get(name)


def list_adapters() -> list[BaseAdapter]:
    """List all registered adapters."""
    return list(_registry.values())


# Register built-in adapters
register_adapter(ClaudeCodeAdapter())
register_adapter(OpenCodeAdapter())
register_adapter(CursorAdapter())
