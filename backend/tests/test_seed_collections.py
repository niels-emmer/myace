"""Tests for install-time starter-pack seeding (app/services/seed_collections.py)."""

from pathlib import Path

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.models.artifact import Artifact
from app.models.collection import Collection
from app.models.user import User
from app.services.seed_collections import (
    STARTER_COLLECTIONS,
    SYSTEM_USER_EMAIL,
    get_or_create_system_user,
    seed_starter_collections,
)

# backend/tests/test_seed_collections.py -> repo root is two parents up.
REPO_COLLECTIONS_ROOT = Path(__file__).resolve().parents[2] / "collections"

EXPECTED_COLLECTION_COUNT = sum(len(c) for c in STARTER_COLLECTIONS.values())


async def _seed_against_repo_collections(db_session: AsyncSession, monkeypatch) -> None:
    monkeypatch.setattr(settings, "collections_root", str(REPO_COLLECTIONS_ROOT))
    await seed_starter_collections(db_session)


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


async def test_seed_is_idempotent(db_session: AsyncSession, monkeypatch) -> None:
    await _seed_against_repo_collections(db_session, monkeypatch)
    await _seed_against_repo_collections(db_session, monkeypatch)

    result = await db_session.execute(
        select(Collection).where(Collection.is_starter_pack.is_(True))
    )
    assert len(result.scalars().all()) == EXPECTED_COLLECTION_COUNT

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

    collections = (
        await db_session.execute(
            select(Collection).where(Collection.is_starter_pack.is_(True))
        )
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

    collections = (
        await db_session.execute(
            select(Collection).where(Collection.is_starter_pack.is_(True))
        )
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
