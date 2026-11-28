"""Pack relations, the content-updated stamp, derived topics and metadata reconcile.

Public reads stay anonymous and visibility-gated (ADR-0014): a related pack that
an anonymous visitor could not open must never be linked.
"""

import json
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.models.artifact import Artifact
from app.models.collection import Collection
from app.services.pack_relations import parse_relations
from app.services.pack_topics import derive_topics
from app.services.seed_collections import seed_starter_collections
from app.services.seed_reconcile import reconcile_seeded_collections

REPO_COLLECTIONS_ROOT = Path(__file__).resolve().parents[2] / "collections"
API = "/api/v1/collections/community"


async def _pack(
    session: AsyncSession,
    name: str,
    ref: str,
    *,
    relations: dict[str, list[str]] | None = None,
    published: bool = True,
    status: str = "approved",
) -> Collection:
    collection = Collection(
        owner_id=uuid.uuid4(),
        name=name,
        description="d",
        git_url=ref,
        collection_type="additional",
        visibility="public",
        published=published,
        moderation_status=status,
        category="Testing",
        relations=json.dumps(relations) if relations is not None else None,
    )
    session.add(collection)
    await session.commit()
    await session.refresh(collection)
    return collection


async def _item(session: AsyncSession, pack: Collection, name: str, tags: list[str]) -> None:
    session.add(
        Artifact(
            collection_id=pack.id,
            artifact_type="skill",
            name=name,
            body="b",
            file_path="x",
            tags=json.dumps(tags),
        )
    )
    await session.commit()


# ---- pure functions --------------------------------------------------------


def test_parse_relations_tolerates_missing_and_malformed() -> None:
    empty = {"layers_on": [], "pairs_with": []}
    assert parse_relations(None) == empty
    assert parse_relations("") == empty
    assert parse_relations("not json") == empty
    assert parse_relations("[1, 2]") == empty
    assert parse_relations('{"layers_on": ["a", 3], "pairs_with": ["b"]}') == {
        "layers_on": ["a"],
        "pairs_with": ["b"],
    }


def test_derive_topics_ranks_by_frequency_and_drops_noise() -> None:
    tag_lists = [
        ["python", "typing", "mode:subagent"],
        ["python", "testing", "process"],
        ["python", "testing", "build"],
        ["go"],
    ]
    # `go` appears once (below min_count), process/build are stoplisted,
    # mode:* is never a topic; ties break alphabetically.
    assert derive_topics(tag_lists) == ["python", "testing"]
    assert derive_topics(tag_lists, limit=1) == ["python"]
    assert derive_topics([]) == []


# ---- relations -------------------------------------------------------------


