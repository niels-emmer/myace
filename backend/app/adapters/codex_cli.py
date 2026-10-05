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
import re

from app.adapters.base import BaseAdapter, safe_path_component, yaml_scalar
from app.models.artifact import CanonicalArtifact


class CodexCliAdapter(BaseAdapter):
    """Adapter for OpenAI Codex CLI — generates AGENTS.md, SKILL.md,
    .codex/agents/*.toml, and .codex/config.toml."""

    def adapter_name(self) -> str:
        return "codex-cli"

    def supported_targets(self) -> list[str]:
        return ["codex-cli", "codex", "openai-codex"]

    def expected_paths(self) -> list[str]:
        return ["AGENTS.md", ".agents/skills/", ".codex/agents/", ".codex/config.toml"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        files: dict[str, str] = {}
        rules_sections: list[str] = []
        model_configs: list[dict[str, object]] = []

        for artifact in artifacts:
            slug = safe_path_component(artifact.name)
            if artifact.artifact_type == "rule":
                rules_sections.append(self._format_rule(artifact))
            elif artifact.artifact_type == "skill":
                files[f".agents/skills/{slug}/SKILL.md"] = self._format_skill(artifact)
            elif artifact.artifact_type == "agent":
                files[f".codex/agents/{slug}.toml"] = self._format_agent(artifact)
            elif artifact.artifact_type == "model_config":
                # `mcp:<name>` artifacts (scanner encoding) are MCP servers,
                # not models — config.toml's `model`/`[model_providers]`
                # shape has no place for them, so they're skipped rather
                # than emitted as a bogus `model = "mcp:foo"`.
                if artifact.name.startswith("mcp:"):
                    continue
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
            f"name: {yaml_scalar(artifact.name)}\n"
            f"description: {yaml_scalar(artifact.description)}\n"
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
            self._toml_multiline_body(artifact.body.strip()),
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
    def _toml_escape(value: str, *, keep_newlines: bool) -> str:
        """Escape text for a TOML basic (multi-line) string: backslash and
        quote, plus control characters TOML forbids raw (as \\uXXXX)."""
        out: list[str] = []
        for ch in value:
            if ch == "\\":
                out.append("\\\\")
            elif ch == '"':
                out.append('\\"')
            elif ch == "\n":
                out.append("\n" if keep_newlines else "\\n")
            elif ch == "\t":
                out.append("\t" if keep_newlines else "\\t")
            elif ord(ch) < 0x20 or ord(ch) == 0x7F:
                out.append(f"\\u{ord(ch):04x}")
            else:
                out.append(ch)
        return "".join(out)

    @staticmethod
    def _toml_string(value: str) -> str:
        """Escape a value as a single-line TOML basic string."""
        return f'"{CodexCliAdapter._toml_escape(value, keep_newlines=False)}"'

    @staticmethod
    def _toml_multiline_body(value: str) -> str:
        """Escape a body for placement between `\"\"\"` delimiters. Every `"`
        is escaped, so the body can never close the string early and inject
        TOML keys, and a stray `\\d` is a literal backslash, not an invalid
        escape."""
        return CodexCliAdapter._toml_escape(value.replace("\r\n", "\n"), keep_newlines=True)

    @staticmethod
    def _toml_key(key: str) -> str:
        """A TOML key: bare when it only uses A-Za-z0-9_-, else quoted."""
        return key if re.fullmatch(r"[A-Za-z0-9_-]+", key) else CodexCliAdapter._toml_string(key)

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
            lines.append(f"[model_providers.{self._toml_key(provider_id)}]")
            for key, value in fields.items():
                lines.append(f"{self._toml_key(key)} = {self._toml_string(str(value))}")
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"
