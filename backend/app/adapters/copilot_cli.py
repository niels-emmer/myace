"""GitHub Copilot CLI adapter — translates Canonical IR into Copilot instructions format."""

import json

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact


class CopilotCliAdapter(BaseAdapter):
    """Adapter for GitHub Copilot CLI — generates copilot-instructions.md and .instructions.md."""

    def adapter_name(self) -> str:
        return "copilot-cli"

    def supported_targets(self) -> list[str]:
        return ["copilot-cli", "copilot", "github-copilot"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        files: dict[str, str] = {}
        rules_entries: list[str] = []

        for artifact in artifacts:
            if artifact.artifact_type == "rule":
                rules_entries.append(self._format_copilot_rule(artifact))
            elif artifact.artifact_type == "skill":
                files[
                    f".github/instructions/{artifact.name}.instructions.md"
                ] = self._format_instructions_file(artifact, "skill")
            elif artifact.artifact_type == "agent":
                files[
                    f".github/instructions/agent-{artifact.name}.instructions.md"
                ] = self._format_instructions_file(artifact, "agent")
            elif artifact.artifact_type == "workflow":
                files[
                    f".github/instructions/workflow-{artifact.name}.instructions.md"
                ] = self._format_instructions_file(artifact, "workflow")
            elif artifact.artifact_type == "model_config":
                files[
                    f".github/instructions/model-{artifact.name}.instructions.md"
                ] = self._format_instructions_file(artifact, "model_config")

        if rules_entries:
            files[".github/copilot-instructions.md"] = (
                "# Copilot Instructions\n\n" + "\n".join(rules_entries)
            )

        return files

    def _format_copilot_rule(self, artifact: CanonicalArtifact) -> str:
        return (
            f"## {artifact.name}\n\n"
            f"{artifact.description}\n\n"
            f"{artifact.body.strip()}\n"
        )

    def _format_instructions_file(self, artifact: CanonicalArtifact, artifact_type: str) -> str:
        globs = self._targets_to_globs(artifact.target_compatibility)
        return (
            f"---\n"
            f"title: {artifact.name}\n"
            f"description: {artifact.description}\n"
            f"applyTo: {json.dumps(globs)}\n"
            f"type: {artifact_type}\n"
            f"priority: {artifact.priority}\n"
            f"---\n"
            f"{artifact.body.strip()}\n"
        )

    def _targets_to_globs(self, targets: list[str]) -> list[str]:
        if not targets:
            return ["**/*.py", "**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"]
        return [f"**/*.{t}" for t in targets if not t.startswith("*")] or ["**/*"]
