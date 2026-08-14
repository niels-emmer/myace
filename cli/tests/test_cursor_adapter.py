"""Tests for the CLI-side Cursor adapter — mirrors
backend/tests/test_adapters.py::TestCursorAdapter."""

import yaml

from myace_cli.adapters.cursor import CursorAdapter


def test_translate_rule_creates_named_mdc_with_always_apply():
    adapter = CursorAdapter()
    result = adapter.translate([{
        "artifact_type": "rule", "name": "lint-before-commit", "version": "1.0.0",
        "priority": 90, "tags": ["quality"], "description": "Lint before commit",
        "body": "Run linter.",
    }])
    path = ".cursor/rules/lint-before-commit.mdc"
    assert path in result
    frontmatter = yaml.safe_load(result[path].split("---\n")[1])
    assert frontmatter["description"] == "Lint before commit"
    assert frontmatter["alwaysApply"] is True


def test_translate_skill_creates_named_mdc_agent_requested():
    adapter = CursorAdapter()
    result = adapter.translate([{
        "artifact_type": "skill", "name": "debugging", "version": "1.0.0",
        "priority": 50, "tags": [], "description": "Debugging guide",
        "body": "Use breakpoints.",
    }])
    path = ".cursor/rules/debugging.mdc"
    assert path in result
    frontmatter = yaml.safe_load(result[path].split("---\n")[1])
    assert frontmatter["alwaysApply"] is False


def test_translate_does_not_emit_legacy_cursorrules():
    adapter = CursorAdapter()
    result = adapter.translate([{
        "artifact_type": "rule", "name": "x", "version": "1.0.0",
        "priority": 50, "tags": [], "description": "x", "body": "x",
    }])
    assert ".cursorrules" not in result
