"""Tests for install-time starter-pack seeding (app/services/seed_collections.py)."""

from pathlib import Path

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
