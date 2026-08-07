"""CLI-side target adapters — local fallback rendering when server is unavailable."""

from typing import Optional
from myace_cli.adapters.base import BaseAdapter
from myace_cli.adapters.claude_code import ClaudeCodeAdapter
from myace_cli.adapters.opencode import OpenCodeAdapter
from myace_cli.adapters.cursor import CursorAdapter

_registry: dict[str, BaseAdapter] = {}


def register_adapter(adapter: BaseAdapter) -> None:
    _registry[adapter.adapter_name()] = adapter


def get_adapter(name: str) -> Optional[BaseAdapter]:
    return _registry.get(name)


def list_adapters() -> list[BaseAdapter]:
    return list(_registry.values())


register_adapter(ClaudeCodeAdapter())
register_adapter(OpenCodeAdapter())
register_adapter(CursorAdapter())
