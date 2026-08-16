"""Tests for the local setup audit scoring/comparison logic (myace_cli.audit)."""

from pathlib import Path

import pytest

from myace_cli.audit import audit_directory, scan_target


def _write_agent(root: Path, adapter_dir: str, name: str) -> None:
    agents_dir = root / adapter_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / f"{name}.md").write_text(
        f"---\ndescription: {name} agent\n---\n\nDo {name} things.\n"
    )


@pytest.fixture
def two_target_paths() -> dict[str, list[str]]:
    """A small, deterministic two-target mapping for tests — avoids
    depending on the full 11-adapter ADAPTER_EXPECTED_PATHS so a future
    change to that mapping can't silently break these tests."""
    return {
        "target-a": [".target-a/agents/"],
        "target-b": [".target-b/agents/"],
    }


def test_divergent_artifact_sets_produce_expected_gaps(
    tmp_path: Path, two_target_paths: dict[str, list[str]]
) -> None:
    _write_agent(tmp_path, ".target-a", "shared-agent")
    _write_agent(tmp_path, ".target-a", "only-in-a")
    _write_agent(tmp_path, ".target-b", "shared-agent")

    result = audit_directory(tmp_path, adapter_paths=two_target_paths)

    assert result["targets"]["target-a"]["detected"] is True
    assert result["targets"]["target-b"]["detected"] is True
    assert result["targets"]["target-a"]["artifact_count"] == 2
    assert result["targets"]["target-b"]["artifact_count"] == 1

    gap_names = {(g["name"], tuple(g["missing_from"])) for g in result["gaps"]}
    assert ("only-in-a", ("target-b",)) in gap_names
    assert not any(g["name"] == "shared-agent" for g in result["gaps"])

    # Not full coverage — target-b is missing one artifact target-a has.
    assert result["score"] < 100


def test_identical_artifact_sets_produce_zero_gaps_and_full_score(
    tmp_path: Path, two_target_paths: dict[str, list[str]]
) -> None:
    _write_agent(tmp_path, ".target-a", "shared-agent")
    _write_agent(tmp_path, ".target-b", "shared-agent")

    result = audit_directory(tmp_path, adapter_paths=two_target_paths)

    assert result["gaps"] == []
    assert result["duplicates"] == []
    assert result["score"] == 100


def test_undetected_target_is_not_reported_as_a_gap_source(
    tmp_path: Path, two_target_paths: dict[str, list[str]]
) -> None:
    """A target whose expected paths don't exist at all shouldn't appear
    in gaps/duplicates — there's nothing to compare, it's simply absent."""
    _write_agent(tmp_path, ".target-a", "solo-agent")

    result = audit_directory(tmp_path, adapter_paths=two_target_paths)

    assert result["targets"]["target-b"]["detected"] is False
    assert result["targets"]["target-b"]["artifacts"] == []
    # target-b is undetected, so it must not show up as "missing" the
    # artifact target-a has — there's no setup to be missing anything from.
    assert result["gaps"] == []


def test_no_targets_detected_scores_zero(
    tmp_path: Path, two_target_paths: dict[str, list[str]]
) -> None:
    result = audit_directory(tmp_path, adapter_paths=two_target_paths)
    assert result["score"] == 0
    assert result["gaps"] == []
    assert result["duplicates"] == []


def test_scan_target_flags_within_target_duplicates(tmp_path: Path) -> None:
    """Two skill directories sharing a `name:` in frontmatter are a
    within-target duplicate, distinct from a cross-target gap."""
    skills_dir = tmp_path / "skills"
    for i in range(2):
        skill_dir = skills_dir / f"dir-{i}"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: duplicate-skill\ndescription: dup\n---\n\nBody.\n"
        )

    paths = {"target-a": ["skills/"]}
    result = audit_directory(tmp_path, adapter_paths=paths)

    assert len(result["duplicates"]) == 1
    dup = result["duplicates"][0]
    assert dup["target"] == "target-a"
    assert dup["name"] == "duplicate-skill"
    assert dup["count"] == 2
    # Duplicates cost points but shouldn't zero out the whole score.
    assert 0 < result["score"] < 100


def test_markdown_rules_file_splits_into_named_rule_artifacts(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text(
        "## First Rule\n\nDo the first thing.\n\n## Second Rule\n\nDo the second thing.\n"
    )
    paths = {"target-a": ["AGENTS.md"]}

    artifacts = scan_target(tmp_path, paths["target-a"])

    names = {a["name"] for a in artifacts}
    assert names == {"First Rule", "Second Rule"}
    assert all(a["artifact_type"] == "rule" for a in artifacts)


def test_flat_rules_directory_uses_filename_stem_as_name(tmp_path: Path) -> None:
    """Cursor-style '.cursor/rules/*.mdc' has no shared per-file parser —
    each file's stem becomes the rule's name."""
    rules_dir = tmp_path / ".cursor" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "security.mdc").write_text("---\ndescription: sec\n---\nBody\n")
    (rules_dir / "style.mdc").write_text("---\ndescription: style\n---\nBody\n")

    artifacts = scan_target(tmp_path, [".cursor/rules/"])

    names = {a["name"] for a in artifacts}
    assert names == {"security", "style"}
    assert all(a["artifact_type"] == "rule" for a in artifacts)


def test_nonmarkdown_config_file_recorded_as_existence_marker(tmp_path: Path) -> None:
    (tmp_path / "opencode.json").write_text("{}")
    artifacts = scan_target(tmp_path, ["opencode.json"])

    assert len(artifacts) == 1
    assert artifacts[0]["name"] == "opencode.json"
    assert artifacts[0]["artifact_type"] == "model_config"
