"""CLI-side Cursor adapter — mirrors backend/app/adapters/cursor.py.

Verified against cursor.com/docs/rules (Aug 2026): Cursor's real, current
rule mechanism is exclusively .cursor/rules/*.mdc files with YAML
frontmatter (description, globs, alwaysApply). The legacy root .cursorrules
file no longer appears anywhere in current docs. Cursor has no documented
"workflow" or "model config" file concept, so those artifact types fold
into the same .cursor/rules/*.mdc format, using Agent Requested mode
(alwaysApply: false with a description).
"""

import yaml

from myace_cli.adapters.base import BaseAdapter


class CursorAdapter(BaseAdapter):
    """CLI-side adapter for Cursor — generates .cursor/rules/*.mdc files."""

    def adapter_name(self) -> str:
        return "cursor"

    def supported_targets(self) -> list[str]:
        return ["cursor", "cursor-editor"]

    def translate(self, artifacts: list[dict]) -> dict[str, str]:
        files: dict[str, str] = {}

        for artifact in artifacts:
            atype = artifact.get("artifact_type", "rule")
            if atype not in ("rule", "skill", "agent", "workflow"):
                continue
            name = artifact.get("name", "unnamed")
            body = artifact.get("body", "")
            desc = artifact.get("description", "")

            frontmatter: dict[str, object] = {
                "description": desc,
                "alwaysApply": atype == "rule",
            }
            yaml_text = yaml.safe_dump(
                frontmatter, sort_keys=False, default_flow_style=False
            ).strip()
            files[f".cursor/rules/{name}.mdc"] = f"---\n{yaml_text}\n---\n{body.strip()}\n"

        return files
