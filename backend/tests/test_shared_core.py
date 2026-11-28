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
    for slug in CONFIG["title"]:
        wanted = {r["name"] for r in CONFIG["rules"] if slug in r.get("packs", [slug])}
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


def test_shared_skills_and_scoped_rules_reach_exactly_their_packs() -> None:
    for skill in CONFIG["skills"]:
        for slug in CONFIG["title"]:
            exists = (BASE / slug / "skills" / skill["slug"] / "SKILL.md").exists()
            assert exists == (slug in skill.get("packs", [slug])), (slug, skill["slug"])
    scoped = [r for r in CONFIG["rules"] if "packs" in r]
    assert scoped, "expected at least one pack-scoped shared rule"
    for rule in scoped:
        for slug in CONFIG["title"]:
            names = {a["name"] for a in _scan_seeded_collection(BASE / slug)}
            assert (rule["name"] in names) == (slug in rule["packs"]), (slug, rule["name"])


def test_every_base_rule_has_a_deliberate_tier() -> None:
    """Priority sorts compiled output, so no base rule may silently sit at the
    default with no tags: each carries a tier (90 safety/security, 70 quality
    gates) or at least a tag saying what it is."""
    for slug in CONFIG["title"]:
        for a in _scan_seeded_collection(BASE / slug):
            if a["artifact_type"] == "rule":
                assert a["priority"] != 50 or a["tags"], (slug, a["name"])


def test_safety_rules_outrank_process_rules_in_every_pack() -> None:
    for slug in CONFIG["title"]:
        rules = {a["name"]: a["priority"] for a in _scan_seeded_collection(BASE / slug)
                 if a["artifact_type"] == "rule"}
        assert rules["Secrets And Destructive Actions"] == 90, slug
        assert rules["Rule Of Least Power"] <= rules["Change Control"], slug