@pytest.mark.asyncio
async def test_detail_resolves_relations_and_hides_unreachable_packs(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _pack(db_session, "Infra", "seed://additional/iac-expert")
    await _pack(db_session, "Draft", "seed://base/draft-pack", published=False, status="draft")
    cloud = await _pack(
        db_session,
        "Cloud",
        "seed://additional/cloud",
        relations={
            "layers_on": ["iac-expert", "missing-slug"],
            "pairs_with": ["draft-pack", "cloud"],
        },
    )

    res = await async_client.get(f"{API}/{cloud.id}")

    assert res.status_code == 200
    relations = res.json()["relations"]
    assert [ref["slug"] for ref in relations["layers_on"]] == ["iac-expert"]
    assert relations["layers_on"][0]["name"] == "Infra"
    # An unpublished pack, an unknown slug and a self-reference are all dropped.
    assert relations["pairs_with"] == []


@pytest.mark.asyncio
async def test_detail_relations_are_null_when_none_declared_or_resolvable(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    plain = await _pack(db_session, "Plain", "seed://additional/plain")
    lonely = await _pack(
        db_session, "Lonely", "seed://additional/lonely", relations={"layers_on": ["nope"]}
    )

    assert (await async_client.get(f"{API}/{plain.id}")).json()["relations"] is None
    assert (await async_client.get(f"{API}/{lonely.id}")).json()["relations"] is None


@pytest.mark.asyncio
async def test_list_does_not_resolve_relations(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _pack(db_session, "Infra", "seed://additional/iac-expert")
    await _pack(
        db_session, "Cloud", "seed://additional/cloud", relations={"layers_on": ["iac-expert"]}
    )

    items = (await async_client.get(API)).json()["items"]

    assert all(item["relations"] is None for item in items)


# ---- topics ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_topics_route_is_anonymous_and_only_covers_public_packs(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    public = await _pack(db_session, "Py", "seed://additional/py")
    hidden = await _pack(db_session, "Hidden", "seed://additional/hidden", published=False, status="draft")
    for pack in (public, hidden):
        await _item(db_session, pack, "a", ["python", "testing"])
        await _item(db_session, pack, "b", ["python"])

    res = await async_client.get(f"{API}/topics")

    # Not shadowed by /community/{collection_id} (rule 16).
    assert res.status_code == 200
    assert res.json() == {str(public.id): ["python"]}


@pytest.mark.asyncio
async def test_topics_ignore_disabled_and_deleted_items(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    pack = await _pack(db_session, "Py", "seed://additional/py")
    await _item(db_session, pack, "a", ["python"])
    await _item(db_session, pack, "b", ["python"])
    rows = (
        await db_session.execute(select(Artifact).where(Artifact.collection_id == pack.id))
    ).scalars().all()
    rows[0].is_enabled = False
    db_session.add(rows[0])
    await db_session.commit()

    # Only one enabled item carries the tag now, below min_count.
    assert (await async_client.get(f"{API}/topics")).json() == {}


# ---- seeding and reconcile --------------------------------------------------


async def _seed(db_session: AsyncSession, monkeypatch) -> None:
    monkeypatch.setattr(settings, "collections_root", str(REPO_COLLECTIONS_ROOT))
    await seed_starter_collections(db_session)


async def _by_ref(db_session: AsyncSession, ref: str) -> Collection:
    return (
        await db_session.execute(select(Collection).where(Collection.git_url == ref))
    ).scalars().one()


@pytest.mark.asyncio
async def test_seeding_records_relations_and_a_content_stamp(
    db_session: AsyncSession, monkeypatch
) -> None:
    await _seed(db_session, monkeypatch)

    aws = await _by_ref(db_session, "seed://additional/aws")

    assert parse_relations(aws.relations)["layers_on"] == ["iac-expert"]
    assert aws.content_updated_at is not None


@pytest.mark.asyncio
async def test_metadata_drift_is_reported_but_not_applied_by_default(
    db_session: AsyncSession, monkeypatch
) -> None:
    await _seed(db_session, monkeypatch)
    aws = await _by_ref(db_session, "seed://additional/aws")
    aws.description = "stale description"
    aws.category = "Old Category"
    db_session.add(aws)
    await db_session.commit()

    report = await reconcile_seeded_collections(db_session, apply=True)

    change = next(p for p in report.packs if p.seed_ref == "seed://additional/aws")
    assert {d.field for d in change.metadata_changed} == {"description", "category"}
    assert change.metadata_updated == []
    assert (await _by_ref(db_session, "seed://additional/aws")).description == "stale description"


@pytest.mark.asyncio
async def test_update_metadata_rewrites_only_registry_fields(
    db_session: AsyncSession, monkeypatch
) -> None:
    await _seed(db_session, monkeypatch)
    aws = await _by_ref(db_session, "seed://additional/aws")
    aws.description = "stale description"
    aws.relations = None
    # Fields the registry must never touch.
    aws.avg_rating = 4.5
    aws.rating_count = 7
    aws.download_count = 12
    aws.moderation_status = "approved"
    db_session.add(aws)
    await db_session.commit()

    report = await reconcile_seeded_collections(db_session, apply=True, update_metadata=True)

    change = next(p for p in report.packs if p.seed_ref == "seed://additional/aws")
    assert {d.field for d in change.metadata_updated} == {"description", "relations"}
    assert change.has_structural_change
    fresh = await _by_ref(db_session, "seed://additional/aws")
    assert fresh.description != "stale description"
    assert parse_relations(fresh.relations)["layers_on"] == ["iac-expert"]
    assert (fresh.avg_rating, fresh.rating_count, fresh.download_count) == (4.5, 7, 12)

    # Idempotent: a second run has nothing to say.
    again = await reconcile_seeded_collections(db_session, apply=False, update_metadata=True)
    assert again.changed_packs == []


@pytest.mark.asyncio
async def test_dry_run_metadata_writes_nothing(db_session: AsyncSession, monkeypatch) -> None:
    await _seed(db_session, monkeypatch)
    aws = await _by_ref(db_session, "seed://additional/aws")
    aws.category = "Old Category"
    db_session.add(aws)
    await db_session.commit()

    report = await reconcile_seeded_collections(db_session, apply=False, update_metadata=True)

    assert any(d.field == "category" for p in report.packs for d in p.metadata_updated)
    assert (await _by_ref(db_session, "seed://additional/aws")).category == "Old Category"


@pytest.mark.asyncio
async def test_reconcile_stamps_content_updated_only_when_items_change(
    db_session: AsyncSession, monkeypatch
) -> None:
    await _seed(db_session, monkeypatch)
    aws = await _by_ref(db_session, "seed://additional/aws")
    aws.content_updated_at = None
    db_session.add(aws)
    await db_session.commit()

    # A metadata-only apply must not look like a content change.
    await reconcile_seeded_collections(db_session, apply=True, update_metadata=True)
    assert (await _by_ref(db_session, "seed://additional/aws")).content_updated_at is None

    # Dropping an item and reconciling restores it, which is a content change.
    item = (
        await db_session.execute(
            select(Artifact).where(Artifact.collection_id == aws.id).limit(1)
        )
    ).scalars().one()
    item.deleted_at = item.created_at
    db_session.add(item)
    await db_session.commit()
    await reconcile_seeded_collections(db_session, apply=True)
    assert (await _by_ref(db_session, "seed://additional/aws")).content_updated_at is not None
