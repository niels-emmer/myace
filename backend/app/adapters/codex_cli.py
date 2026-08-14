"""Codex CLI adapter — translates Canonical IR into OpenAI Codex CLI format.

Verified against learn.chatgpt.com/docs/agents-md, /docs/build-skills,
/docs/agent-configuration/subagents, and /docs/config-file/config-reference
(Aug 2026). Confirmed correct: `AGENTS.md` at the project root for rules,
and `.agents/skills/<name>/SKILL.md` for skills (frontmatter: `name` +
`description` only — Codex CLI scans `.agents/skills` from cwd up to the
repo root). Confirmed WRONG and fixed here: custom subagents are **TOML**
files under `.codex/agents/<name>.toml` (project-scoped) or
`~/.codex/agents/` (personal), required fields `name`, `description`,
`developer_instructions` — not `.agents/agents/*.md` Markdown. There is no
"workflow" concept anywhere in Codex CLI (skills + subagents + MCP are the
only customization primitives), so `workflow` artifacts are skipped rather
than written to an invented path. `config.toml`'s real model/provider
schema is a top-level `model = "..."` string plus `[model_providers.<id>]`
tables (`name`, `base_url`, `env_key`, ...) — not a `[models]` table. Note:
project-scoped `.codex/config.toml` cannot override machine-local
provider/auth/profile-selection config per the docs — that must live in
`~/.codex/config.toml` — so a compiled project-local file may not take
effect for those fields even with the corrected schema; this is a real
platform constraint, not an adapter bug.
"""

import json

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact


class CodexCliAdapter(BaseAdapter):
    """Adapter for OpenAI Codex CLI — generates AGENTS.md, SKILL.md,
    .codex/agents/*.toml, and .codex/config.toml."""

    def adapter_name(self) -> str:
        return "codex-cli"

    def supported_targets(self) -> list[str]:
        return ["codex-cli", "codex", "openai-codex"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        files: dict[str, str] = {}
        rules_sections: list[str] = []
        model_configs: list[dict[str, object]] = []

        for artifact in artifacts:
            if artifact.artifact_type == "rule":
                rules_sections.append(self._format_rule(artifact))
            elif artifact.artifact_type == "skill":
                files[f".agents/skills/{artifact.name}/SKILL.md"] = self._format_skill(artifact)
            elif artifact.artifact_type == "agent":
                files[f".codex/agents/{artifact.name}.toml"] = self._format_agent(artifact)
            elif artifact.artifact_type == "model_config":
                model_configs.append(self._parse_model_config(artifact))
            # No "workflow" concept exists in Codex CLI — skipped.

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
            f"---\n"
            f"{artifact.body.strip()}\n"
        )

    def _format_agent(self, artifact: CanonicalArtifact) -> str:
        """Custom subagents are TOML, not Markdown — name/description/
        developer_instructions are the required fields."""
        lines = [
            f"name = {self._toml_string(artifact.name)}",
            f"description = {self._toml_string(artifact.description)}",
            'developer_instructions = """',
            artifact.body.strip(),
            '"""',
        ]
        return "\n".join(lines) + "\n"

    def _parse_model_config(self, artifact: CanonicalArtifact) -> dict[str, object]:
        try:
            parsed = json.loads(artifact.body)
            if isinstance(parsed, dict):
                return {"name": artifact.name, **parsed}
        except (json.JSONDecodeError, TypeError):
            pass
        return {"name": artifact.name, "provider": "openai", "model": artifact.name}

    @staticmethod
    def _toml_string(value: str) -> str:
        """Escape a value as a single-line TOML basic string."""
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'

    def _render_toml(self, model_configs: list[dict[str, object]]) -> str:
        """Render the real Codex CLI config.toml shape: a top-level `model`
        selector plus one [model_providers.<id>] table per distinct
        provider. The first model_config encountered becomes the active
        `model`, since config.toml has no equivalent of a model *list*."""
        active_model = model_configs[0].get("model", model_configs[0]["name"])
        lines = [f"model = {self._toml_string(str(active_model))}", ""]

        providers: dict[str, dict[str, object]] = {}
        for mc in model_configs:
            provider_id = str(mc.get("provider", "openai"))
            entry = providers.setdefault(provider_id, {"name": provider_id})
            extra = {k: v for k, v in mc.items() if k not in ("name", "provider", "model")}
            entry.update(extra)

        for provider_id, fields in providers.items():
            lines.append(f"[model_providers.{provider_id}]")
            for key, value in fields.items():
                lines.append(f"{key} = {self._toml_string(str(value))}")
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"
