"""Cursor adapter — translates Canonical IR into Cursor rules format.

Verified against cursor.com/docs/rules (Aug 2026): Cursor's real, current
rule mechanism is exclusively .cursor/rules/*.mdc files with YAML
frontmatter (description, globs, alwaysApply) — these fields determine
whether/when a rule loads: alwaysApply=true is always-on, a description
with alwaysApply=false is "Agent Requested" (the agent decides whether to
pull it in based on the description), globs is "Auto Attached" (loads when
a matching file is open). The legacy root .cursorrules file no longer
appears anywhere in current docs. Cursor has no documented "workflow" or
"model config" file concept, so those artifact types fold into the same
.cursor/rules/*.mdc format as skills/agents, using Agent Requested mode —
the same fallback convention used by the Cline and Windsurf adapters for
target frameworks that only have one native artifact concept.
"""

import yaml

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact


class CursorAdapter(BaseAdapter):
    """Adapter for Cursor — generates .cursor/rules/*.mdc files."""

    def adapter_name(self) -> str:
        return "cursor"

    def supported_targets(self) -> list[str]:
        return ["cursor", "cursor-editor"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        """
        Translate artifacts into Cursor format.

        Everything becomes a .cursor/rules/<name>.mdc file. Rule-type
        artifacts get alwaysApply: true (always-on baseline instructions).
        Skill/agent/workflow-type artifacts get alwaysApply: false with a
        description, so Cursor's agent decides when to pull them in
        ("Agent Requested" mode). model_config has no repo-committed file
        convention in Cursor and is skipped.
        """
        files: dict[str, str] = {}

        for artifact in artifacts:
            if artifact.artifact_type in ("rule", "skill", "agent", "workflow"):
                files[f".cursor/rules/{artifact.name}.mdc"] = self._format_mdc(artifact)

        return files

    def _format_mdc(self, artifact: CanonicalArtifact) -> str:
        frontmatter: dict[str, object] = {
            "description": artifact.description,
            "alwaysApply": artifact.artifact_type == "rule",
        }
        yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, default_flow_style=False).strip()
        return f"---\n{yaml_text}\n---\n{artifact.body.strip()}\n"
