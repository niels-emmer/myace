"""Tests for target adapters."""

from app.adapters import get_adapter, list_adapters
from app.models.artifact import CanonicalArtifact


class TestAdapterRegistry:
    """Test adapter registration and lookup."""

    def test_list_adapters(self):
        """Should list all registered adapters."""
        adapters = list_adapters()
        names = [a.adapter_name() for a in adapters]
        assert "claude-code" in names
        assert "opencode" in names
        assert "cursor" in names
        assert "codex-cli" in names
        assert "copilot-cli" in names
        assert "cline" in names
        assert "windsurf" in names

    def test_get_adapter(self):
        """Should retrieve adapter by name."""
        adapter = get_adapter("claude-code")
        assert adapter is not None
        assert adapter.adapter_name() == "claude-code"

    def test_get_nonexistent_adapter(self):
        """Should return None for unknown adapter."""
        adapter = get_adapter("nonexistent")
        assert adapter is None


class TestClaudeCodeAdapter:
    """Test Claude Code adapter translation."""

    def setup_method(self):
        self.adapter = get_adapter("claude-code")
        self.artifacts = [
            CanonicalArtifact(
                artifact_type="rule",
                name="test-rule",
                version="1.0.0",
                target_compatibility=["claude-code"],
                priority=80,
                tags=["python"],
                description="A test rule",
                body="Always use type annotations.",
            ),
            CanonicalArtifact(
                artifact_type="skill",
                name="test-skill",
                version="1.0.0",
                target_compatibility=["claude-code"],
                priority=50,
                tags=["testing"],
                description="A test skill",
                body="How to write tests.",
            ),
        ]

    def test_translate_returns_dict(self):
        """Translate should return a dict of filename -> content."""
        result = self.adapter.translate(self.artifacts)
        assert isinstance(result, dict)

    def test_translate_creates_claude_md(self):
        """Should generate CLAUDE.md with rules and skills."""
        result = self.adapter.translate(self.artifacts)
        assert "CLAUDE.md" in result
        assert "test-rule" in result["CLAUDE.md"]
        assert "test-skill" in result["CLAUDE.md"]

    def test_translate_agent_creates_separate_file(self):
        """Agent artifacts should become separate files."""
        agent = CanonicalArtifact(
            artifact_type="agent",
            name="code-reviewer",
            version="1.0.0",
            target_compatibility=["claude-code"],
            priority=60,
            tags=[],
            description="Code review agent",
            body="Review all PRs.",
        )
        result = self.adapter.translate([agent])
        assert ".claude/agents/code-reviewer.md" in result


