"""Tests for reconciling already-seeded packs with the content on disk."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.models.artifact import Artifact
from app.models.collection import Collection
from app.services.seed_collections import seed_starter_collections
from app.services.seed_reconcile import (
    PackChange,
    ReconcileReport,
    reconcile_seeded_collections,
)

# backend/tests/test_seed_reconcile.py -> repo root is two parents up.
REPO_COLLECTIONS_ROOT = Path(__file__).resolve().parents[2] / "collections"

EDITOR_REF = "seed://additional/editor"
EDITOR_NAME = "Documentation Editor"


async def _seed(db_session: AsyncSession, monkeypatch, root: Path | None = None) -> None:
    monkeypatch.setattr(settings, "collections_root", str(root or REPO_COLLECTIONS_ROOT))
    await seed_starter_collections(db_session)


async def _collection(db_session: AsyncSession, ref: str) -> Collection:
    result = await db_session.execute(select(Collection).where(Collection.git_url == ref))
    return result.scalars().one()


async def _artifacts(
    db_session: AsyncSession, collection: Collection, *, include_deleted: bool = False
) -> list[Artifact]:
    statement = select(Artifact).where(Artifact.collection_id == collection.id)
    if not include_deleted:
        statement = statement.where(Artifact.deleted_at.is_(None))
    return list((await db_session.execute(statement)).scalars().all())


async def test_freshly_seeded_packs_report_no_drift(db_session: AsyncSession, monkeypatch) -> None:
    """A pack just imported from disk must diff clean.

    Guards the JSON-text round trip in `artifact_from_scanned()`: tags,
    target_compatibility and handoff_to are serialized on write and re-derived
    from the scan on compare, so an asymmetry here would show every pack as
    permanently drifted.
    """
    await _seed(db_session, monkeypatch)

    report = await reconcile_seeded_collections(db_session, apply=False)

    assert report.changed_packs == []
    assert report.missing_packs == []


async def test_missing_packs_are_reported(db_session: AsyncSession, monkeypatch, tmp_path) -> None:
    """A registry entry with no collection row is a pack that seeds on next boot."""
    empty_root = tmp_path / "collections"
    (empty_root / "base").mkdir(parents=True)
    (empty_root / "additional").mkdir(parents=True)
    await _seed(db_session, monkeypatch, root=empty_root)

    report = await reconcile_seeded_collections(db_session, apply=False)

    assert EDITOR_REF in report.missing_packs


async def test_dry_run_reports_drift_without_writing(db_session: AsyncSession, monkeypatch) -> None:
    await _seed(db_session, monkeypatch)
    editor = await _collection(db_session, EDITOR_REF)

    renamed = (
        await db_session.execute(
            select(Artifact).where(
                Artifact.collection_id == editor.id,
                Artifact.name == "Documentation Standards",
            )
        )
    ).scalars().one()
    renamed.name = "Documentation Standards (old name)"
    db_session.add(renamed)
    await db_session.commit()

    report = await reconcile_seeded_collections(db_session, apply=False)

    change = next(p for p in report.packs if p.seed_ref == EDITOR_REF)
    assert "Documentation Standards (old name)" in change.removed
    assert "Documentation Standards" in change.added
    assert report.applied is False

    # Nothing was written: the renamed row is still live and no new row exists.
    live = await _artifacts(db_session, editor)
    names = {artifact.name for artifact in live}
    assert "Documentation Standards (old name)" in names
    assert "Documentation Standards" not in names


async def test_apply_restores_pack_to_disk_and_soft_deletes(
    db_session: AsyncSession, monkeypatch
) -> None:
    await _seed(db_session, monkeypatch)
    editor = await _collection(db_session, EDITOR_REF)

    stale = Artifact(
        collection_id=editor.id,
        artifact_type="rule",
        name="Rule That No Longer Exists",
        version="1.0.0",
        priority=50,
        target_compatibility="[]",
        tags="[]",
        description="",
        body="gone",
        file_path="AGENTS.md",
    )
    db_session.add(stale)
    await db_session.commit()

    report = await reconcile_seeded_collections(db_session, apply=True)
    assert report.applied is True

    live = await _artifacts(db_session, editor)
    live_names = {artifact.name for artifact in live}
    assert "Rule That No Longer Exists" not in live_names
    assert "Writing For Agent Readers" in live_names

    # Soft delete only: the row is still there, just excluded from live reads.
    everything = await _artifacts(db_session, editor, include_deleted=True)
    assert "Rule That No Longer Exists" in {a.name for a in everything}

    refreshed = await _collection(db_session, EDITOR_REF)
    assert refreshed.artifact_count == len(live)

    # Re-running is a no-op: the reconcile is idempotent.
    second = await reconcile_seeded_collections(db_session, apply=True)
    assert second.changed_packs == []


async def test_duplicate_names_collapse_to_the_row_the_files_describe(
    db_session: AsyncSession, monkeypatch
) -> None:
    """A renamed rule that shares its old name with a skill left two live rows."""
    await _seed(db_session, monkeypatch)
    editor = await _collection(db_session, EDITOR_REF)

    twin = Artifact(
        collection_id=editor.id,
        artifact_type="rule",
        name="Documentation Standards",
        version="1.0.0",
        priority=50,
        target_compatibility="[]",
        tags="[]",
        description="old rule that was renamed",
        body="old rule body",
        file_path="AGENTS.md",
    )
    db_session.add(twin)
    await db_session.commit()

    await reconcile_seeded_collections(db_session, apply=True)

    live = [a for a in await _artifacts(db_session, editor) if a.name == "Documentation Standards"]
    assert len(live) == 1
    assert live[0].artifact_type == "skill"
    assert live[0].file_path == "skills/doc-standards/SKILL.md"


async def test_content_changes_need_update_content(db_session: AsyncSession, monkeypatch) -> None:
    await _seed(db_session, monkeypatch)
    editor = await _collection(db_session, EDITOR_REF)

    item = (
        await db_session.execute(
            select(Artifact).where(
                Artifact.collection_id == editor.id,
                Artifact.name == "Documentation Standards",
            )
        )
    ).scalars().one()
    original_body = item.body
    item.body = "hand-written replacement"
    db_session.add(item)
    await db_session.commit()

    report = await reconcile_seeded_collections(db_session, apply=True)
    change = next(p for p in report.packs if p.seed_ref == EDITOR_REF)
    assert "Documentation Standards" in change.content_changed
    assert change.content_updated == []

    unchanged = (
        await db_session.execute(
            select(Artifact).where(Artifact.id == item.id)
        )
    ).scalars().one()
    assert unchanged.body == "hand-written replacement"

    await reconcile_seeded_collections(db_session, apply=True, update_content=True)

    restored = (await db_session.execute(select(Artifact).where(Artifact.id == item.id))).scalars().one()
    assert restored.body == original_body


async def test_only_limits_the_run_to_one_pack(db_session: AsyncSession, monkeypatch) -> None:
    await _seed(db_session, monkeypatch)
    editor = await _collection(db_session, EDITOR_REF)

    ghost = Artifact(
        collection_id=editor.id,
        artifact_type="rule",
        name="Ghost Rule",
        version="1.0.0",
        priority=50,
        target_compatibility="[]",
        tags="[]",
        description="",
        body="ghost",
        file_path="AGENTS.md",
    )
    db_session.add(ghost)
    await db_session.commit()

    report = await reconcile_seeded_collections(db_session, apply=True, only="software-engineer")

    assert all(pack.seed_ref != EDITOR_REF for pack in report.packs)
    still_there = await _artifacts(db_session, editor)
    assert "Ghost Rule" in {artifact.name for artifact in still_there}


async def test_user_collections_are_never_touched(db_session: AsyncSession, monkeypatch) -> None:
    await _seed(db_session, monkeypatch)

    user_collection = Collection(
        owner_id=(await db_session.execute(select(Collection))).scalars().first().owner_id,
        name="My own pack",
        description="not from collections/",
        git_url="https://github.com/example/my-own-pack",
        collection_type="additional",
        visibility="private",
        artifact_count=1,
    )
    db_session.add(user_collection)
    await db_session.commit()
    await db_session.refresh(user_collection)

    db_session.add(
        Artifact(
            collection_id=user_collection.id,
            artifact_type="skill",
            name="Hand Written Skill",
            version="1.0.0",
            priority=50,
            target_compatibility="[]",
            tags="[]",
            description="",
            body="mine",
            file_path="skills/hand-written/SKILL.md",
        )
    )
    await db_session.commit()

    report = await reconcile_seeded_collections(db_session, apply=True)

    assert all(pack.seed_ref.startswith("seed://") for pack in report.packs)
    untouched = await _artifacts(db_session, user_collection)
    assert [artifact.name for artifact in untouched] == ["Hand Written Skill"]


async def test_missing_collections_root_deletes_nothing(
    db_session: AsyncSession, monkeypatch, tmp_path
) -> None:
    """A wrong COLLECTIONS_ROOT must not read as "every file was deleted".

    The default root is /app/collections, which does not exist on a host
    checkout, so this is one mistyped command away from wiping every seeded
    pack. Mirrors `seed_starter_collections()`'s early return.
    """
    await _seed(db_session, monkeypatch)
    before = (await db_session.execute(select(Artifact).where(Artifact.deleted_at.is_(None)))).scalars().all()

    monkeypatch.setattr(settings, "collections_root", str(tmp_path / "nope"))
    report = await reconcile_seeded_collections(db_session, apply=True)

    assert report.root_error is not None
    assert report.packs == []
    assert report.changed_packs == []

    db_session.expire_all()
    after = (await db_session.execute(select(Artifact).where(Artifact.deleted_at.is_(None)))).scalars().all()
    assert len(after) == len(before)


async def test_missing_pack_directory_is_skipped_not_reconciled_to_zero(
    db_session: AsyncSession, monkeypatch, tmp_path
) -> None:
    """One missing pack directory is "unreadable", not "all its items went away"."""
    await _seed(db_session, monkeypatch)
    editor = await _collection(db_session, EDITOR_REF)
    editor_id = editor.id
    before = len(await _artifacts(db_session, editor))
    assert before > 0

    empty_root = tmp_path / "collections"
    (empty_root / "base").mkdir(parents=True)
    (empty_root / "additional").mkdir(parents=True)
    monkeypatch.setattr(settings, "collections_root", str(empty_root))

    report = await reconcile_seeded_collections(db_session, apply=True)

    assert EDITOR_REF in report.skipped
    assert all(pack.seed_ref != EDITOR_REF for pack in report.packs)
    db_session.expire_all()
    remaining = (
        await db_session.execute(
            select(Artifact).where(
                Artifact.collection_id == editor_id, Artifact.deleted_at.is_(None)
            )
        )
    ).scalars().all()
    assert len(remaining) == before


async def test_content_only_pack_is_not_counted_as_structural(
    db_session: AsyncSession, monkeypatch
) -> None:
    """The CLI trailer promises "applied changes" only for real writes."""
    await _seed(db_session, monkeypatch)
    editor = await _collection(db_session, EDITOR_REF)

    item = (
        await db_session.execute(
            select(Artifact).where(
                Artifact.collection_id == editor.id,
                Artifact.name == "Documentation Standards",
            )
        )
    ).scalars().one()
    item.body = "hand-written replacement"
    db_session.add(item)
    await db_session.commit()

    report = await reconcile_seeded_collections(db_session, apply=True)

    assert report.structural_packs == []
    assert [pack.seed_ref for pack in report.content_only_packs] == [EDITOR_REF]


def test_known_slugs_covers_both_registries() -> None:
    from app.scripts.reconcile_seeded_collections import _known_slugs

    slugs = _known_slugs()
    assert {"editor", "dev-writing", "software-engineer", "eu-ai-act"} <= slugs


def test_report_never_claims_clean_when_packs_were_skipped(capsys) -> None:
    """All-skipped is what a wrong-but-existing root produces, not a clean run."""
    from app.scripts.reconcile_seeded_collections import _print_report

    report = ReconcileReport(applied=False, skipped=["seed://additional/editor"])
    _print_report(report, show_content=True)

    out = capsys.readouterr().out
    assert "every seeded pack matches its files" not in out
    assert "with a source directory" in out


def test_report_never_claims_clean_when_packs_are_not_seeded(capsys) -> None:
    from app.scripts.reconcile_seeded_collections import _print_report

    report = ReconcileReport(applied=False, missing_packs=["seed://additional/editor"])
    _print_report(report, show_content=True)

    out = capsys.readouterr().out
    assert "every seeded pack matches its files" not in out
    assert "not seeded yet" in out


def test_clean_report_still_says_so(capsys) -> None:
    from app.scripts.reconcile_seeded_collections import _print_report

    report = ReconcileReport(
        applied=False, packs=[PackChange(name="Documentation Editor", seed_ref="seed://x")]
    )
    _print_report(report, show_content=True)

    assert "every seeded pack matches its files" in capsys.readouterr().out


def test_applied_content_only_report_does_not_claim_deletions(capsys) -> None:
    """Nothing was deleted, so the trailer must not say anything was."""
    from app.scripts.reconcile_seeded_collections import _print_report

    report = ReconcileReport(
        applied=True,
        packs=[
            PackChange(
                name="Documentation Editor",
                seed_ref="seed://additional/editor",
                content_changed=["Documentation Standards"],
            )
        ],
    )
    _print_report(report, show_content=True)

    out = capsys.readouterr().out
    assert "soft-deleted" not in out
    assert "--update-content" in out
