"""Direct unit tests for myace_cli.scanner's private per-file parsers.

No scanner-level test file existed before this — these cover only the new
handoff_to frontmatter field (Epic 3.1) added to _parse_agent_file, kept
in sync with backend/app/services/scanner.py per AGENTS.md rule 8. Not a
general scanner test suite (a pre-existing gap, out of scope here).
"""

from pathlib import Path

from myace_cli.scanner import _parse_agent_file


def _write_agent_file(tmp_path: Path, frontmatter_extra: str) -> Path:
    content = f"""---
description: Test agent.
version: "1.0.0"
priority: 50
{frontmatter_extra}
---
Body text.
"""
    path = tmp_path / "test-agent.md"
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_agent_file_reads_handoff_to_list(tmp_path: Path) -> None:
    path = _write_agent_file(tmp_path, "handoff_to: [builder, verifier]")
    result = _parse_agent_file(path)
    assert result is not None
    assert result["handoff_to"] == ["builder", "verifier"]


def test_parse_agent_file_handoff_to_absent_is_none(tmp_path: Path) -> None:
    path = _write_agent_file(tmp_path, "mode: subagent")
    result = _parse_agent_file(path)
    assert result is not None
    assert result["handoff_to"] is None


def test_parse_agent_file_handoff_to_empty_list_is_not_none(tmp_path: Path) -> None:
    """An explicit empty list ('declared, terminal') must round-trip as
    [], not get coerced into None ('not declared')."""
    path = _write_agent_file(tmp_path, "handoff_to: []")
    result = _parse_agent_file(path)
    assert result is not None
    assert result["handoff_to"] == []
