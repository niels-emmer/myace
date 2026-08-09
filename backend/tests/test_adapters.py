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
