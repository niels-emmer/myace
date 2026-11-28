"""The shared governance core stays in sync with, and reaches, every base pack."""

import json
import subprocess
import sys
from pathlib import Path

from app.services.seed_collections import _scan_seeded_collection

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "collections" / "base"
CONFIG = json.loads((REPO / "collections" / "_shared" / "packs.json").read_text())


def test_generated_agents_md_is_in_sync() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "sync_shared_core.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_base_pack_ships_the_core_rules_self_contained() -> None:
    wanted = {r["name"] for r in CONFIG["rules"]}
    for slug in CONFIG["title"]:
        rules = {
            a["name"]: a["body"]
            for a in _scan_seeded_collection(BASE / slug)
            if a["artifact_type"] == "rule"
        }
        assert wanted <= rules.keys(), f"{slug} is missing {wanted - rules.keys()}"
        assert all(rules[n].strip() for n in wanted)
        assert not any("GENERATED" in body for body in rules.values())


def test_core_rule_names_are_unique_within_each_pack() -> None:
    for slug in CONFIG["title"]:
        names = [
            a["name"] for a in _scan_seeded_collection(BASE / slug) if a["artifact_type"] == "rule"
        ]
        assert len(names) == len(set(names)), slug


def test_shared_source_is_not_a_seeded_collection() -> None:
    from app.services.seed_collections import COMMUNITY_CONTRIBUTED_COLLECTIONS, STARTER_COLLECTIONS

    seeded = {s for group in (STARTER_COLLECTIONS, COMMUNITY_CONTRIBUTED_COLLECTIONS) for t in group.values() for s in t}
    assert "_shared" not in seeded
