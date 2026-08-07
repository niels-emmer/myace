"""Claude Code adapter — translates Canonical IR into CLAUDE.md format."""

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact


class ClaudeCodeAdapter(BaseAdapter):
    """Adapter for Claude Code — generates CLAUDE.md and project-level rules."""

    def adapter_name(self) -> str:
        return "claude-code"

    def supported_targets(self) -> list[str]:
        return ["claude-code", "claude"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        """
        Translate artifacts into Claude Code format.

        Rules and skills become sections in CLAUDE.md.
        Agents become separate .md files in .claude/agents/.
        Workflows become .md files in .claude/workflows/.
        """
        files: dict[str, str] = {}
        rules_sections: list[str] = []
        skills_sections: list[str] = []

        for artifact in artifacts:
            if artifact.artifact_type == "rule":
                rules_sections.append(self._format_rule(artifact))
            elif artifact.artifact_type == "skill":
                skills_sections.append(self._format_skill(artifact))
            elif artifact.artifact_type == "agent":
                files[f".claude/agents/{artifact.name}.md"] = self._format_agent(artifact)
            elif artifact.artifact_type == "workflow":
                files[f".claude/workflows/{artifact.name}.md"] = self._format_workflow(artifact)
            elif artifact.artifact_type == "model_config":
                files[f".claude/models/{artifact.name}.md"] = self._format_model_config(artifact)

        # Build CLAUDE.md
        claude_md_parts = []
        if rules_sections:
            claude_md_parts.append("# Rules\n")
            claude_md_parts.extend(rules_sections)
        if skills_sections:
            claude_md_parts.append("\n# Skills\n")
            claude_md_parts.extend(skills_sections)

        if claude_md_parts:
            files["CLAUDE.md"] = "\n".join(claude_md_parts)

        return files

    def _format_rule(self, artifact: CanonicalArtifact) -> str:
        tags_str = ", ".join(artifact.tags) if artifact.tags else ""
        header = f"## {artifact.name}\n"
        header += f"> Priority: {artifact.priority} | Tags: {tags_str}\n\n"
        return header + artifact.body.strip() + "\n"

    def _format_skill(self, artifact: CanonicalArtifact) -> str:
        return f"## {artifact.name}\n\n{artifact.description}\n\n{artifact.body.strip()}\n"

    def _format_agent(self, artifact: CanonicalArtifact) -> str:
        return f"# {artifact.name}\n\n{artifact.description}\n\n{artifact.body.strip()}\n"

    def _format_workflow(self, artifact: CanonicalArtifact) -> str:
        return f"# {artifact.name}\n\n{artifact.description}\n\n{artifact.body.strip()}\n"

    def _format_model_config(self, artifact: CanonicalArtifact) -> str:
        return f"# {artifact.name}\n\n{artifact.body.strip()}\n"
