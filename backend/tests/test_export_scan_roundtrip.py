"""Export → scan round trip: `artifacts_to_files()` must scan back to itself.

AGENTS.md rule 8: "Keep `artifacts_to_files()` (export) and the scanner's
parsers (import) symmetric — a collection exported to GitHub should scan back to
the same artifacts."

Regression this pins: `_frontmatter()` emitted `target_compatibility`, while
both scanners read `compatibility` (each defaulting to `["opencode"]`), so every
re-scan silently dropped the field. Agent `tags` were dropped too, because
`_parse_agent_file` rebuilt tags from `mode`/`model` alone.

Known residual limitations, asserted explicitly below rather than left as a
surprise:
  - `rule` artifacts become `##` sections in a merged `AGENTS.md`, which carries
    no frontmatter at all — so version/priority/tags cannot survive.
  - An agent/workflow name that isn't already slug-safe (`"My Agent"`) does not
    round-trip, because the export slugifies it into the filename and the
    scanner derives the name from the filename stem.
Both are properties of the on-disk format, not of this change.
"""

import pytest

from app.models.artifact import CanonicalArtifact
from app.services import scanner
from app.services.github_export import artifacts_to_files


def _artifacts() -> list[CanonicalArtifact]:
    return [
        CanonicalArtifact(
            artifact_type="skill", name="my-skill", version="2.1.0",
            target_compatibility=["claude-code", "cursor"], priority=70,
            tags=["alpha", "beta"], description="A skill.", body="Skill body.",
        ),
        CanonicalArtifact(
            artifact_type="agent", name="my-agent", version="1.2.3",
            target_compatibility=["cursor", "codex-cli"], priority=40,
            tags=["mode:primary"], description="An agent.", body="Agent body.",
            handoff_to=["my-skill"],
        ),
        CanonicalArtifact(
            artifact_type="workflow", name="my-flow", version="1.0.0",
            target_compatibility=["opencode"], priority=50,
            tags=["gamma"], description="A workflow.", body="Workflow body.",
        ),
    ]


def _scan_back(tmp_path):
    files = artifacts_to_files(_artifacts())
    root = tmp_path.resolve()
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return {a["name"]: a for a in scanner._scan_tree(root, confine_to=root)}


@pytest.mark.parametrize(
    "name", ["my-skill", "my-agent", "my-flow"]
)
def test_file_backed_artifacts_survive_the_round_trip(tmp_path, name: str) -> None:
    scanned = _scan_back(tmp_path)
    original = next(a for a in _artifacts() if a.name == name)
    back = scanned.get(name)
    assert back is not None, f"{name} did not survive the round trip"

    assert back["artifact_type"] == original.artifact_type
    assert back["version"] == original.version
    assert back["priority"] == original.priority
    assert back["target_compatibility"] == original.target_compatibility, (
        "target_compatibility was dropped — the exporter and the scanner must "
        "agree on the frontmatter key (`compatibility`)."
    )
    assert back["tags"] == original.tags
    assert back["description"] == original.description
    assert back["body"].strip() == original.body.strip()


def test_agent_handoff_survives_the_round_trip(tmp_path) -> None:
    scanned = _scan_back(tmp_path)
    assert scanned["my-agent"]["handoff_to"] == ["my-skill"]


def test_rule_artifacts_round_trip_name_and_body_only(tmp_path) -> None:
    """A rule becomes a `##` section in AGENTS.md with no frontmatter, so only
    its name and body can survive — pinned so the limitation is explicit."""
    rules = [CanonicalArtifact(
        artifact_type="rule", name="a-rule", version="3.0.0",
        target_compatibility=["claude-code"], priority=90, tags=["t"],
        description="A rule.", body="Rule body.",
    )]
    root = tmp_path.resolve()
    for rel, content in artifacts_to_files(rules).items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    scanned = {a["name"]: a for a in scanner._scan_tree(root, confine_to=root)}
    back = scanned["a-rule"]
    assert back["body"].strip() == "Rule body."
    # Not round-trippable through the `##`-section format:
    assert back["version"] == "1.0.0"
    assert back["tags"] == []
