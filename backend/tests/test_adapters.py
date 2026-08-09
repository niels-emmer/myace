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
    """Test OpenCode adapter translation."""

    def setup_method(self):
        self.adapter = get_adapter("opencode")

    def test_translate_skill_creates_json(self):
        """Skills should become JSON files."""
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
        assert ".opencode/skills/type-safety.json" in result
        import json
        data = json.loads(result[".opencode/skills/type-safety.json"])
        assert data["name"] == "type-safety"
        assert data["priority"] == 80

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
