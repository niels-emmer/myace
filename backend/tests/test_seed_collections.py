"""Tests for install-time starter/community pack seeding (app/services/seed_collections.py)."""

from pathlib import Path

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.models.artifact import Artifact
from app.models.collection import Collection
from app.models.user import User
from app.services.seed_collections import (
    COMMUNITY_CONTRIBUTED_COLLECTIONS,
    STARTER_COLLECTIONS,
    SYSTEM_USER_EMAIL,
    get_or_create_system_user,
    seed_starter_collections,
)

# backend/tests/test_seed_collections.py -> repo root is two parents up.
REPO_COLLECTIONS_ROOT = Path(__file__).resolve().parents[2] / "collections"

EXPECTED_COLLECTION_COUNT = sum(len(c) for c in STARTER_COLLECTIONS.values())
EXPECTED_COMMUNITY_COUNT = sum(len(c) for c in COMMUNITY_CONTRIBUTED_COLLECTIONS.values())


async def _seed_against_repo_collections(db_session: AsyncSession, monkeypatch) -> None:
    monkeypatch.setattr(settings, "collections_root", str(REPO_COLLECTIONS_ROOT))
    await seed_starter_collections(db_session)


def test_seed_registries_do_not_overlap() -> None:
    """A slug listed in both maps would make its classification depend on
    iteration order; keep the starter and community registries disjoint."""
    starter_refs = {
        (collection_type, slug)
        for collection_type, collections in STARTER_COLLECTIONS.items()
        for slug in collections
    }
    community_refs = {
        (collection_type, slug)
        for collection_type, collections in COMMUNITY_CONTRIBUTED_COLLECTIONS.items()
        for slug in collections
    }
    assert starter_refs.isdisjoint(community_refs)


async def test_seed_creates_expected_collections(db_session: AsyncSession, monkeypatch) -> None:
    await _seed_against_repo_collections(db_session, monkeypatch)

    result = await db_session.execute(
        select(Collection).where(Collection.is_starter_pack.is_(True))
    )
    seeded = result.scalars().all()
    assert len(seeded) == EXPECTED_COLLECTION_COUNT

    by_name = {c.name: c for c in seeded}
    for collection_type, collections in STARTER_COLLECTIONS.items():
        for _slug, meta in collections.items():
            collection = by_name[meta["name"]]
            assert collection.collection_type == collection_type
            assert collection.visibility == "public"
            assert collection.published is True
            assert collection.category == meta["category"]
            assert collection.artifact_count > 0

            artifacts = (
                await db_session.execute(
                    select(Artifact).where(Artifact.collection_id == collection.id)
                )
            ).scalars().all()
            assert len(artifacts) == collection.artifact_count


async def test_seed_creates_community_contributed_collections(
    db_session: AsyncSession, monkeypatch
) -> None:
    await _seed_against_repo_collections(db_session, monkeypatch)

    result = await db_session.execute(
        select(Collection).where(Collection.is_starter_pack.is_(False))
    )
    seeded = result.scalars().all()
    assert len(seeded) == EXPECTED_COMMUNITY_COUNT

    by_name = {c.name: c for c in seeded}
    for collection_type, collections in COMMUNITY_CONTRIBUTED_COLLECTIONS.items():
        for slug, meta in collections.items():
            collection = by_name[meta["name"]]
            assert collection.collection_type == collection_type
            assert collection.git_url == f"seed://{collection_type}/{slug}"
            assert collection.visibility == "public"
            assert collection.published is True
            assert collection.moderation_status == "approved"
            assert collection.category == meta["category"]
            assert collection.artifact_count > 0


