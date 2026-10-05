"""Tests for CLI sync module."""

from pathlib import Path

import pytest

from myace_cli.sync import SyncEngine


def test_resolve_profile_id_by_uuid():
    """Test that UUID strings are returned directly."""
    sync = SyncEngine()
    uuid_str = "12345678-1234-5678-1234-567812345678"
    # This won't actually call the server since it's a valid UUID
    result = sync._resolve_profile_id("http://localhost", "token", uuid_str)
    assert result == uuid_str


def test_resolve_profile_id_invalid():
    """Test that non-UUID strings trigger a server lookup attempt."""
    sync = SyncEngine()
    # This will fail to connect, returning None
    result = sync._resolve_profile_id("http://localhost:1", "token", "nonexistent-profile")
    assert result is None


def test_safe_output_path_allows_nested_relative_paths(tmp_path: Path) -> None:
    from myace_cli.sync import safe_output_path

    assert safe_output_path(tmp_path, "CLAUDE.md") == tmp_path / "CLAUDE.md"
    nested = safe_output_path(tmp_path, ".claude/agents/builder.md")
    assert nested == tmp_path / ".claude" / "agents" / "builder.md"


@pytest.mark.parametrize(
    "bad",
    ["../x", "a/../../x", "/etc/passwd", "a//b", "", "a\\b", "..", "a/..", "x\0y"],
)
def test_safe_output_path_rejects_unsafe_names(tmp_path: Path, bad: str) -> None:
    from myace_cli.sync import safe_output_path

    assert safe_output_path(tmp_path, bad) is None