class TestOpenCodeAdapter:
    """Test OpenCode adapter translation — verified against
    https://opencode.ai/docs: skills/agents/commands are Markdown with YAML
    frontmatter, only opencode.json is JSON."""

    def setup_method(self):
        self.adapter = get_adapter("opencode")

    def test_translate_skill_creates_markdown_with_frontmatter(self):
        skill = CanonicalArtifact(
            artifact_type="skill",
            name="type-safety",
            version="1.0.0",
            target_compatibility=["opencode"],
            priority=80,
            tags=["python"],
            description="Type safety rules",
            body="Use strict typing.",
        )
        result = self.adapter.translate([skill])
        path = ".opencode/skills/type-safety/SKILL.md"
        assert path in result
        content = result[path]
        assert content.startswith("---\n")
        frontmatter, body = content.split("---\n", 2)[1:]
        import yaml
        parsed = yaml.safe_load(frontmatter)
        # Only OpenCode's own recognized skill fields at the top level.
        assert parsed.keys() <= {"name", "description", "compatibility", "metadata"}
        assert parsed["name"] == "type-safety"
        assert parsed["description"] == "Type safety rules"
        assert parsed["metadata"] == {"version": "1.0.0", "priority": 80, "tags": ["python"]}
        assert body.strip() == "Use strict typing."

    def test_translate_agent_creates_markdown_with_mode_and_model(self):
        agent = CanonicalArtifact(
            artifact_type="agent",
            name="reviewer",
            version="1.0.0",
            target_compatibility=["opencode"],
            priority=50,
            tags=["mode:subagent", "model:anthropic/claude-sonnet-4-5"],
            description="Reviews code",
            body="You are a thorough code reviewer.",
        )
        result = self.adapter.translate([agent])
        path = ".opencode/agents/reviewer.md"
        assert path in result
        import yaml
        frontmatter = yaml.safe_load(result[path].split("---\n")[1])
        assert frontmatter == {
            "description": "Reviews code",
            "mode": "subagent",
            "model": "anthropic/claude-sonnet-4-5",
        }
        assert "You are a thorough code reviewer." in result[path]

    def test_translate_workflow_creates_command_markdown(self):
        workflow = CanonicalArtifact(
            artifact_type="workflow",
            name="ship",
            version="1.0.0",
            target_compatibility=["opencode"],
            priority=50,
            tags=[],
            description="Pre-ship checklist",
            body="Run tests, then commit.",
        )
        result = self.adapter.translate([workflow])
        path = ".opencode/commands/ship.md"
        assert path in result
        import yaml
        frontmatter = yaml.safe_load(result[path].split("---\n")[1])
        assert frontmatter == {"description": "Pre-ship checklist"}

    def test_translate_rule_creates_agents_md(self):
        """Rules should become AGENTS.md entries."""
        rule = CanonicalArtifact(
            artifact_type="rule",
            name="naming-convention",
            version="1.0.0",
            target_compatibility=["opencode"],
            priority=70,
            tags=["style"],
            description="Naming rules",
            body="Use snake_case.",
        )
        result = self.adapter.translate([rule])
        assert "AGENTS.md" in result
        assert "naming-convention" in result["AGENTS.md"]

    def test_translate_model_configs_merge_into_single_opencode_json(self):
        import json

        model = CanonicalArtifact(
            artifact_type="model_config",
            name="model:claude-sonnet-4-5",
            version="1.0.0",
            target_compatibility=["opencode"],
            priority=50,
            tags=["provider:anthropic"],
            description="Model config",
            body=json.dumps({"temperature": 0.2}),
        )
        mcp = CanonicalArtifact(
            artifact_type="model_config",
            name="mcp:example-server",
            version="1.0.0",
            target_compatibility=["opencode"],
            priority=50,
            tags=["mcp"],
            description="MCP server",
            body=json.dumps({"type": "remote", "url": "https://example.com/mcp"}),
        )
        result = self.adapter.translate([model, mcp])
        assert ".opencode/models" not in "".join(result.keys())
        assert "opencode.json" in result
        config = json.loads(result["opencode.json"])
        assert config["provider"]["anthropic"]["models"]["claude-sonnet-4-5"] == {"temperature": 0.2}
        assert config["mcp"]["example-server"] == {
            "type": "remote", "url": "https://example.com/mcp",
        }

    def test_compiled_skill_round_trips_through_the_scanner(self, tmp_path):
        """A skill compiled to OpenCode format must scan back in with its
        version/priority/tags intact — they live under SKILL.md's
        explicitly free-form `metadata` field since OpenCode itself doesn't
        recognize them at the top level (see _format_skill)."""
        from pathlib import Path

        from app.services.scanner import _parse_skill_file

        skill = CanonicalArtifact(
            artifact_type="skill",
            name="git-release",
            version="2.3.0",
            target_compatibility=["opencode"],
            priority=77,
            tags=["maintainers", "releases"],
            description="Create releases",
            body="Do the release thing.",
        )
        result = self.adapter.translate([skill])
        skill_dir = tmp_path / "skills" / "git-release"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(result[".opencode/skills/git-release/SKILL.md"])

        parsed = _parse_skill_file(Path(skill_file))
        assert parsed["name"] == "git-release"
        assert parsed["version"] == "2.3.0"
        assert parsed["priority"] == 77
        assert parsed["tags"] == ["maintainers", "releases"]
        assert parsed["description"] == "Create releases"
        assert parsed["body"] == "Do the release thing."


