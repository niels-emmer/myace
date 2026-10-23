"""Cross-check each adapter's `expected_paths()` against what `translate()` writes.

AGENTS.md rule 35 calls `expected_paths()` a hand-maintained contract and notes
that "no test cross-checks `expected_paths()` output against `translate()`
output". This is that test.

The two drifting apart fails *silently* in the worst possible way: the local
setup audit (`cli/myace_cli/audit.py`, driven by the mirror
`ADAPTER_EXPECTED_PATHS`) would look in a directory the adapter never writes to,
and report a perfectly configured machine as uncovered — with nothing in the
build or the adapter to indicate why.

Only the forward direction is asserted (every path `translate()` emits is
covered by `expected_paths()`). The reverse — every `expected_paths()` entry
actually being written for a given artifact set — legitimately does not hold:
an adapter with no `model_config` input, for example, writes no config file,
and that is correct rather than drift.
"""

import pytest

from app.adapters import list_adapters
from app.models.artifact import CanonicalArtifact


def _artifact(artifact_type: str, name: str, body: str) -> CanonicalArtifact:
    return CanonicalArtifact(
        artifact_type=artifact_type,
        name=name,
        version="1.0.0",
        target_compatibility=["python"],
        priority=50,
        tags=["mode:primary"],
        description="description",
        body=body,
        handoff_to=["some-agent"] if artifact_type == "agent" else None,
    )


def _one_of_every_type() -> list[CanonicalArtifact]:
    """One artifact per type, so each adapter exercises every branch it has."""
    return [
        _artifact("rule", "a-rule", "Rule body."),
        _artifact("skill", "a-skill", "Skill body."),
        _artifact("agent", "an-agent", "Agent body."),
        _artifact("workflow", "a-workflow", "Workflow body."),
        # Valid JSON: several adapters parse a model_config body as JSON and
        # fall back to a default shape when it doesn't parse, which would mask
        # the model/MCP output paths this test exists to cover.
        _artifact("model_config", "model:gpt-4", '{"model": "gpt-4", "provider": "openai"}'),
    ]


def _covered(path: str, expected: list[str]) -> bool:
    """Whether `path` is covered by an `expected_paths()` entry.

    Directory entries end in `/` and cover everything beneath them; file
    entries must match exactly.
    """
    for entry in expected:
        if entry.endswith("/"):
            if path.startswith(entry):
                return True
        elif path == entry:
            return True
    return False


@pytest.mark.parametrize("adapter", list_adapters(), ids=lambda a: a.adapter_name())
def test_translate_only_writes_paths_expected_paths_covers(adapter) -> None:
    written = sorted(adapter.translate(_one_of_every_type()))
    expected = adapter.expected_paths()

    uncovered = [p for p in written if not _covered(p, expected)]
    assert not uncovered, (
        f"{adapter.adapter_name()} writes {uncovered}, which its expected_paths() "
        f"({expected}) does not cover — the local setup audit would never look there. "
        f"Update expected_paths() and cli/myace_cli/audit.py's ADAPTER_EXPECTED_PATHS "
        f"together (AGENTS.md rule 35)."
    )


@pytest.mark.parametrize("adapter", list_adapters(), ids=lambda a: a.adapter_name())
def test_expected_paths_entries_are_well_formed(adapter) -> None:
    """Directory entries end with `/`, file entries don't, and nothing is
    absolute or traversing — the shape `audit.py` relies on when it decides
    whether to hand an entry to `scan_directory()` or read it as one file."""
    for entry in adapter.expected_paths():
        assert entry, f"{adapter.adapter_name()} has an empty expected_paths() entry"
        assert not entry.startswith("/"), f"{adapter.adapter_name()}: {entry!r} is absolute"
        assert ".." not in entry.split("/"), f"{adapter.adapter_name()}: {entry!r} traverses"
        if entry.endswith("/"):
            assert not entry.endswith("//"), f"{adapter.adapter_name()}: {entry!r}"
