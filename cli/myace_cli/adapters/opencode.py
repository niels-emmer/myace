"""CLI-side OpenCode adapter."""

import json
from myace_cli.adapters.base import BaseAdapter


class OpenCodeAdapter(BaseAdapter):
    """CLI-side adapter for OpenCode — generates JSON modules."""

    def adapter_name(self) -> str:
        return "opencode"

    def supported_targets(self) -> list[str]:
        return ["opencode", "open-code"]

    def translate(self, artifacts: list[dict]) -> dict[str, str]:
        files: dict[str, str] = {}
        rules: list[str] = []

        for artifact in artifacts:
            atype = artifact.get("artifact_type", "rule")
            name = artifact.get("name", "unnamed")
            body = artifact.get("body", "")
            desc = artifact.get("description", "")
            priority = artifact.get("priority", 50)
            tags = artifact.get("tags", [])
            version = artifact.get("version", "1.0.0")

            if atype == "skill":
                files[f".opencode/skills/{name}.json"] = json.dumps({
                    "name": name, "version": version, "description": desc,
                    "priority": priority, "tags": tags, "body": body,
                }, indent=2)
            elif atype == "agent":
                files[f".opencode/agents/{name}.json"] = json.dumps({
                    "name": name, "version": version, "description": desc,
                    "type": "agent", "instructions": body, "tags": tags,
                }, indent=2)
            elif atype == "rule":
                rules.append(f"## {name}\n> Priority: {priority} | Tags: {', '.join(tags)}\n\n{body}\n")

        if rules:
            files["AGENTS.md"] = "# OpenCode Rules\n\n" + "\n".join(rules)

        return files
