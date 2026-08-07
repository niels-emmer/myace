"""OpenCode adapter — translates Canonical IR into OpenCode JSON modules."""

import json
from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact


class OpenCodeAdapter(BaseAdapter):
    """Adapter for OpenCode — generates JSON skill/agent modules and config files."""

    def adapter_name(self) -> str:
        return "opencode"

    def supported_targets(self) -> list[str]:
        return ["opencode", "open-code"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        """
        Translate artifacts into OpenCode format.

        Skills become JSON files in .opencode/skills/.
        Agents become JSON files in .opencode/agents/.
        Rules become entries in opencode.json or AGENTS.md.
        """
        files: dict[str, str] = {}
        skills: list[dict] = []
        agents: list[dict] = []
        rules_content: list[str] = []

        for artifact in artifacts:
            if artifact.artifact_type == "skill":
                skills.append(self._to_opencode_skill(artifact))
            elif artifact.artifact_type == "agent":
                agents.append(self._to_opencode_agent(artifact))
            elif artifact.artifact_type == "rule":
                rules_content.append(self._format_rule(artifact))
            elif artifact.artifact_type == "workflow":
                files[f".opencode/workflows/{artifact.name}.json"] = json.dumps(
                    self._to_opencode_workflow(artifact), indent=2
                )
            elif artifact.artifact_type == "model_config":
                files[f".opencode/models/{artifact.name}.json"] = json.dumps(
                    self._to_opencode_model_config(artifact), indent=2
                )

        # Write skills
        for skill in skills:
            files[f".opencode/skills/{skill['name']}.json"] = json.dumps(skill, indent=2)

        # Write agents
        for agent in agents:
            files[f".opencode/agents/{agent['name']}.json"] = json.dumps(agent, indent=2)

        # Write AGENTS.md if rules exist
        if rules_content:
            files["AGENTS.md"] = "# OpenCode Rules\n\n" + "\n".join(rules_content)

        return files

    def _to_opencode_skill(self, artifact: CanonicalArtifact) -> dict:
        return {
            "name": artifact.name,
            "version": artifact.version,
            "description": artifact.description,
            "priority": artifact.priority,
            "tags": artifact.tags,
            "target_compatibility": artifact.target_compatibility,
            "body": artifact.body,
        }

    def _to_opencode_agent(self, artifact: CanonicalArtifact) -> dict:
        return {
            "name": artifact.name,
            "version": artifact.version,
            "description": artifact.description,
            "type": "agent",
            "instructions": artifact.body,
            "tags": artifact.tags,
        }

    def _to_opencode_workflow(self, artifact: CanonicalArtifact) -> dict:
        return {
            "name": artifact.name,
            "version": artifact.version,
            "description": artifact.description,
            "steps": artifact.body,
            "tags": artifact.tags,
        }

    def _to_opencode_model_config(self, artifact: CanonicalArtifact) -> dict:
        return {
            "name": artifact.name,
            "version": artifact.version,
            "description": artifact.description,
            "config": artifact.body,
            "tags": artifact.tags,
        }

    def _format_rule(self, artifact: CanonicalArtifact) -> str:
        tags_str = ", ".join(artifact.tags) if artifact.tags else ""
        header = f"## {artifact.name}\n"
        header += f"> Priority: {artifact.priority} | Tags: {tags_str}\n\n"
        return header + artifact.body.strip() + "\n"
