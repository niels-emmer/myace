"""GitHub Copilot CLI adapter — translates Canonical IR into Copilot instructions format."""

import json

import yaml

from app.adapters.base import (
    BaseAdapter,
    restricting_permissions,
    safe_path_component,
    yaml_scalar,
)
from app.models.artifact import CanonicalArtifact

# Copilot custom-agent tool aliases (docs.github.com .../custom-agents-configuration).
_ALL_ALIASES = ["execute", "read", "edit", "search", "agent", "web", "todo"]
_DENIED_ALIASES: dict[str, list[str]] = {
    "read": ["read", "search"],
    "edit": ["edit"],
    "execute": ["execute"],
    "network": ["web"],
    "delegate": ["agent"],
}


class CopilotCliAdapter(BaseAdapter):
    """Adapter for GitHub Copilot CLI — generates copilot-instructions.md and .instructions.md."""

    def adapter_name(self) -> str:
        return "copilot-cli"

    def supported_targets(self) -> list[str]:
        return ["copilot-cli", "copilot", "github-copilot"]

    def expected_paths(self) -> list[str]:
        return [".github/copilot-instructions.md", ".github/instructions/", ".github/agents/"]

    def unenforced_permissions(self, artifact: CanonicalArtifact) -> dict[str, str]:
        # Only `deny` has a form (drop the alias from the agent's `tools` list);
        # `ask` is a session/approval concept in Copilot CLI.
        return {
            cap: eff
            for cap, eff in restricting_permissions(artifact).items()
            if eff != "deny"
        }

    def _format_native_agent(self, artifact: CanonicalArtifact) -> str:
        fields: dict[str, object] = {
            "name": artifact.name,
            "description": artifact.description,
        }
        denied = {
            cap for cap, eff in restricting_permissions(artifact).items() if eff == "deny"
        }
        if denied:
            # `tools` is an allow-list (omitted = everything), so express a deny
            # as "all aliases except these". Listing tools also drops MCP tools
            # for that agent — tighter than asked, never looser.
            removed = {c for cap in denied for c in _DENIED_ALIASES[cap]}
            fields["tools"] = [alias for alias in _ALL_ALIASES if alias not in removed]
        yaml_text = yaml.safe_dump(fields, sort_keys=False, default_flow_style=False).strip()
        return f"---\n{yaml_text}\n---\n" + artifact.body.strip() + "\n"

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        files: dict[str, str] = {}
        rules_entries: list[str] = []

        for artifact in artifacts:
            slug = safe_path_component(artifact.name)
            if artifact.artifact_type == "rule":
                rules_entries.append(self._format_copilot_rule(artifact))
            elif artifact.artifact_type == "skill":
                files[
                    f".github/instructions/{slug}.instructions.md"
                ] = self._format_instructions_file(artifact, "skill")
            elif artifact.artifact_type == "agent":
                files[
                    f".github/instructions/agent-{slug}.instructions.md"
                ] = self._format_instructions_file(artifact, "agent")
                # Additive: also a native custom agent, the only place a
                # per-agent `tools` restriction can live (ADR-0019).
                files[f".github/agents/{slug}.agent.md"] = self._format_native_agent(artifact)
            elif artifact.artifact_type == "workflow":
                files[
                    f".github/instructions/workflow-{slug}.instructions.md"
                ] = self._format_instructions_file(artifact, "workflow")
            elif artifact.artifact_type == "model_config":
                files[
                    f".github/instructions/model-{slug}.instructions.md"
                ] = self._format_instructions_file(artifact, "model_config")

        if rules_entries:
            files[".github/copilot-instructions.md"] = (
                "# Copilot Instructions\n\n" + "\n".join(rules_entries)
            )

        return files

    def _format_copilot_rule(self, artifact: CanonicalArtifact) -> str:
        return (
            f"## {artifact.name}\n\n"
            f"{artifact.description}\n\n"
            f"{artifact.body.strip()}\n"
        )

    def _format_instructions_file(self, artifact: CanonicalArtifact, artifact_type: str) -> str:
        globs = self._targets_to_globs(artifact.target_compatibility)
        return (
            f"---\n"
            f"title: {yaml_scalar(artifact.name)}\n"
            f"description: {yaml_scalar(artifact.description)}\n"
            f"applyTo: {json.dumps(globs)}\n"
            f"type: {artifact_type}\n"
            f"priority: {artifact.priority}\n"
            f"---\n"
            f"{artifact.body.strip()}\n"
        )

    def _targets_to_globs(self, targets: list[str]) -> list[str]:
        if not targets:
            return ["**/*.py", "**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"]
        return [f"**/*.{t}" for t in targets if not t.startswith("*")] or ["**/*"]
