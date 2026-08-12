"""Sourcegraph Cody adapter — translates Canonical IR into Cody's rule format.

CAVEAT: as of this writing, Cody's live documentation
(sourcegraph.com/docs/cody and the public sourcegraph/docs GitHub repo)
lists chat, edit modes, auto-edit, the prompt library, MCP support, debug
assistance, and context filters as its documented capabilities — it does
NOT currently list a dedicated "rules"/`.rule.md` capability page, despite
`.sourcegraph/*.rule.md` being the format this adapter was commissioned to
target. This adapter still emits that path with a minimal, conservative
frontmatter (`description` only — the one field virtually every
rule-file-based tool in this codebase's adapters supports, and the safest
choice absent a confirmed schema), formatted the same way Cline/Windsurf
scope skills and agents into their single rules directory. Re-verify
against Cody's docs before relying on this in production; if the feature
has been renamed or removed, this adapter's output may need to move to
whatever replaced it (Cody's Prompt Library and MCP support are the
closest currently-documented equivalents for turning static instructions
into something Cody actually reads).
"""

import yaml

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact

_TYPE_PREFIXES = {"rule": "", "skill": "skill-", "agent": "agent-", "workflow": "workflow-"}


class CodyAdapter(BaseAdapter):
    """Adapter for Sourcegraph Cody — generates .sourcegraph/*.rule.md files."""

    def adapter_name(self) -> str:
        return "cody"

    def supported_targets(self) -> list[str]:
        return ["cody", "sourcegraph-cody"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        files: dict[str, str] = {}

        for artifact in artifacts:
            prefix = _TYPE_PREFIXES.get(artifact.artifact_type)
            if prefix is None:
                continue
            files[f".sourcegraph/{prefix}{artifact.name}.rule.md"] = self._format_rule(artifact)

        return files

    def _format_rule(self, artifact: CanonicalArtifact) -> str:
        description = artifact.description or artifact.name
        yaml_text = yaml.safe_dump({"description": description}, default_flow_style=False).strip()
        return f"---\n{yaml_text}\n---\n\n{artifact.body.strip()}\n"
