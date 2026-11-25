"""Reconcile already-seeded packs with the content currently on disk.

`seed_starter_collections()` is idempotent at the *collection* level: once a
`seed://<collection_type>/<slug>` row exists, its files are never re-read, so
an in-place edit to an already-shipped pack only ever reaches a fresh install
(AGENTS.md rule 25). That is the right default for a boot-time seed — it must
never clobber anything on every restart — but it leaves a long-lived
deployment accumulating every rename and addition that shipped after it was
first seeded.

This module is the deliberate, opt-in fix. It diffs each seeded pack against
its files and, when asked to apply:

- adds items that exist on disk but not in the database,
- soft-deletes items whose names are gone from disk (never a hard delete —
  AGENTS.md rule 15),
- collapses duplicate live names, keeping the row whose
  `artifact_type`/`file_path` matches what is on disk,
- optionally rewrites the content of items that exist on both sides,
- recomputes `Collection.artifact_count` from the live rows.

Anything the seed has never seen (a pack that was never seeded, a user's own
collection) is left alone. Run it with `--dry-run` (the default) first; see
`app/scripts/reconcile_seeded_collections.py`.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.models.artifact import Artifact
from app.models.collection import Collection
from app.services.seed_collections import (
    COMMUNITY_CONTRIBUTED_COLLECTIONS,
    STARTER_COLLECTIONS,
    _scan_seeded_collection,
    artifact_from_scanned,
)

logger = logging.getLogger("myace")

# Fields compared when deciding whether an item's content drifted. Identity and
# bookkeeping columns (id, collection_id, timestamps, is_enabled, deleted_at)
# are deliberately absent: is_enabled is the owner's toggle, not content.
CONTENT_FIELDS = (
    "artifact_type",
    "description",
    "body",
    "file_path",
    "priority",
    "version",
    "target_compatibility",
    "tags",
    "handoff_to",
)


@dataclass
class PackChange:
    """What reconciling one seeded pack would do (or did)."""

    name: str
    seed_ref: str
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    duplicates_removed: list[str] = field(default_factory=list)
    content_updated: list[str] = field(default_factory=list)
    content_changed: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (
            self.added
            or self.removed
            or self.duplicates_removed
            or self.content_updated
            or self.content_changed
        )


@dataclass
class ReconcileReport:
    applied: bool
    packs: list[PackChange] = field(default_factory=list)
    missing_packs: list[str] = field(default_factory=list)

    @property
    def changed_packs(self) -> list[PackChange]:
        return [p for p in self.packs if not p.is_empty]


def _disk_items(collection_type: str, slug: str) -> dict[str, dict]:
    directory = Path(settings.collections_root) / collection_type / slug
    return {item["name"]: item for item in _scan_seeded_collection(directory)}


def _content_differs(artifact: Artifact, item: dict) -> bool:
    candidate = artifact_from_scanned(artifact.collection_id, item)
    return any(getattr(candidate, name) != getattr(artifact, name) for name in CONTENT_FIELDS)


def _apply_content(artifact: Artifact, item: dict) -> None:
    candidate = artifact_from_scanned(artifact.collection_id, item)
    for name in CONTENT_FIELDS:
        setattr(artifact, name, getattr(candidate, name))


def _pick_duplicate_keeper(rows: list[Artifact], item: dict | None) -> Artifact:
    """Among same-named live rows, prefer the one the files describe.

    A renamed rule whose pack also contains a skill of the old name leaves two
    live rows sharing a name (the rule never got renamed in the database). The
    row matching the on-disk `artifact_type`/`file_path` is the one the scan
    just produced, so it is the one to keep.
    """
    if item is not None:
        for row in rows:
            if row.artifact_type == item["artifact_type"] and row.file_path == item.get(
                "file_path", ""
            ):
                return row
    return max(rows, key=lambda row: row.updated_at)


async def reconcile_seeded_collections(
    session: AsyncSession,
    *,
    apply: bool = False,
    update_content: bool = False,
    only: str | None = None,
) -> ReconcileReport:
    """Diff every seeded pack against its files; write only when `apply`.

    `apply=False` computes the same report without touching the session, so a
    dry run is a true preview. `only` limits the run to one registry slug (its
    `seed://` ref is still the lookup key).
    """
    report = ReconcileReport(applied=apply)

    seeded = (
        await session.execute(select(Collection).where(Collection.git_url.like("seed://%")))
    ).scalars().all()
    by_ref = {collection.git_url: collection for collection in seeded}

    for registry in (STARTER_COLLECTIONS, COMMUNITY_CONTRIBUTED_COLLECTIONS):
        for collection_type, packs in registry.items():
            for slug in packs:
                if only is not None and slug != only:
                    continue

                seed_ref = f"seed://{collection_type}/{slug}"
                collection = by_ref.get(seed_ref)
                if collection is None:
                    report.missing_packs.append(seed_ref)
                    continue

                on_disk = _disk_items(collection_type, slug)
                live = (
                    await session.execute(
                        select(Artifact).where(
                            Artifact.collection_id == collection.id,
                            Artifact.deleted_at.is_(None),
                        )
                    )
                ).scalars().all()

                change = PackChange(name=collection.name, seed_ref=seed_ref)

                by_name: dict[str, list[Artifact]] = {}
                for artifact in live:
                    by_name.setdefault(artifact.name, []).append(artifact)

                for name, rows in by_name.items():
                    if name not in on_disk:
                        change.removed.extend([name] * len(rows))
                        if apply:
                            for row in rows:
                                row.deleted_at = datetime.now(UTC)
                                session.add(row)
                        continue

                    keeper = _pick_duplicate_keeper(rows, on_disk[name])
                    for row in rows:
                        if row is not keeper:
                            change.duplicates_removed.append(name)
                            if apply:
                                row.deleted_at = datetime.now(UTC)
                                session.add(row)

                    if _content_differs(keeper, on_disk[name]):
                        if update_content:
                            change.content_updated.append(name)
                            if apply:
                                _apply_content(keeper, on_disk[name])
                                session.add(keeper)
                        else:
                            change.content_changed.append(name)

                for name, item in on_disk.items():
                    if name in by_name:
                        continue
                    change.added.append(name)
                    if apply:
                        session.add(artifact_from_scanned(collection.id, item))

                if apply:
                    surviving = len([n for n in on_disk if n in by_name]) + len(change.added)
                    collection.artifact_count = surviving
                    session.add(collection)

                report.packs.append(change)

    if apply:
        await session.commit()

    return report
