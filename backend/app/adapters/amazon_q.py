"""Amazon Q Developer adapter — translates Canonical IR into Q's project rules format.

Verified against
https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/context-project-rules.html:
project rules are plain Markdown files (no YAML frontmatter mentioned or
required) under `{project-root}/.amazonq/rules/`, one file per rule, each
holding a "detailed prompt" of coding standards. Q has no dedicated file
format for skills/agents/workflows, so those artifact types are rendered
into the same `.amazonq/rules/` directory with a type-prefixed filename —
the same fallback convention used by the Cline and Windsurf adapters for
target frameworks that only have one native artifact concept. `model_config`
artifacts are skipped: model selection isn't a repo-committed rules file
in Q Developer.
"""

from app.adapters.base import BaseAdapter
from app.models.artifact import CanonicalArtifact

_FILENAME_PREFIXES = {"rule": "", "skill": "skill-", "agent": "agent-", "workflow": "workflow-"}


class AmazonQAdapter(BaseAdapter):
    """Adapter for Amazon Q Developer — generates .amazonq/rules/*.md files."""

    def adapter_name(self) -> str:
        return "amazon-q"

    def supported_targets(self) -> list[str]:
        return ["amazon-q", "amazonq"]

    def expected_paths(self) -> list[str]:
        return [".amazonq/rules/"]

    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        files: dict[str, str] = {}

        for artifact in artifacts:
            prefix = _FILENAME_PREFIXES.get(artifact.artifact_type)
            if prefix is None:
                continue
            files[f".amazonq/rules/{prefix}{artifact.name}.md"] = self._format_rule(artifact)

        return files

    def _format_rule(self, artifact: CanonicalArtifact) -> str:
        parts = [f"# {artifact.name}\n"]
        if artifact.description:
            parts.append(f"{artifact.description}\n")
        parts.append(artifact.body.strip() + "\n")
        return "\n".join(parts)
