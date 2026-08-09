"""Cursor adapter — translates Canonical IR into Cursor rules format."""

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact


class CursorAdapter(BaseAdapter):
    """Adapter for Cursor — generates .cursorrules and .cursor/rules/ files."""

    def adapter_name(self) -> str:
        return "cursor"

    def supported_targets(self) -> list[str]:
        return ["cursor", "cursor-editor"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        """
        Translate artifacts into Cursor format.

        Rules become entries in .cursorrules.
        Skills and agents become .mdc files in .cursor/rules/.
        """
        files: dict[str, str] = {}
        rules_lines: list[str] = []
        agent_skills: list[str] = []

        for artifact in artifacts:
            if artifact.artifact_type == "rule":
                rules_lines.append(self._format_cursor_rule(artifact))
            elif artifact.artifact_type in ("skill", "agent"):
                agent_skills.append(self._format_agent_skill(artifact))
            elif artifact.artifact_type == "workflow":
                files[f".cursor/workflows/{artifact.name}.mdc"] = self._format_mdc(artifact)
            elif artifact.artifact_type == "model_config":
                files[f".cursor/models/{artifact.name}.mdc"] = self._format_mdc(artifact)

        if rules_lines:
            files[".cursorrules"] = "# Cursor Rules\n\n" + "\n".join(rules_lines)

        for i, content in enumerate(agent_skills):
            files[f".cursor/rules/rule_{i:03d}.mdc"] = content

        return files

    def _format_cursor_rule(self, artifact: CanonicalArtifact) -> str:
        return (
            f"- **{artifact.name}** (priority {artifact.priority}): "
            f"{artifact.description}\n  {artifact.body.strip()}\n"
        )

    def _format_agent_skill(self, artifact: CanonicalArtifact) -> str:
        return (
            f"---\n"
            f"title: {artifact.name}\n"
            f"description: {artifact.description}\n"
            f"type: {artifact.artifact_type}\n"
            f"priority: {artifact.priority}\n"
            f"---\n"
            f"{artifact.body.strip()}\n"
        )

    def _format_mdc(self, artifact: CanonicalArtifact) -> str:
        return (
            f"---\n"
            f"title: {artifact.name}\n"
            f"description: {artifact.description}\n"
            f"type: {artifact.artifact_type}\n"
            f"---\n"
            f"{artifact.body.strip()}\n"
        )
