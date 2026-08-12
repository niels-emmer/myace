"""Continue adapter — translates Canonical IR into Continue's real on-disk format.

Verified against https://docs.continue.dev/customize/rules and
https://docs.continue.dev/reference: `config.json` is deprecated in favor
of `config.yaml` (a "Migrating Config to YAML" guide covers the move), so
this adapter targets `config.yaml` rather than the legacy JSON format.
Rules are Markdown files with YAML frontmatter (`name`, `globs`,
`description`, `alwaysApply`) under `.continue/rules/`. Continue's legacy
custom-slash-command format — a `.prompt` file with a small frontmatter
block plus a template body — is still how this adapter renders `workflow`
artifacts, since `config.yaml`'s `prompts:` list has no equivalent
per-file granularity. `models` and `mcpServers` are merged into a single
root `config.yaml`, mirroring how `model_config` artifacts already get
merged for the OpenCode adapter (`model:<name>` tagged `provider:<provider>`,
and `mcp:<name>`, per the scanner's encoding).
"""

import json

import yaml

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact


class ContinueAdapter(BaseAdapter):
    """Adapter for Continue — generates .continue/rules/*.md, .continue/prompts/*.prompt,
    and config.yaml."""

    def adapter_name(self) -> str:
        return "continue"

    def supported_targets(self) -> list[str]:
        return ["continue", "continue-dev"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        files: dict[str, str] = {}
        provider_models: list[dict[str, object]] = []
        mcp_servers: list[dict[str, object]] = []

        for artifact in artifacts:
            if artifact.artifact_type == "rule":
                files[f".continue/rules/{artifact.name}.md"] = self._format_rule(artifact)
            elif artifact.artifact_type == "skill":
                files[f".continue/rules/skill-{artifact.name}.md"] = self._format_rule(artifact)
            elif artifact.artifact_type == "agent":
                files[f".continue/rules/agent-{artifact.name}.md"] = self._format_rule(artifact)
            elif artifact.artifact_type == "workflow":
                files[f".continue/prompts/{artifact.name}.prompt"] = self._format_prompt(artifact)
            elif artifact.artifact_type == "model_config":
                self._collect_model_config(artifact, provider_models, mcp_servers)

        if provider_models or mcp_servers:
            files["config.yaml"] = self._build_config_yaml(provider_models, mcp_servers)

        return files

    def _format_rule(self, artifact: CanonicalArtifact) -> str:
        frontmatter: dict[str, object] = {"name": artifact.name}
        globs = [t for t in artifact.target_compatibility if not t.startswith("*")]
        if globs:
            frontmatter["globs"] = [f"**/*.{g}" for g in globs]
        if artifact.description:
            frontmatter["description"] = artifact.description
        frontmatter["alwaysApply"] = artifact.priority >= 80
        yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, default_flow_style=False).strip()
        return f"---\n{yaml_text}\n---\n\n{artifact.body.strip()}\n"

    def _format_prompt(self, artifact: CanonicalArtifact) -> str:
        frontmatter = {"name": artifact.name, "description": artifact.description}
        yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, default_flow_style=False).strip()
        return f"---\n{yaml_text}\n---\n{artifact.body.strip()}\n"

    def _collect_model_config(
        self,
        artifact: CanonicalArtifact,
        provider_models: list[dict[str, object]],
        mcp_servers: list[dict[str, object]],
    ) -> None:
        """Reverses the scanner's model_config encoding (model:<name> tagged
        provider:<provider>, mcp:<name>) into Continue's config.yaml shape."""
        try:
            body: dict[str, object] = json.loads(artifact.body) if artifact.body else {}
        except json.JSONDecodeError:
            body = {}

        if artifact.name.startswith("mcp:"):
            server_name = artifact.name.split(":", 1)[1]
            entry: dict[str, object] = {"name": server_name}
            entry.update(body)
            mcp_servers.append(entry)
        elif artifact.name.startswith("model:"):
            model_name = artifact.name.split(":", 1)[1]
            provider_name = next(
                (t.split(":", 1)[1] for t in artifact.tags if t.startswith("provider:")),
                "openai",
            )
            entry = {"name": model_name, "provider": provider_name, "model": model_name}
            entry.update(body)
            provider_models.append(entry)

    def _build_config_yaml(
        self, provider_models: list[dict[str, object]], mcp_servers: list[dict[str, object]]
    ) -> str:
        config: dict[str, object] = {
            "name": "MyACE Profile", "version": "1.0.0", "schema": "v1",
        }
        if provider_models:
            config["models"] = provider_models
        if mcp_servers:
            config["mcpServers"] = mcp_servers
        return str(yaml.safe_dump(config, sort_keys=False, default_flow_style=False))