class TestCursorAdapter:
    """Test Cursor adapter translation."""

    def setup_method(self):
        self.adapter = get_adapter("cursor")

    def test_translate_rule_creates_cursorrules(self):
        """Rules should become .cursorrules entries."""
        rule = CanonicalArtifact(
            artifact_type="rule",
            name="lint-before-commit",
            version="1.0.0",
            target_compatibility=["cursor"],
            priority=90,
            tags=["quality"],
            description="Lint before commit",
            body="Run linter.",
        )
        result = self.adapter.translate([rule])
        assert ".cursorrules" in result
        assert "lint-before-commit" in result[".cursorrules"]

    def test_translate_skill_creates_mdc(self):
        """Skills should become .mdc files."""
        skill = CanonicalArtifact(
            artifact_type="skill",
            name="debugging",
            version="1.0.0",
            target_compatibility=["cursor"],
            priority=50,
            tags=[],
            description="Debugging guide",
            body="Use breakpoints.",
        )
        result = self.adapter.translate([skill])
        mdc_files = [k for k in result if k.endswith(".mdc")]
        assert len(mdc_files) > 0


class TestCodexCliAdapter:
    """Test Codex CLI adapter translation."""

    def setup_method(self):
        self.adapter = get_adapter("codex-cli")

    def test_translate_rule_creates_agents_md(self):
        """Rules should become AGENTS.md entries."""
        rule = CanonicalArtifact(
            artifact_type="rule",
            name="type-safety",
            version="1.0.0",
            target_compatibility=["python"],
            priority=80,
            tags=["python"],
            description="Type safety rules",
            body="Use strict typing.",
        )
        result = self.adapter.translate([rule])
        assert "AGENTS.md" in result
        assert "type-safety" in result["AGENTS.md"]

    def test_translate_skill_creates_skill_md(self):
        """Skills should become .agents/skills/<name>/SKILL.md files."""
        skill = CanonicalArtifact(
            artifact_type="skill",
            name="testing",
            version="1.0.0",
            target_compatibility=[],
            priority=50,
            tags=[],
            description="Testing guide",
            body="Write tests first.",
        )
        result = self.adapter.translate([skill])
        assert ".agents/skills/testing/SKILL.md" in result
        assert "Write tests first." in result[".agents/skills/testing/SKILL.md"]

    def test_translate_agent_creates_separate_file(self):
        """Agent artifacts should become separate .md files."""
        agent = CanonicalArtifact(
            artifact_type="agent",
            name="reviewer",
            version="1.0.0",
            target_compatibility=[],
            priority=60,
            tags=[],
            description="Code review agent",
            body="Review all PRs.",
        )
        result = self.adapter.translate([agent])
        assert ".agents/agents/reviewer.md" in result

    def test_translate_model_config_creates_toml(self):
        """Model configs should become .codex/config.toml."""
        mc = CanonicalArtifact(
            artifact_type="model_config",
            name="gpt-4o",
            version="1.0.0",
            target_compatibility=[],
            priority=50,
            tags=[],
            description="Default model",
            body='{"provider": "openai", "model": "gpt-4o"}',
        )
        result = self.adapter.translate([mc])
        assert ".codex/config.toml" in result
        assert "gpt-4o" in result[".codex/config.toml"]
        assert "[models]" in result[".codex/config.toml"]


class TestCopilotCliAdapter:
    """Test GitHub Copilot CLI adapter translation."""

    def setup_method(self):
        self.adapter = get_adapter("copilot-cli")

    def test_translate_rule_creates_copilot_instructions(self):
        """Rules should become .github/copilot-instructions.md."""
        rule = CanonicalArtifact(
            artifact_type="rule",
            name="naming-convention",
            version="1.0.0",
            target_compatibility=["python"],
            priority=70,
            tags=["style"],
            description="Naming rules",
            body="Use snake_case.",
        )
        result = self.adapter.translate([rule])
        assert ".github/copilot-instructions.md" in result
        assert "naming-convention" in result[".github/copilot-instructions.md"]

    def test_translate_skill_creates_instructions_file(self):
        """Skills should become .instructions.md files with YAML frontmatter."""
        skill = CanonicalArtifact(
            artifact_type="skill",
            name="debugging",
            version="1.0.0",
            target_compatibility=["py"],
            priority=50,
            tags=[],
            description="Debugging guide",
            body="Use breakpoints.",
        )
        result = self.adapter.translate([skill])
        key = ".github/instructions/debugging.instructions.md"
        assert key in result
        assert "applyTo" in result[key]
        assert "debugging" in result[key]

    def test_translate_agent_creates_instructions_file(self):
        """Agent artifacts should become agent-prefixed .instructions.md files."""
        agent = CanonicalArtifact(
            artifact_type="agent",
            name="tester",
            version="1.0.0",
            target_compatibility=[],
            priority=60,
            tags=[],
            description="Test agent",
            body="Run tests.",
        )
        result = self.adapter.translate([agent])
        assert ".github/instructions/agent-tester.instructions.md" in result


