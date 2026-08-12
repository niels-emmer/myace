"""Goose adapter — translates Canonical IR into Goose's .goosehints format.

Verified against
https://goose-docs.ai/docs/guides/context-engineering/using-goosehints/:
`.goosehints` is a single plain-text/Markdown file at the project root
(Goose also supports a global `~/.config/goose/.goosehints` and
per-subdirectory files, merged root-to-leaf, but adapters only ever emit
repo-relative files — see `translate()`'s contract). There's no YAML
frontmatter or per-artifact-type file convention, so every artifact type
folds into one file as a plain heading + body, same general shape as
Aider's CONVENTIONS.md. Goose has no repo-committed model-config file
(models are configured via `~/.config/goose/config.yaml` on the host), so
`model_config` artifacts are skipped, matching the precedent set by the
Cline and Windsurf adapters for artifact types their target doesn't
support.
"""

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact

_KIND_LABELS = {"rule": "Rule", "skill": "Skill", "agent": "Agent", "workflow": "Workflow"}


class GooseAdapter(BaseAdapter):
    """Adapter for Goose — generates a .goosehints file."""

    def adapter_name(self) -> str:
        return "goose"

    def supported_targets(self) -> list[str]:
        return ["goose"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        sections: list[str] = []

        for artifact in artifacts:
            label = _KIND_LABELS.get(artifact.artifact_type)
            if label is None:
                continue
            sections.append(self._format_section(artifact, label))

        if not sections:
            return {}

        return {".goosehints": "# Hints\n\n" + "\n".join(sections)}

    def _format_section(self, artifact: CanonicalArtifact, label: str) -> str:
        header = f"## {artifact.name} ({label})\n\n"
        if artifact.description:
            header += f"{artifact.description}\n\n"
        return header + artifact.body.strip() + "\n"
