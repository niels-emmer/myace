"""Claude Code adapter — translates Canonical IR into CLAUDE.md format.

Verified against code.claude.com/docs/en/sub-agents, code.claude.com/docs/en/
slash-commands, and code.claude.com/docs/en/model-config (Aug 2026): subagent
files (.claude/agents/*.md) require YAML frontmatter with at least name +
description — identity comes from the name field, not the filename, so a
bare heading with no frontmatter isn't a valid agent definition. Commands
were merged into skills; the current recommended format for on-demand
capabilities is .claude/skills/<name>/SKILL.md (this is also how this
adapter's `skill` artifacts are now emitted, instead of being inlined into
always-loaded CLAUDE.md — real Claude Code skills are loaded on demand, not
up front). `workflow` artifacts map to the still-supported legacy slash
command format at .claude/commands/<name>.md. There is no repo-committed
model-config file convention (model selection is via /model, --model, the
ANTHROPIC_MODEL env var, or the model field in .claude/settings.json) —
model_config artifacts are skipped, matching the precedent set by the Amazon
Q and Goose adapters for target frameworks that don't support a given
artifact type.
"""

import yaml

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact


class ClaudeCodeAdapter(BaseAdapter):
    """Adapter for Claude Code — generates CLAUDE.md, .claude/agents/,
    .claude/skills/, and .claude/commands/."""

    def adapter_name(self) -> str:
        return "claude-code"

    def supported_targets(self) -> list[str]:
        return ["claude-code", "claude"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        """
        Translate artifacts into Claude Code format.

        Rules become sections in CLAUDE.md. Skills become
        .claude/skills/<name>/SKILL.md (loaded on demand). Agents become
        .claude/agents/<name>.md with required name/description frontmatter.
        Workflows become .claude/commands/<name>.md. model_config has no
        repo-committed file convention and is skipped.
        """
        files: dict[str, str] = {}
        rules_sections: list[str] = []

        for artifact in artifacts:
            if artifact.artifact_type == "rule":
                rules_sections.append(self._format_rule(artifact))
            elif artifact.artifact_type == "skill":
                files[f".claude/skills/{artifact.name}/SKILL.md"] = self._format_skill(artifact)
            elif artifact.artifact_type == "agent":
                files[f".claude/agents/{artifact.name}.md"] = self._format_agent(artifact)
            elif artifact.artifact_type == "workflow":
                files[f".claude/commands/{artifact.name}.md"] = self._format_command(artifact)

        if rules_sections:
            files["CLAUDE.md"] = "# Rules\n\n" + "\n".join(rules_sections)

        return files

    def _format_rule(self, artifact: CanonicalArtifact) -> str:
        tags_str = ", ".join(artifact.tags) if artifact.tags else ""
        header = f"## {artifact.name}\n"
        header += f"> Priority: {artifact.priority} | Tags: {tags_str}\n\n"
        # Only the first paragraph — the core instruction without explanatory padding.
        body = artifact.body.strip().split("\n\n")[0]
        return header + body + "\n"

    def _format_skill(self, artifact: CanonicalArtifact) -> str:
        return self._frontmatter_block(
            {"name": artifact.name, "description": artifact.description}
        ) + artifact.body.strip() + "\n"

    def _format_agent(self, artifact: CanonicalArtifact) -> str:
        return self._frontmatter_block(
            {"name": artifact.name, "description": artifact.description}
        ) + artifact.body.strip() + "\n"

    def _format_command(self, artifact: CanonicalArtifact) -> str:
        return self._frontmatter_block(
            {"description": artifact.description}
        ) + artifact.body.strip() + "\n"

    def _frontmatter_block(self, fields: dict[str, str]) -> str:
        yaml_text = yaml.safe_dump(fields, sort_keys=False, default_flow_style=False).strip()
        return f"---\n{yaml_text}\n---\n"