async def test_seeded_community_packs_are_listed_publicly(
    async_client: AsyncClient, db_session: AsyncSession, monkeypatch
) -> None:
    """The community shelf starts non-empty: the seeded community-contributed
    add-ons are published + approved, so an anonymous visitor sees them at
    /community and Home's highlights filter can surface them."""
    await _seed_against_repo_collections(db_session, monkeypatch)

    res = await async_client.get("/api/v1/collections/community?limit=100")
    assert res.status_code == 200

    items = res.json()["items"]
    community_names = {item["name"] for item in items if not item["is_starter_pack"]}
    expected = {
        meta["name"]
        for collections in COMMUNITY_CONTRIBUTED_COLLECTIONS.values()
        for meta in collections.values()
    }
    assert community_names == expected

    # Starter packs still fill the same endpoint; the client filters them out
    # of the community highlights (Home.tsx).
    assert any(item["is_starter_pack"] for item in items)


async def test_seed_reclassifies_a_slug_moved_to_community(
    db_session: AsyncSession, monkeypatch
) -> None:
    """A slug that moved from the starter map to the community map must flip
    its existing row's flag in place, not insert a duplicate."""
    await _seed_against_repo_collections(db_session, monkeypatch)

    seed_ref = "seed://additional/eu-ai-act"
    collection = (
        await db_session.execute(select(Collection).where(Collection.git_url == seed_ref))
    ).scalars().one()
    assert collection.is_starter_pack is False

    # Simulate the pre-change state: this community slug used to seed as a
    # starter pack.
    collection.is_starter_pack = True
    db_session.add(collection)
    await db_session.commit()

    await _seed_against_repo_collections(db_session, monkeypatch)

    rows = (
        await db_session.execute(select(Collection).where(Collection.git_url == seed_ref))
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].is_starter_pack is False


async def test_seed_is_idempotent(db_session: AsyncSession, monkeypatch) -> None:
    await _seed_against_repo_collections(db_session, monkeypatch)
    await _seed_against_repo_collections(db_session, monkeypatch)

    result = await db_session.execute(
        select(Collection).where(Collection.is_starter_pack.is_(True))
    )
    assert len(result.scalars().all()) == EXPECTED_COLLECTION_COUNT

    community = await db_session.execute(
        select(Collection).where(Collection.is_starter_pack.is_(False))
    )
    assert len(community.scalars().all()) == EXPECTED_COMMUNITY_COUNT

    users = (
        await db_session.execute(select(User).where(User.email == SYSTEM_USER_EMAIL))
    ).scalars().all()
    assert len(users) == 1


async def test_system_user_is_passwordless_and_reused(db_session: AsyncSession) -> None:
    first = await get_or_create_system_user(db_session)
    second = await get_or_create_system_user(db_session)

    assert first.id == second.id
    assert first.password_hash is None
    assert first.is_admin is False
    assert first.is_active is True


async def test_seed_skips_missing_directory(db_session: AsyncSession, monkeypatch, tmp_path) -> None:
    empty_root = tmp_path / "collections"
    (empty_root / "base").mkdir(parents=True)
    (empty_root / "additional").mkdir(parents=True)
    monkeypatch.setattr(settings, "collections_root", str(empty_root))

    await seed_starter_collections(db_session)

    result = await db_session.execute(
        select(Collection).where(Collection.is_starter_pack.is_(True))
    )
    assert result.scalars().all() == []


async def test_seeded_artifacts_have_valid_json_columns(
    db_session: AsyncSession, monkeypatch
) -> None:
    """Artifact.tags/target_compatibility must be JSON-decodable, matching the
    convention _artifact_to_read() relies on (see collections.py)."""
    import json

    await _seed_against_repo_collections(db_session, monkeypatch)

    artifacts = (await db_session.execute(select(Artifact))).scalars().all()
    assert artifacts
    for artifact in artifacts:
        tags = json.loads(artifact.tags)
        compat = json.loads(artifact.target_compatibility)
        assert isinstance(tags, list)
        assert isinstance(compat, list)
        assert artifact.body.strip() != ""


async def _register(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "seed-compile@example.com",
            "password": "password123",
            "display_name": "Seed Compile",
        },
    )
    assert res.status_code == 201


