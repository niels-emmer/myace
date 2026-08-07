"""CLI-side Claude Code adapter."""

from myace_cli.adapters.base import BaseAdapter


class ClaudeCodeAdapter(BaseAdapter):
    """CLI-side adapter for Claude Code — generates CLAUDE.md."""

    def adapter_name(self) -> str:
        return "claude-code"

    def supported_targets(self) -> list[str]:
        return ["claude-code", "claude"]

    def translate(self, artifacts: list[dict]) -> dict[str, str]:
        files: dict[str, str] = {}
        rules: list[str] = []
        skills: list[str] = []

        for artifact in artifacts:
            atype = artifact.get("artifact_type", "rule")
            name = artifact.get("name", "unnamed")
            body = artifact.get("body", "")
            priority = artifact.get("priority", 50)
            tags = artifact.get("tags", [])
            desc = artifact.get("description", "")

            if atype == "rule":
                rules.append(f"## {name}\n> Priority: {priority} | Tags: {', '.join(tags)}\n\n{body}\n")
            elif atype == "skill":
                skills.append(f"## {name}\n\n{desc}\n\n{body}\n")
            elif atype == "agent":
                files[f".claude/agents/{name}.md"] = f"# {name}\n\n{desc}\n\n{body}\n"
            elif atype == "workflow":
                files[f".claude/workflows/{name}.md"] = f"# {name}\n\n{desc}\n\n{body}\n"

        claude_md = "# Rules\n" + "\n".join(rules) if rules else ""
        if skills:
            claude_md += "\n# Skills\n" + "\n".join(skills)
        if claude_md:
            files["CLAUDE.md"] = claude_md

        return files
