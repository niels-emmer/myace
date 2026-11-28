"""Convention guard for the hand-written add-on packs (collections/additional).

Add-ons are not generated (rule 42), so nothing else stops them drifting from
the conventions the base packs follow. See docs/plans/addon-pack-quality-audit.md.
"""

import re
from pathlib import Path

import pytest
import yaml

ADDONS = Path(__file__).resolve().parents[2] / "collections" / "additional"
PACKS = sorted(p for p in ADDONS.iterdir() if p.is_dir())
FALLBACK = "no subagents"


def _frontmatter(path: Path) -> dict[str, object]:
    match = re.match(r"---\n(.*?)\n---\n", path.read_text(), re.S)
    assert match, f"{path} has no frontmatter"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict)
    return data


def test_every_addon_frontmatter_parses() -> None:
    files = [
        *ADDONS.glob("*/agents/*.md"),
        *ADDONS.glob("*/skills/*/SKILL.md"),
        *ADDONS.glob("*/commands/*.md"),
    ]
    assert files
    for path in files:
        _frontmatter(path)


@pytest.mark.parametrize("pack", PACKS, ids=lambda p: p.name)
def test_every_rule_has_a_priority_tier(pack: Path) -> None:
    text = (pack / "AGENTS.md").read_text()
    headings = re.findall(r"^## .*$", text, re.M)
    markers = re.findall(r"<!-- myace: priority=(\d+) tags=\S+ -->", text)
    assert len(markers) == len(headings), f"{pack.name}: rule without a tier marker"
    assert {int(m) for m in markers} <= {50, 70, 90}


@pytest.mark.parametrize(
    "agent", sorted(ADDONS.glob("*/agents/*.md")), ids=lambda p: f"{p.parent.parent.name}/{p.stem}"
)
def test_agent_conventions(agent: Path) -> None:
    text = agent.read_text()
    fm = _frontmatter(agent)
    assert FALLBACK in text, "missing the no-subagent fallback sentence"
    if str(fm.get("description", "")).lower().startswith("read-only"):
        assert fm.get("permissions") == {"edit": "deny"}, "read-only agent must deny edit"


def test_addon_item_names_are_unique_across_every_pack() -> None:
    """Rule 29: compile de-duplicates by name alone, so an add-on item that
    reuses another pack's name silently vanishes from a composed setup."""
    from app.services.seed_collections import _scan_seeded_collection

    collections = ADDONS.parent
    seen: dict[str, str] = {}
    shared_base_names: set[str] = set()
    for kind in ("base", "additional"):
        for pack in sorted(p for p in (collections / kind).iterdir() if p.is_dir()):
            for artifact in _scan_seeded_collection(pack):
                name = artifact["name"]
                if kind == "base":
                    shared_base_names.add(name)  # base packs intentionally share names
                    continue
                assert name not in shared_base_names, f"{pack.name}: '{name}' collides with a base pack"
                assert name not in seen, f"{pack.name}: '{name}' also in {seen[name]}"
                seen[name] = pack.name