async def _create_profile(
    client: AsyncClient,
    name: str,
    base_collection_id: str,
    additional_collection_ids: list[str] | None = None,
) -> str:
    res = await client.post(
        "/api/v1/profiles",
        json={
            "name": name,
            "base_collection_id": base_collection_id,
            "additional_collection_ids": additional_collection_ids or [],
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


async def test_base_profiles_compile_without_orchestration_warnings(
    async_client: AsyncClient, db_session: AsyncSession, monkeypatch
) -> None:
    """Regression guard for the three base starter packages: each must compile
    with zero `dangling_handoff` and zero `name_collision` warnings.

    This is the guard that would have caught the earlier drift where
    data-scientist/vibecoder agents described handoffs in prose but lacked
    the machine-readable `handoff_to` frontmatter (AGENTS.md rule 34) — a
    dangling handoff only surfaces at compile time, so compiling the real
    seeded content is the only way to catch it.
    """
    await _seed_against_repo_collections(db_session, monkeypatch)
    await _register(async_client)

    # The four base packages, keyed by their seeded display name.
    base_names = ["Software Engineer", "Data Scientist", "Vibecoder", "DevOps Engineer"]

    collections = (
        await db_session.execute(
            select(Collection).where(
                Collection.is_starter_pack.is_(True),
                Collection.collection_type == "base",
            )
        )
    ).scalars().all()
    by_name = {c.name: c for c in collections}
    assert set(base_names) <= set(by_name), f"Missing base packages: {set(base_names) - set(by_name)}"

    for name in base_names:
        collection = by_name[name]
        profile_id = await _create_profile(async_client, f"base-{name}", str(collection.id))

        res = await async_client.post(
            "/api/v1/profiles/compile",
            json={"profile_id": profile_id, "target": "claude-code"},
        )
        assert res.status_code == 200, f"{name} failed to compile: {res.text}"
        body = res.json()

        codes = [w["code"] for w in body["warnings"]]
        assert "dangling_handoff" not in codes, (
            f"{name} has a dangling handoff_to: {body['warnings']}"
        )
        assert "name_collision" not in codes, (
            f"{name} has a name collision: {body['warnings']}"
        )
        # Sanity: the profile actually resolved artifacts (not silently empty).
        assert body["artifact_count"] > 0, f"{name} compiled to zero artifacts"


async def test_additional_collections_compile_clean_on_software_engineer(
    async_client: AsyncClient, db_session: AsyncSession, monkeypatch
) -> None:
    """Regression guard for the additional starter packages: each must compile
    cleanly when layered onto the software-engineer base — zero
    `dangling_handoff` and zero `name_collision` warnings.

    Additional collections' agents legitimately reference base agents
    (`verifier`, `security-auditor`, `code-reviewer`) via handoff_to (rule 34
    resolves cross-collection at compile time), so this is the composition
    that must stay clean. Also guards the rule-29 naming discipline: two
    same-named artifacts across the composed set would surface as a
    name_collision warning here.
    """
    await _seed_against_repo_collections(db_session, monkeypatch)
    await _register(async_client)

    # Every seeded collection, starter and community-contributed alike: the
    # community-contributed add-ons still ship the same content and must keep
    # compiling cleanly onto these bases.
    collections = (
        await db_session.execute(select(Collection).where(Collection.git_url.like("seed://%")))
    ).scalars().all()
    by_name = {c.name: c for c in collections}

    base = by_name["Software Engineer"]
    additional_names = sorted(
        c.name for c in collections if c.collection_type == "additional"
    )
    assert additional_names, "Expected additional starter collections to be seeded"

    for name in additional_names:
        additional = by_name[name]
        profile_id = await _create_profile(
            async_client,
            f"se-{name}",
            str(base.id),
            additional_collection_ids=[str(additional.id)],
        )

        res = await async_client.post(
            "/api/v1/profiles/compile",
            json={"profile_id": profile_id, "target": "claude-code"},
        )
        assert res.status_code == 200, f"{name} failed to compile: {res.text}"
        body = res.json()

        codes = [w["code"] for w in body["warnings"]]
        assert "dangling_handoff" not in codes, (
            f"{name} on software-engineer has a dangling handoff_to: {body['warnings']}"
        )
        assert "name_collision" not in codes, (
            f"{name} on software-engineer has a name collision: {body['warnings']}"
        )
        assert body["artifact_count"] > 0, f"{name} compiled to zero artifacts"


NEW_ADDON_PACKS: dict[str, set[str]] = {
    "Git Practices": {
        "Git Workflow Discipline",
        "github",
        "precommit",
        "release",
        "Never Commit Secrets",
        "Commit One Concern At A Time",
        "Protect Shared Branches",
        "Green Before Merge",
    },
    "Design & Scaffold": {
        "Design Grilling",
        "New App Scaffold",
        "scout",
        "decision-log",
        "handoff",
        "Decide Before Building",
        "Scaffold Complete On Day One",
        "Verify Dependency Provenance",
    },
    "Self-Hosted Deployment": {
        "Self-Hosted App",
        "Docker Patterns",
        "One Container, One Database By Default",
        "Back Up Before You Change State",
        "Health Checks Gate Every Deploy",
    },
    "Enterprise AI Governance": {
        "Agent Guardrails",
        "Model Routing Policy",
        "Audit Trail and Attribution",
        "Classify Before You Send",
        "Confirm Before Production Or Publication",
        "Keep A Zero-Egress Path",
        "Attribute AI-Authored Changes",
    },
}


async def test_new_addon_packs_seed_their_artifacts(
    db_session: AsyncSession, monkeypatch
) -> None:
    """The four newer add-on packs seed with exactly the expected artifact names.

    Guards the public starter-pack contract from rule 42's vocabulary pass and
    rule 29's naming discipline: a renamed skill or moved file would change the
    compiled artifact set silently, so pin the names here.
    """
    await _seed_against_repo_collections(db_session, monkeypatch)

    collections = (
        await db_session.execute(
            select(Collection).where(Collection.is_starter_pack.is_(True))
        )
    ).scalars().all()
    by_name = {c.name: c for c in collections}

    for pack_name, expected_names in NEW_ADDON_PACKS.items():
        assert pack_name in by_name, f"Missing new add-on pack: {pack_name}"
        collection = by_name[pack_name]
        assert collection.collection_type == "additional"

        artifacts = (
            await db_session.execute(
                select(Artifact).where(Artifact.collection_id == collection.id)
            )
        ).scalars().all()
        assert {a.name for a in artifacts} == expected_names
        assert collection.artifact_count == len(expected_names)


async def test_dev_writing_pack_seeds_expected_artifacts(
    db_session: AsyncSession, monkeypatch
) -> None:
    """The Developer Writing add-on seeds its two skills and five rules.

    Pins the pack's artifact set the same way NEW_ADDON_PACKS does, so a
    renamed skill directory or a dropped `##` heading fails here instead of
    silently changing what users install (AGENTS.md rules 29 and 42).
    """
    await _seed_against_repo_collections(db_session, monkeypatch)

    collection = (
        await db_session.execute(
            select(Collection).where(Collection.name == "Developer Writing")
        )
    ).scalars().one()
    assert collection.is_starter_pack is True
    assert collection.collection_type == "additional"

    artifacts = (
        await db_session.execute(
            select(Artifact).where(Artifact.collection_id == collection.id)
        )
    ).scalars().all()

    expected = {
        "Developer Voice",
        "Review And Commit Wording",
        "Write The Way A Person Types",
        "No Dashes And No Forced Contrast",
        "Stop At The Last Point",
        "Name Things The Way People Do",
        "Never Invent An Event",
    }
    assert {a.name for a in artifacts} == expected
    assert collection.artifact_count == len(expected)


async def test_new_addons_compile_clean_together_on_software_engineer(
    async_client: AsyncClient, db_session: AsyncSession, monkeypatch
) -> None:
    """Software Engineer + all four new add-ons in one profile must compile with
    zero `name_collision` and zero `dangling_handoff` warnings.

    This is the exact composition the add-ons are designed to layer onto, and
    the check that rule 29 name uniqueness across collections actually holds —
    a collision shows up only when the whole set is resolved together.
    """
    await _seed_against_repo_collections(db_session, monkeypatch)
    await _register(async_client)

    collections = (
        await db_session.execute(
            select(Collection).where(Collection.is_starter_pack.is_(True))
        )
    ).scalars().all()
    by_name = {c.name: c for c in collections}
    base = by_name["Software Engineer"]
    addon_ids = [str(by_name[name].id) for name in NEW_ADDON_PACKS]

    profile_id = await _create_profile(
        async_client,
        "se-all-new-addons",
        str(base.id),
        additional_collection_ids=addon_ids,
    )

    res = await async_client.post(
        "/api/v1/profiles/compile",
        json={"profile_id": profile_id, "target": "claude-code"},
    )
    assert res.status_code == 200, f"Combined profile failed to compile: {res.text}"
    body = res.json()

    codes = [w["code"] for w in body["warnings"]]
    assert "dangling_handoff" not in codes, body["warnings"]
    assert "name_collision" not in codes, body["warnings"]
    assert body["artifact_count"] > 0


async def test_additional_collections_compile_clean_on_devops_engineer(
    async_client: AsyncClient, db_session: AsyncSession, monkeypatch
) -> None:
    """Regression guard for the DevOps Engineer base package: each additional
    starter collection must compile cleanly when layered onto it — zero
    `dangling_handoff` and zero `name_collision` warnings.

    The DevOps Engineer base deliberately reuses the software-engineer
    pipeline agent names (`builder`, `verifier`, `security-auditor`,
    `code-reviewer`, `docs-writer`, `debugger`, `orchestrator`) so the
    additional collections' handoff_to references to those names resolve
    against it too, and its skill/rule names are chosen to avoid colliding
    with the infra-related additions (devops, iac-expert, azure, aws, gcp,
    scaleway, auditor) it's most naturally composed with (AGENTS.md rule 29).
    """
    await _seed_against_repo_collections(db_session, monkeypatch)
    await _register(async_client)

    # Every seeded collection, starter and community-contributed alike: the
    # community-contributed add-ons still ship the same content and must keep
    # compiling cleanly onto these bases.
    collections = (
        await db_session.execute(select(Collection).where(Collection.git_url.like("seed://%")))
    ).scalars().all()
    by_name = {c.name: c for c in collections}

    base = by_name["DevOps Engineer"]
    additional_names = sorted(
        c.name for c in collections if c.collection_type == "additional"
    )
    assert additional_names, "Expected additional starter collections to be seeded"

    for name in additional_names:
        additional = by_name[name]
        profile_id = await _create_profile(
            async_client,
            f"de-{name}",
            str(base.id),
            additional_collection_ids=[str(additional.id)],
        )

        res = await async_client.post(
            "/api/v1/profiles/compile",
            json={"profile_id": profile_id, "target": "claude-code"},
        )
        assert res.status_code == 200, f"{name} failed to compile: {res.text}"
        body = res.json()

        codes = [w["code"] for w in body["warnings"]]
        assert "dangling_handoff" not in codes, (
            f"{name} on devops-engineer has a dangling handoff_to: {body['warnings']}"
        )
        assert "name_collision" not in codes, (
            f"{name} on devops-engineer has a name collision: {body['warnings']}"
        )
        assert body["artifact_count"] > 0, f"{name} compiled to zero artifacts"
