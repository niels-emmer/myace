"""Windsurf adapter — translates Canonical IR into Windsurf rules format."""

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact


class WindsurfAdapter(BaseAdapter):
    """Adapter for Windsurf — generates .windsurf/rules/ with YAML frontmatter and trigger modes."""

    def adapter_name(self) -> str:
        return "windsurf"

    def supported_targets(self) -> list[str]:
        return ["windsurf", "codeium-windsurf"]

    def expected_paths(self) -> list[str]:
        return [".windsurf/rules/"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        files: dict[str, str] = {}

        for artifact in artifacts:
            trigger = self._trigger_for_artifact(artifact)
            content = self._format_file(artifact, trigger)
            name = artifact.name
            if artifact.artifact_type == "rule":
                files[f".windsurf/rules/{name}.md"] = content
            elif artifact.artifact_type == "skill":
                files[f".windsurf/rules/skill-{name}.md"] = content
            elif artifact.artifact_type == "agent":
                files[f".windsurf/rules/agent-{name}.md"] = content
            elif artifact.artifact_type == "workflow":
                files[f".windsurf/rules/workflow-{name}.md"] = content

        return files

    def _trigger_for_artifact(self, artifact: CanonicalArtifact) -> str:
        if artifact.priority >= 80:
            return "always_on"
        elif artifact.priority >= 50:
            return "model_decision"
        return "manual"

    def _format_file(self, artifact: CanonicalArtifact, trigger: str) -> str:
        return (
            f"---\n"
            f"title: {artifact.name}\n"
            f"description: {artifact.description}\n"
            f"type: {artifact.artifact_type}\n"
            f"trigger: {trigger}\n"
            f"priority: {artifact.priority}\n"
            f"globs: {self._targets_to_globs(artifact.target_compatibility)}\n"
            f"---\n"
            f"{artifact.body.strip()}\n"
        )

    def _targets_to_globs(self, targets: list[str]) -> str:
        if not targets:
            return "['**/*']"
        items = [f"'**/*.{t}'" for t in targets if not t.startswith("*")]
        return "[" + ", ".join(items) + "]" if items else "['**/*']"
