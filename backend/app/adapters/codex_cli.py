"""Codex CLI adapter — translates Canonical IR into Codex CLI format."""

import json

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact


class CodexCliAdapter(BaseAdapter):
    """Adapter for OpenAI Codex CLI — generates AGENTS.md, SKILL.md, and config.toml."""

    def adapter_name(self) -> str:
        return "codex-cli"

    def supported_targets(self) -> list[str]:
        return ["codex-cli", "codex", "openai-codex"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        files: dict[str, str] = {}
        rules_sections: list[str] = []
        model_configs: list[dict] = []

        for artifact in artifacts:
            if artifact.artifact_type == "rule":
                rules_sections.append(self._format_rule(artifact))
            elif artifact.artifact_type == "skill":
                files[f".agents/skills/{artifact.name}/SKILL.md"] = self._format_skill(artifact)
            elif artifact.artifact_type == "agent":
                files[f".agents/agents/{artifact.name}.md"] = self._format_agent(artifact)
            elif artifact.artifact_type == "workflow":
                files[f".agents/workflows/{artifact.name}.md"] = self._format_workflow(artifact)
            elif artifact.artifact_type == "model_config":
                model_configs.append(self._parse_model_config(artifact))

        if rules_sections:
            files["AGENTS.md"] = "# Codex CLI Rules\n\n" + "\n".join(rules_sections)

        if model_configs:
            files[".codex/config.toml"] = self._render_toml(model_configs)

        return files

    def _format_rule(self, artifact: CanonicalArtifact) -> str:
        tags_str = ", ".join(artifact.tags) if artifact.tags else ""
        header = f"## {artifact.name}\n"
        header += f"> Priority: {artifact.priority} | Tags: {tags_str}\n\n"
        return header + artifact.body.strip() + "\n"

    def _format_skill(self, artifact: CanonicalArtifact) -> str:
        return (
            f"---\n"
            f"name: {artifact.name}\n"
            f"description: {artifact.description}\n"
            f"priority: {artifact.priority}\n"
            f"---\n"
            f"{artifact.body.strip()}\n"
        )

    def _format_agent(self, artifact: CanonicalArtifact) -> str:
        return f"# {artifact.name}\n\n{artifact.description}\n\n{artifact.body.strip()}\n"

    def _format_workflow(self, artifact: CanonicalArtifact) -> str:
        return f"# {artifact.name}\n\n{artifact.description}\n\n{artifact.body.strip()}\n"

    def _parse_model_config(self, artifact: CanonicalArtifact) -> dict:
        try:
            parsed = json.loads(artifact.body)
            if isinstance(parsed, dict):
                return {"name": artifact.name, **parsed}
        except (json.JSONDecodeError, TypeError):
            pass
        return {"name": artifact.name, "provider": "openai", "model": artifact.name}

    @staticmethod
    def _render_toml(model_configs: list[dict]) -> str:
        """Render model configs as a minimal TOML string (no external dep needed)."""
        lines = ["[models]"]
        for mc in model_configs:
            name = mc["name"]
            provider = mc.get("provider", "openai")
            model = mc.get("model", name)
            lines.append(f'{name} = {{ provider = "{provider}", model = "{model}" }}')
        lines.append("\n[mcp]")
        lines.append("servers = []")
        return "\n".join(lines) + "\n"