class TestClineAdapter:
    """Test Cline adapter translation."""

    def setup_method(self):
        self.adapter = get_adapter("cline")

    def test_translate_rule_creates_clinerules_file(self):
        """Rules should become .clinerules/<name>.md files."""
        rule = CanonicalArtifact(
            artifact_type="rule",
            name="lint-before-commit",
            version="1.0.0",
            target_compatibility=["python"],
            priority=90,
            tags=["quality"],
            description="Lint before commit",
            body="Run linter.",
        )
        result = self.adapter.translate([rule])
        assert ".clinerules/lint-before-commit.md" in result
        assert "Run linter." in result[".clinerules/lint-before-commit.md"]

    def test_translate_skill_creates_clinerules_file(self):
        """Skills should become skill-prefixed .clinerules files."""
        skill = CanonicalArtifact(
            artifact_type="skill",
            name="testing",
            version="1.0.0",
            target_compatibility=[],
            priority=50,
            tags=[],
            description="Testing guide",
            body="Write tests.",
        )
        result = self.adapter.translate([skill])
        assert ".clinerules/skill-testing.md" in result
        assert "type: skill" in result[".clinerules/skill-testing.md"]

    def test_translate_agent_creates_clinerules_file(self):
        """Agent artifacts should become agent-prefixed .clinerules files."""
        agent = CanonicalArtifact(
            artifact_type="agent",
            name="reviewer",
            version="1.0.0",
            target_compatibility=[],
            priority=60,
            tags=[],
            description="Review agent",
            body="Review code.",
        )
        result = self.adapter.translate([agent])
        assert ".clinerules/agent-reviewer.md" in result
        assert "type: agent" in result[".clinerules/agent-reviewer.md"]


class TestWindsurfAdapter:
    """Test Windsurf adapter translation."""

    def setup_method(self):
        self.adapter = get_adapter("windsurf")

    def test_translate_rule_creates_windsurf_rule(self):
        """Rules should become .windsurf/rules/<name>.md files."""
        rule = CanonicalArtifact(
            artifact_type="rule",
            name="type-safety",
            version="1.0.0",
            target_compatibility=["python"],
            priority=80,
            tags=["python"],
            description="Type safety",
            body="Use strict typing.",
        )
        result = self.adapter.translate([rule])
        assert ".windsurf/rules/type-safety.md" in result
        assert "trigger: always_on" in result[".windsurf/rules/type-safety.md"]

    def test_translate_high_priority_uses_always_on_trigger(self):
        """Priority >= 80 should use always_on trigger."""
        rule = CanonicalArtifact(
            artifact_type="rule",
            name="critical",
            version="1.0.0",
            target_compatibility=[],
            priority=90,
            tags=[],
            description="Critical rule",
            body="Must follow.",
        )
        result = self.adapter.translate([rule])
        assert "trigger: always_on" in result[".windsurf/rules/critical.md"]

    def test_translate_medium_priority_uses_model_decision_trigger(self):
        """Priority 50-79 should use model_decision trigger."""
        rule = CanonicalArtifact(
            artifact_type="rule",
            name="suggestion",
            version="1.0.0",
            target_compatibility=[],
            priority=60,
            tags=[],
            description="Suggestion",
            body="Consider this.",
        )
        result = self.adapter.translate([rule])
        assert "trigger: model_decision" in result[".windsurf/rules/suggestion.md"]

    def test_translate_low_priority_uses_manual_trigger(self):
        """Priority < 50 should use manual trigger."""
        rule = CanonicalArtifact(
            artifact_type="rule",
            name="optional",
            version="1.0.0",
            target_compatibility=[],
            priority=30,
            tags=[],
            description="Optional",
            body="Nice to have.",
        )
        result = self.adapter.translate([rule])
        assert "trigger: manual" in result[".windsurf/rules/optional.md"]
