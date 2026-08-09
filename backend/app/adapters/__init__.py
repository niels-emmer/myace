"""Target adapters — translate Canonical IR into framework-specific formats.

Adapters are static Python classes registered at import time. Adding or
updating an adapter requires a code change and deployment — there is no
runtime plugin mechanism.

KNOWN GAP: The doc_verifier service periodically fetches framework
documentation from URLs (Claude Code docs, OpenCode GitHub, Cursor docs)
and caches it in DocCacheEntry. This cached data is NOT currently consumed
by the adapters themselves — the adapters' translation logic is hardcoded.
A future enhancement could make adapters read from the doc cache to
dynamically adjust their output based on the latest framework docs.

The doc cache can be refreshed by admins via POST /api/v1/doc-cache/refresh.
"""

from app.adapters.base import BaseAdapter
from app.adapters.claude_code import ClaudeCodeAdapter
from app.adapters.cline import ClineAdapter
from app.adapters.codex_cli import CodexCliAdapter
from app.adapters.copilot_cli import CopilotCliAdapter
from app.adapters.cursor import CursorAdapter
from app.adapters.opencode import OpenCodeAdapter
from app.adapters.windsurf import WindsurfAdapter

_registry: dict[str, BaseAdapter] = {}


def register_adapter(adapter: BaseAdapter) -> None:
    """Register an adapter in the global registry."""
    _registry[adapter.adapter_name()] = adapter


def get_adapter(name: str) -> BaseAdapter | None:
    """Get an adapter by name."""
    return _registry.get(name)


def list_adapters() -> list[BaseAdapter]:
    """List all registered adapters."""
    return list(_registry.values())


# Register built-in adapters
register_adapter(ClaudeCodeAdapter())
register_adapter(OpenCodeAdapter())
register_adapter(CursorAdapter())
register_adapter(CodexCliAdapter())
register_adapter(CopilotCliAdapter())
register_adapter(ClineAdapter())
register_adapter(WindsurfAdapter())
