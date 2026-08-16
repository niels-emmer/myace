"""Goose adapter — translates Canonical IR into Goose's context-file format.

Verified against goose-docs.ai (Aug 2026, the domain the docs migrated to —
block.github.io/goose now redirects there): Goose's real context-file
search order is `["AGENTS.md", ".goosehints"]`, checked at each directory
level — `AGENTS.md` is checked first and is effectively the primary
mechanism now, not `.goosehints`. This adapter targets `AGENTS.md` alone
rather than both, since it's unconfirmed whether Goose merges content from
both files or treats the first found as authoritative — duplicating
identical content into both would risk double-loading the same instructions
if it merges. There's no YAML frontmatter or per-artifact-type file
convention, so every artifact type folds into one file as a plain heading +
body, same general shape as Aider's CONVENTIONS.md. Goose has no
repo-committed model-config file (models are configured via
`~/.config/goose/config.yaml` on the host), so `model_config` artifacts are
skipped, matching the precedent set by the Cline and Windsurf adapters for
artifact types their target doesn't support. (Goose has since added a
Recipes system — YAML files bundling instructions/prompt/extensions/
sub-agents — that could map to this project's `agent`/`workflow` artifact
types instead of folding everything into one file; not yet implemented
here, worth a follow-up enhancement.)
"""

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact

_KIND_LABELS = {"rule": "Rule", "skill": "Skill", "agent": "Agent", "workflow": "Workflow"}


class GooseAdapter(BaseAdapter):
    """Adapter for Goose — generates an AGENTS.md context file."""

    def adapter_name(self) -> str:
        return "goose"

    def supported_targets(self) -> list[str]:
        return ["goose"]

    def expected_paths(self) -> list[str]:
        return ["AGENTS.md"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        sections: list[str] = []

        for artifact in artifacts:
            label = _KIND_LABELS.get(artifact.artifact_type)
            if label is None:
                continue
            sections.append(self._format_section(artifact, label))

        if not sections:
            return {}

        return {"AGENTS.md": "# Hints\n\n" + "\n".join(sections)}

    def _format_section(self, artifact: CanonicalArtifact, label: str) -> str:
        header = f"## {artifact.name} ({label})\n\n"
        if artifact.description:
            header += f"{artifact.description}\n\n"
        return header + artifact.body.strip() + "\n"
