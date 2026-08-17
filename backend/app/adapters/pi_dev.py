"""pi.dev (Pi Coding Agent) adapter — translates Canonical IR into Pi's real on-disk format.

Verified against https://pi.dev/docs/latest/usage, /skills, /prompt-templates,
and /settings (Aug 2026): Pi loads `AGENTS.md` (or `CLAUDE.md`) hierarchically
from the cwd and its parent directories, same mechanism as OpenCode/Goose, so
`rule` artifacts fold into a single root `AGENTS.md`. Pi has a real skills
system — `.pi/skills/<name>/SKILL.md`, YAML frontmatter + Markdown, with the
same `name`/`description`/`license`/`compatibility`/`metadata` fields
OpenCode's skill format uses (`allowed-tools` and `disable-model-invocation`
also exist but have no Canonical IR equivalent to source them from, so this
adapter omits them rather than fabricate values). Pi also has a real
slash-command mechanism — "prompt templates" at `.pi/prompts/<name>.md`,
frontmatter `description` (+ optional `argument-hint`, which Canonical IR has
no field for) — so `workflow` artifacts map there rather than folding into
AGENTS.md. Pi has no documented subagent/agent concept (the full docs nav has
no "agents" page distinct from skills), so `agent` artifacts fold into
`AGENTS.md` as a labeled section, the same fallback OpenCode/Goose use for
artifact types their target doesn't have a dedicated file for.

`model_config` artifacts named `model:<name>` (scanner's encoding, tagged
`provider:<provider>`) merge into `.pi/settings.json`'s `defaultProvider`/
`defaultModel` (first one wins) and `enabledModels` (every model name, which
`/docs/latest/settings` confirms accepts literal model IDs, not just glob
patterns). `model_config` artifacts named `mcp:<name>` are deliberately
skipped: `pi.dev/docs/latest/mcp` 404s, and the only MCP config shape found
(a `~/.pi/agent/mcp.json` / `.pi/mcp.json` file with a `mcpServers` object)
comes from third-party sources (`pi-mcp-adapter`, `oh-my-pi`), not pi.dev's
own docs — not confirmed with enough confidence to ship, left as a follow-up
once the format is verified against primary docs, same standard the
Continue adapter holds itself to for its own unconfirmed half.
"""

import json

import yaml

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact

_AGENTS_MD_LABELS = {"rule": "Rule", "agent": "Agent"}


class PiDevAdapter(BaseAdapter):
    """Adapter for pi.dev (Pi Coding Agent) — generates AGENTS.md,
    .pi/skills/*/SKILL.md, .pi/prompts/*.md, and .pi/settings.json."""

    def adapter_name(self) -> str:
        return "pi-dev"

    def supported_targets(self) -> list[str]:
        return ["pi-dev", "pi"]

    def expected_paths(self) -> list[str]:
        return ["AGENTS.md", ".pi/skills/", ".pi/prompts/", ".pi/settings.json"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        files: dict[str, str] = {}
        agents_md_sections: list[str] = []
        models: list[dict[str, str]] = []

        for artifact in artifacts:
            if artifact.artifact_type in _AGENTS_MD_LABELS:
                agents_md_sections.append(
                    self._format_agents_md_section(
                        artifact, _AGENTS_MD_LABELS[artifact.artifact_type]
                    )
                )
            elif artifact.artifact_type == "skill":
                files[f".pi/skills/{artifact.name}/SKILL.md"] = self._format_skill(artifact)
            elif artifact.artifact_type == "workflow":
                files[f".pi/prompts/{artifact.name}.md"] = self._format_prompt_template(artifact)
            elif artifact.artifact_type == "model_config" and artifact.name.startswith("model:"):
                self._collect_model(artifact, models)

        if agents_md_sections:
            files["AGENTS.md"] = "# AGENTS.md\n\n" + "\n".join(agents_md_sections)

        if models:
            files[".pi/settings.json"] = self._build_settings_json(models)

        return files

    def _format_agents_md_section(self, artifact: CanonicalArtifact, label: str) -> str:
        header = f"## {artifact.name} ({label})\n\n"
        if artifact.description:
            header += f"{artifact.description}\n\n"
        return header + artifact.body.strip() + "\n"

    def _format_skill(self, artifact: CanonicalArtifact) -> str:
        frontmatter: dict[str, object] = {
            "name": artifact.name,
            "description": artifact.description,
        }
        if artifact.target_compatibility:
            frontmatter["compatibility"] = artifact.target_compatibility
        frontmatter["metadata"] = {
            "version": artifact.version,
            "priority": artifact.priority,
            "tags": artifact.tags,
        }
        yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, default_flow_style=False).strip()
        return f"---\n{yaml_text}\n---\n\n{artifact.body.strip()}\n"

    def _format_prompt_template(self, artifact: CanonicalArtifact) -> str:
        frontmatter = {"description": artifact.description}
        yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, default_flow_style=False).strip()
        return f"---\n{yaml_text}\n---\n\n{artifact.body.strip()}\n"

    def _collect_model(self, artifact: CanonicalArtifact, models: list[dict[str, str]]) -> None:
        model_name = artifact.name.split(":", 1)[1]
        provider_name = next(
            (t.split(":", 1)[1] for t in artifact.tags if t.startswith("provider:")),
            "anthropic",
        )
        models.append({"name": model_name, "provider": provider_name})

    def _build_settings_json(self, models: list[dict[str, str]]) -> str:
        first = models[0]
        config: dict[str, object] = {
            "defaultProvider": first["provider"],
            "defaultModel": first["name"],
            "enabledModels": [m["name"] for m in models],
        }
        return json.dumps(config, indent=2)
