"""CLI-side Claude Code adapter — mirrors backend/app/adapters/claude_code.py.

Verified against code.claude.com/docs/en/sub-agents, /slash-commands, and
/model-config (Aug 2026): subagent files (.claude/agents/*.md) require YAML
frontmatter with at least name + description — identity comes from the
name field, not the filename. Commands were merged into skills, so this
adapter emits skills to .claude/skills/<name>/SKILL.md (loaded on demand)
and workflows to the still-supported legacy .claude/commands/<name>.md.
There is no repo-committed model-config file convention, so model_config
artifacts are skipped.
"""

import yaml

from myace_cli.adapters.base import BaseAdapter


class ClaudeCodeAdapter(BaseAdapter):
    """CLI-side adapter for Claude Code — generates CLAUDE.md,
    .claude/agents/, .claude/skills/, and .claude/commands/."""

    def adapter_name(self) -> str:
        return "claude-code"

    def supported_targets(self) -> list[str]:
        return ["claude-code", "claude"]

    def translate(self, artifacts: list[dict]) -> dict[str, str]:
        files: dict[str, str] = {}
        rules: list[str] = []

        for artifact in artifacts:
            atype = artifact.get("artifact_type", "rule")
            name = artifact.get("name", "unnamed")
            body = artifact.get("body", "")
            priority = artifact.get("priority", 50)
            tags = artifact.get("tags", [])
            desc = artifact.get("description", "")

            if atype == "rule":
                rules.append(
                    f"## {name}\n> Priority: {priority} | Tags: {', '.join(tags)}\n\n{body}\n"
                )
            elif atype == "skill":
                files[f".claude/skills/{name}/SKILL.md"] = _frontmatter_block(
                    {"name": name, "description": desc}
                ) + body.strip() + "\n"
            elif atype == "agent":
                files[f".claude/agents/{name}.md"] = _frontmatter_block(
                    {"name": name, "description": desc}
                ) + body.strip() + "\n"
            elif atype == "workflow":
                files[f".claude/commands/{name}.md"] = _frontmatter_block(
                    {"description": desc}
                ) + body.strip() + "\n"
            # model_config: no repo-committed file convention — skipped.

        if rules:
            files["CLAUDE.md"] = "# Rules\n\n" + "\n".join(rules)

        return files


def _frontmatter_block(fields: dict[str, str]) -> str:
    yaml_text = yaml.safe_dump(fields, sort_keys=False, default_flow_style=False).strip()
    return f"---\n{yaml_text}\n---\n"
