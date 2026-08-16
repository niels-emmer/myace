"""Aider adapter — translates Canonical IR into Aider's conventions format.

Verified against https://aider.chat/docs/usage/conventions.html: coding
guidelines live in a plain Markdown `CONVENTIONS.md`, and `.aider.conf.yml`
carries a `read:` key that tells Aider to always load it (read-only,
cached). Aider has no native concept of skills/agents/workflows, so those
artifact types fold into `CONVENTIONS.md` as additional sections rather
than being dropped.
"""

import json

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact


class AiderAdapter(BaseAdapter):
    """Adapter for Aider — generates CONVENTIONS.md and .aider.conf.yml."""

    def adapter_name(self) -> str:
        return "aider"

    def supported_targets(self) -> list[str]:
        return ["aider"]

    def expected_paths(self) -> list[str]:
        return ["CONVENTIONS.md", ".aider.conf.yml"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        files: dict[str, str] = {}
        sections: list[str] = []
        model_name: str | None = None

        for artifact in artifacts:
            if artifact.artifact_type == "rule":
                sections.append(self._format_section(artifact, "Rule"))
            elif artifact.artifact_type == "skill":
                sections.append(self._format_section(artifact, "Skill"))
            elif artifact.artifact_type == "agent":
                sections.append(self._format_section(artifact, "Agent"))
            elif artifact.artifact_type == "workflow":
                sections.append(self._format_section(artifact, "Workflow"))
            elif artifact.artifact_type == "model_config":
                model_name = self._parse_model_name(artifact)

        if sections:
            files["CONVENTIONS.md"] = "# Conventions\n\n" + "\n".join(sections)

        conf_lines: list[str] = []
        if "CONVENTIONS.md" in files:
            conf_lines.append("read: CONVENTIONS.md")
        if model_name:
            conf_lines.append(f"model: {model_name}")
        if conf_lines:
            files[".aider.conf.yml"] = "\n".join(conf_lines) + "\n"

        return files

    def _format_section(self, artifact: CanonicalArtifact, kind: str) -> str:
        tags_str = ", ".join(artifact.tags) if artifact.tags else ""
        header = f"## {artifact.name}\n"
        header += f"> {kind} | Priority: {artifact.priority} | Tags: {tags_str}\n\n"
        if artifact.description:
            header += f"{artifact.description}\n\n"
        return header + artifact.body.strip() + "\n"

    def _parse_model_name(self, artifact: CanonicalArtifact) -> str:
        try:
            parsed = json.loads(artifact.body) if artifact.body else {}
            if isinstance(parsed, dict) and parsed.get("model"):
                return str(parsed["model"])
        except (json.JSONDecodeError, TypeError):
            pass
        return artifact.name
