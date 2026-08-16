"""OpenCode adapter — translates Canonical IR into OpenCode's real on-disk format.

Verified against https://opencode.ai/docs (agents, skills, commands, config,
rules): skills/agents/commands are Markdown with YAML frontmatter, not JSON
— only the model/MCP config file (opencode.json) is JSON, and it's a single
merged file, not one per model_config artifact.
"""

import json

import yaml

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact


class OpenCodeAdapter(BaseAdapter):
    """Adapter for OpenCode — generates Markdown skills/agents/commands,
    AGENTS.md, and opencode.json."""

    def adapter_name(self) -> str:
        return "opencode"

    def supported_targets(self) -> list[str]:
        return ["opencode", "open-code"]

    def expected_paths(self) -> list[str]:
        return [
            "AGENTS.md", "opencode.json",
            ".opencode/skills/", ".opencode/agents/", ".opencode/commands/",
        ]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        """
        Translate artifacts into OpenCode format.

        Skills become Markdown files (with YAML frontmatter) in
        .opencode/skills/<name>/SKILL.md. Agents become
        .opencode/agents/<name>.md, commands (workflows) become
        .opencode/commands/<name>.md. Rules become AGENTS.md sections.
        Model configs are merged into a single root opencode.json.
        """
        files: dict[str, str] = {}
        rules_content: list[str] = []
        provider_models: dict[str, dict[str, dict]] = {}
        mcp_servers: dict[str, dict] = {}

        for artifact in artifacts:
            if artifact.artifact_type == "skill":
                files[f".opencode/skills/{artifact.name}/SKILL.md"] = self._format_skill(artifact)
            elif artifact.artifact_type == "agent":
                files[f".opencode/agents/{artifact.name}.md"] = self._format_agent(artifact)
            elif artifact.artifact_type == "workflow":
                files[f".opencode/commands/{artifact.name}.md"] = self._format_command(artifact)
            elif artifact.artifact_type == "rule":
                rules_content.append(self._format_rule(artifact))
            elif artifact.artifact_type == "model_config":
                self._merge_model_config(artifact, provider_models, mcp_servers)

        if rules_content:
            files["AGENTS.md"] = "# OpenCode Rules\n\n" + "\n".join(rules_content)

        if provider_models or mcp_servers:
            files["opencode.json"] = self._build_opencode_json(provider_models, mcp_servers)

        return files

    def _format_skill(self, artifact: CanonicalArtifact) -> str:
        # Frontmatter fields OpenCode actually recognizes for skills: name,
        # description, license, compatibility, metadata (all optional except
        # name/description). version/priority/tags aren't part of that
        # schema, but `metadata` is explicitly free-form, so stash them
        # there — round-trips through the scanner without risking an
        # unrecognized-field issue on OpenCode's own parser.
        frontmatter: dict = {
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
        return self._frontmatter_block(frontmatter) + artifact.body.strip() + "\n"

    def _format_agent(self, artifact: CanonicalArtifact) -> str:
        # Canonical IR has no dedicated mode/model fields — the scanner
        # encodes them as "mode:<value>"/"model:<value>" tags on import, so
        # mirror that back out here to round-trip cleanly.
        mode = None
        model = None
        for tag in artifact.tags:
            if tag.startswith("mode:"):
                mode = tag.split(":", 1)[1]
            elif tag.startswith("model:"):
                model = tag.split(":", 1)[1]

        frontmatter: dict = {"description": artifact.description}
        if mode:
            frontmatter["mode"] = mode
        if model:
            frontmatter["model"] = model
        return self._frontmatter_block(frontmatter) + artifact.body.strip() + "\n"

    def _format_command(self, artifact: CanonicalArtifact) -> str:
        frontmatter = {"description": artifact.description}
        return self._frontmatter_block(frontmatter) + artifact.body.strip() + "\n"

    def _format_rule(self, artifact: CanonicalArtifact) -> str:
        tags_str = ", ".join(artifact.tags) if artifact.tags else ""
        header = f"## {artifact.name}\n"
        header += f"> Priority: {artifact.priority} | Tags: {tags_str}\n\n"
        # Only the first paragraph — the core instruction without explanatory padding.
        body = artifact.body.strip().split("\n\n")[0]
        return header + body + "\n"

    def _merge_model_config(
        self,
        artifact: CanonicalArtifact,
        provider_models: dict[str, dict[str, dict]],
        mcp_servers: dict[str, dict],
    ) -> None:
        """Reverses scanner._parse_opencode_json()'s shape: model_config
        artifacts named "model:<name>" (tagged "provider:<provider>") and
        "mcp:<name>" get merged back into one opencode.json."""
        try:
            body = json.loads(artifact.body) if artifact.body else {}
        except json.JSONDecodeError:
            body = {}

        if artifact.name.startswith("mcp:"):
            server_name = artifact.name.split(":", 1)[1]
            mcp_servers[server_name] = body
        elif artifact.name.startswith("model:"):
            model_name = artifact.name.split(":", 1)[1]
            provider_name = next(
                (t.split(":", 1)[1] for t in artifact.tags if t.startswith("provider:")),
                "unknown",
            )
            provider_models.setdefault(provider_name, {})[model_name] = body

    def _build_opencode_json(
        self,
        provider_models: dict[str, dict[str, dict]],
        mcp_servers: dict[str, dict],
    ) -> str:
        config: dict = {}
        if provider_models:
            config["provider"] = {
                name: {"models": models} for name, models in provider_models.items()
            }
        if mcp_servers:
            config["mcp"] = mcp_servers
        return json.dumps(config, indent=2)

    def _frontmatter_block(self, fields: dict) -> str:
        yaml_text = yaml.safe_dump(fields, sort_keys=False, default_flow_style=False).strip()
        return f"---\n{yaml_text}\n---\n"
