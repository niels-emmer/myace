"""CLI-side OpenCode adapter — mirrors backend/app/adapters/opencode.py.

Verified against https://opencode.ai/docs: skills/agents/commands are
Markdown with YAML frontmatter, not JSON — only the model/MCP config file
(opencode.json) is JSON, and it's a single merged file.
"""

import json

import yaml

from myace_cli.adapters.base import BaseAdapter


class OpenCodeAdapter(BaseAdapter):
    """CLI-side adapter for OpenCode — generates Markdown skills/agents/
    commands, AGENTS.md, and opencode.json."""

    def adapter_name(self) -> str:
        return "opencode"

    def supported_targets(self) -> list[str]:
        return ["opencode", "open-code"]

    def translate(self, artifacts: list[dict]) -> dict[str, str]:
        files: dict[str, str] = {}
        rules: list[str] = []
        provider_models: dict[str, dict[str, dict]] = {}
        mcp_servers: dict[str, dict] = {}

        for artifact in artifacts:
            atype = artifact.get("artifact_type", "rule")
            name = artifact.get("name", "unnamed")
            body = artifact.get("body", "")
            desc = artifact.get("description", "")
            priority = artifact.get("priority", 50)
            tags = artifact.get("tags", [])
            version = artifact.get("version", "1.0.0")
            compatibility = artifact.get("target_compatibility", [])

            content = body.strip() + "\n"
            if atype == "skill":
                frontmatter: dict = {"name": name, "description": desc}
                if compatibility:
                    frontmatter["compatibility"] = compatibility
                frontmatter["metadata"] = {
                    "version": version, "priority": priority, "tags": tags,
                }
                path = f".opencode/skills/{name}/SKILL.md"
                files[path] = _frontmatter_block(frontmatter) + content
            elif atype == "agent":
                mode = next((t.split(":", 1)[1] for t in tags if t.startswith("mode:")), None)
                model = next((t.split(":", 1)[1] for t in tags if t.startswith("model:")), None)
                frontmatter = {"description": desc}
                if mode:
                    frontmatter["mode"] = mode
                if model:
                    frontmatter["model"] = model
                files[f".opencode/agents/{name}.md"] = _frontmatter_block(frontmatter) + content
            elif atype == "workflow":
                frontmatter = {"description": desc}
                files[f".opencode/commands/{name}.md"] = _frontmatter_block(frontmatter) + content
            elif atype == "rule":
                tags_str = ", ".join(tags)
                rules.append(f"## {name}\n> Priority: {priority} | Tags: {tags_str}\n\n{body}\n")
            elif atype == "model_config":
                _merge_model_config(name, tags, body, provider_models, mcp_servers)

        if rules:
            files["AGENTS.md"] = "# OpenCode Rules\n\n" + "\n".join(rules)

        if provider_models or mcp_servers:
            config: dict = {}
            if provider_models:
                config["provider"] = {n: {"models": m} for n, m in provider_models.items()}
            if mcp_servers:
                config["mcp"] = mcp_servers
            files["opencode.json"] = json.dumps(config, indent=2)

        return files


def _frontmatter_block(fields: dict) -> str:
    yaml_text = yaml.safe_dump(fields, sort_keys=False, default_flow_style=False).strip()
    return f"---\n{yaml_text}\n---\n"


def _merge_model_config(
    name: str,
    tags: list[str],
    body: str,
    provider_models: dict[str, dict[str, dict]],
    mcp_servers: dict[str, dict],
) -> None:
    try:
        parsed = json.loads(body) if body else {}
    except json.JSONDecodeError:
        parsed = {}

    if name.startswith("mcp:"):
        mcp_servers[name.split(":", 1)[1]] = parsed
    elif name.startswith("model:"):
        model_name = name.split(":", 1)[1]
        provider_name = next(
            (t.split(":", 1)[1] for t in tags if t.startswith("provider:")), "unknown",
        )
        provider_models.setdefault(provider_name, {})[model_name] = parsed
