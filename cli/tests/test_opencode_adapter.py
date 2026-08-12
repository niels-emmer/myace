"""Tests for the CLI-side OpenCode adapter — mirrors
backend/tests/test_adapters.py::TestOpenCodeAdapter. Verified against
https://opencode.ai/docs: skills/agents/commands are Markdown with YAML
frontmatter, only opencode.json is JSON."""

import json

import yaml

from myace_cli.adapters.opencode import OpenCodeAdapter


def test_translate_skill_creates_markdown_with_frontmatter():
    adapter = OpenCodeAdapter()
    result = adapter.translate([{
        "artifact_type": "skill", "name": "type-safety", "version": "1.0.0",
        "priority": 80, "tags": ["python"], "description": "Type safety rules",
        "body": "Use strict typing.", "target_compatibility": ["opencode"],
    }])
    path = ".opencode/skills/type-safety/SKILL.md"
    assert path in result
    frontmatter, body = result[path].split("---\n")[1:]
    parsed = yaml.safe_load(frontmatter)
    assert parsed.keys() <= {"name", "description", "compatibility", "metadata"}
    assert parsed["name"] == "type-safety"
    assert parsed["metadata"] == {"version": "1.0.0", "priority": 80, "tags": ["python"]}
    assert body.strip() == "Use strict typing."


def test_translate_agent_creates_markdown_with_mode_and_model():
    adapter = OpenCodeAdapter()
    result = adapter.translate([{
        "artifact_type": "agent", "name": "reviewer", "version": "1.0.0",
        "priority": 50, "tags": ["mode:subagent", "model:anthropic/claude-sonnet-4-5"],
        "description": "Reviews code", "body": "Be thorough.",
    }])
    path = ".opencode/agents/reviewer.md"
    assert path in result
    frontmatter = yaml.safe_load(result[path].split("---\n")[1])
    assert frontmatter == {
        "description": "Reviews code",
        "mode": "subagent",
        "model": "anthropic/claude-sonnet-4-5",
    }


def test_translate_workflow_creates_command_markdown():
    adapter = OpenCodeAdapter()
    result = adapter.translate([{
        "artifact_type": "workflow", "name": "ship", "version": "1.0.0",
        "priority": 50, "tags": [], "description": "Ship checklist", "body": "Run tests.",
    }])
    path = ".opencode/commands/ship.md"
    assert path in result
    frontmatter = yaml.safe_load(result[path].split("---\n")[1])
    assert frontmatter == {"description": "Ship checklist"}


def test_translate_rule_creates_agents_md():
    adapter = OpenCodeAdapter()
    result = adapter.translate([{
        "artifact_type": "rule", "name": "naming-convention", "version": "1.0.0",
        "priority": 70, "tags": ["style"], "description": "Naming rules",
        "body": "Use snake_case.",
    }])
    assert "AGENTS.md" in result
    assert "naming-convention" in result["AGENTS.md"]


def test_translate_model_configs_merge_into_single_opencode_json():
    adapter = OpenCodeAdapter()
    result = adapter.translate([
        {
            "artifact_type": "model_config", "name": "model:claude-sonnet-4-5",
            "version": "1.0.0", "priority": 50, "tags": ["provider:anthropic"],
            "description": "Model config", "body": json.dumps({"temperature": 0.2}),
        },
        {
            "artifact_type": "model_config", "name": "mcp:example-server",
            "version": "1.0.0", "priority": 50, "tags": ["mcp"],
            "description": "MCP server",
            "body": json.dumps({"type": "remote", "url": "https://example.com/mcp"}),
        },
    ])
    assert "opencode.json" in result
    config = json.loads(result["opencode.json"])
    assert config["provider"]["anthropic"]["models"]["claude-sonnet-4-5"] == {"temperature": 0.2}
    assert config["mcp"]["example-server"] == {
        "type": "remote", "url": "https://example.com/mcp",
    }
