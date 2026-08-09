"""Cline adapter — translates Canonical IR into Cline rules format."""

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact


class ClineAdapter(BaseAdapter):
    """Adapter for Cline — generates .clinerules/ files with YAML frontmatter."""

    def adapter_name(self) -> str:
        return "cline"

    def supported_targets(self) -> list[str]:
        return ["cline", "clinerules"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        files: dict[str, str] = {}

        for artifact in artifacts:
            if artifact.artifact_type == "rule":
                files[f".clinerules/{artifact.name}.md"] = self._format_rule(artifact)
            elif artifact.artifact_type == "skill":
                files[f".clinerules/skill-{artifact.name}.md"] = self._format_skill(artifact)
            elif artifact.artifact_type == "agent":
                files[f".clinerules/agent-{artifact.name}.md"] = self._format_agent(artifact)
            elif artifact.artifact_type == "workflow":
                files[f".clinerules/workflow-{artifact.name}.md"] = self._format_workflow(artifact)

        return files

    def _yaml_frontmatter(self, artifact: CanonicalArtifact, subtype: str) -> str:
        tags_str = ", ".join(artifact.tags) if artifact.tags else ""
        return (
            f"---\n"
            f"title: {artifact.name}\n"
            f"description: {artifact.description}\n"
            f"type: {subtype}\n"
            f"priority: {artifact.priority}\n"
            f"tags: [{tags_str}]\n"
            f"globs: {self._targets_to_globs(artifact.target_compatibility)}\n"
            f"---\n"
        )

    def _format_rule(self, artifact: CanonicalArtifact) -> str:
        return self._yaml_frontmatter(artifact, "rule") + artifact.body.strip() + "\n"

    def _format_skill(self, artifact: CanonicalArtifact) -> str:
        return self._yaml_frontmatter(artifact, "skill") + artifact.body.strip() + "\n"

    def _format_agent(self, artifact: CanonicalArtifact) -> str:
        return self._yaml_frontmatter(artifact, "agent") + artifact.body.strip() + "\n"

    def _format_workflow(self, artifact: CanonicalArtifact) -> str:
        return self._yaml_frontmatter(artifact, "workflow") + artifact.body.strip() + "\n"

    def _targets_to_globs(self, targets: list[str]) -> str:
        if not targets:
            return "['**/*']"
        items = [f"'**/*.{t}'" for t in targets if not t.startswith("*")]
        return "[" + ", ".join(items) + "]" if items else "['**/*']"
