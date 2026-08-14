"""Cline adapter — translates Canonical IR into Cline rules format.

Verified against docs.cline.bot/customization/cline-rules (Aug 2026): Cline
does parse YAML frontmatter on .clinerules/*.md files, but the only
documented/recognized field is `paths` (an array of glob patterns for
conditional activation) — "rules without frontmatter are always active."
Canonical IR has no natural per-artifact glob/path-scoping concept to map
onto `paths`, so this adapter emits no frontmatter at all rather than
fields Cline doesn't recognize (title/type/priority/tags/globs were never
real fields; if frontmatter parsing fails on unrecognized content Cline
"fails open" and shows it as raw text, which is at best noise and at worst
confusing, not a functional risk — but there's no reason to emit it when
plain files work correctly and are the documented default-active behavior).
"""

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact

_KIND_LABELS = {"rule": "Rule", "skill": "Skill", "agent": "Agent", "workflow": "Workflow"}
_FILENAME_PREFIXES = {"rule": "", "skill": "skill-", "agent": "agent-", "workflow": "workflow-"}


class ClineAdapter(BaseAdapter):
    """Adapter for Cline — generates .clinerules/ files, no frontmatter."""

    def adapter_name(self) -> str:
        return "cline"

    def supported_targets(self) -> list[str]:
        return ["cline", "clinerules"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        files: dict[str, str] = {}

        for artifact in artifacts:
            prefix = _FILENAME_PREFIXES.get(artifact.artifact_type)
            label = _KIND_LABELS.get(artifact.artifact_type)
            if prefix is None or label is None:
                continue
            files[f".clinerules/{prefix}{artifact.name}.md"] = self._format_file(artifact, label)

        return files

    def _format_file(self, artifact: CanonicalArtifact, label: str) -> str:
        header = f"# {artifact.name} ({label})\n\n"
        if artifact.description:
            header += f"{artifact.description}\n\n"
        return header + artifact.body.strip() + "\n"
