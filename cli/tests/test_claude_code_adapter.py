"""Tests for the CLI-side Claude Code adapter — mirrors
backend/tests/test_adapters.py::TestClaudeCodeAdapter."""

import yaml

from myace_cli.adapters.claude_code import ClaudeCodeAdapter


def test_translate_creates_claude_md_with_rules_only():
    adapter = ClaudeCodeAdapter()
    result = adapter.translate([
        {
            "artifact_type": "rule", "name": "test-rule", "version": "1.0.0",
            "priority": 80, "tags": ["python"], "description": "A test rule",
            "body": "Always use type annotations.",
        },
        {
            "artifact_type": "skill", "name": "test-skill", "version": "1.0.0",
            "priority": 50, "tags": ["testing"], "description": "A test skill",
            "body": "How to write tests.",
        },
    ])
    assert "CLAUDE.md" in result
    assert "test-rule" in result["CLAUDE.md"]
    assert "test-skill" not in result["CLAUDE.md"]


def test_translate_skill_creates_on_demand_skill_file():
    adapter = ClaudeCodeAdapter()
    result = adapter.translate([{
        "artifact_type": "skill", "name": "test-skill", "version": "1.0.0",
        "priority": 50, "tags": [], "description": "A test skill",
        "body": "How to write tests.",
    }])
    path = ".claude/skills/test-skill/SKILL.md"
    assert path in result
    content = result[path]
    assert content.startswith("---\n")
    frontmatter = yaml.safe_load(content.split("---\n")[1])
    assert frontmatter["name"] == "test-skill"
    assert frontmatter["description"] == "A test skill"
    assert "How to write tests." in content


def test_translate_agent_creates_separate_file_with_required_frontmatter():
    adapter = ClaudeCodeAdapter()
    result = adapter.translate([{
        "artifact_type": "agent", "name": "code-reviewer", "version": "1.0.0",
        "priority": 60, "tags": [], "description": "Code review agent",
        "body": "Review all PRs.",
    }])
    path = ".claude/agents/code-reviewer.md"
    assert path in result
    frontmatter = yaml.safe_load(result[path].split("---\n")[1])
    assert frontmatter["name"] == "code-reviewer"
    assert frontmatter["description"] == "Code review agent"


def test_translate_workflow_creates_command_file():
    adapter = ClaudeCodeAdapter()
    result = adapter.translate([{
        "artifact_type": "workflow", "name": "ship", "version": "1.0.0",
        "priority": 50, "tags": [], "description": "Ship it",
        "body": "1. Test.\n2. Push.",
    }])
    assert ".claude/commands/ship.md" in result


def test_translate_model_config_skipped():
    adapter = ClaudeCodeAdapter()
    result = adapter.translate([{
        "artifact_type": "model_config", "name": "sonnet", "version": "1.0.0",
        "priority": 50, "tags": [], "description": "", "body": "{}",
    }])
    assert result == {}
