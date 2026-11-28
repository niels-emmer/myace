"""Resolve a seeded pack's advisory relations to packs on this deployment.

`Collection.relations` stores registry slugs (`{"layers_on": [...], "pairs_with":
[...]}`), because ids differ per deployment. The public pack read resolves them
here, dropping any slug that does not resolve to a pack an anonymous visitor may
see (ADR-0014), so a pack never links to something that would 404.

Advisory only, like `handoff_to` (AGENTS.md rule 34): nothing enforces them.
"""

import json
import uuid

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.collection import Collection


class PackRef(BaseModel):
    """A link to another pack: enough for the UI to render and navigate."""

    id: uuid.UUID
    name: str
    slug: str


class PackRelationsRead(BaseModel):
    layers_on: list[PackRef] = []
    pairs_with: list[PackRef] = []


def parse_relations(raw: str | None) -> dict[str, list[str]]:
    """Decode `Collection.relations`; malformed or missing means no relations."""
    empty: dict[str, list[str]] = {"layers_on": [], "pairs_with": []}
    if not raw:
        return empty
    try:
        data = json.loads(raw)
    except ValueError:
        return empty
    if not isinstance(data, dict):
        return empty
    return {
        key: [slug for slug in data.get(key, []) if isinstance(slug, str)]
        for key in ("layers_on", "pairs_with")
    }


def _seed_refs(slug: str) -> tuple[str, str]:
    return (f"seed://base/{slug}", f"seed://additional/{slug}")


async def resolve_relations(
    session: AsyncSession, collection: Collection
) -> PackRelationsRead | None:
    """The pack's relations as links, or None when it declares none that resolve."""
    wanted = parse_relations(collection.relations)
    slugs = {slug for group in wanted.values() for slug in group}
    if not slugs:
        return None

    refs = [ref for slug in slugs for ref in _seed_refs(slug)]
    rows = (
        await session.execute(
            select(Collection).where(
                Collection.git_url.in_(refs),  # type: ignore[attr-defined]
                Collection.is_active == True,  # noqa: E712
                Collection.published == True,  # noqa: E712
                Collection.moderation_status == "approved",
            )
        )
    ).scalars().all()
    by_slug = {row.git_url.rsplit("/", 1)[-1]: row for row in rows}

    def refs_for(group: list[str]) -> list[PackRef]:
        return [
            PackRef(id=by_slug[slug].id, name=by_slug[slug].name, slug=slug)
            for slug in group
            if slug in by_slug and by_slug[slug].id != collection.id
        ]

    result = PackRelationsRead(
        layers_on=refs_for(wanted["layers_on"]), pairs_with=refs_for(wanted["pairs_with"])
    )
    if not result.layers_on and not result.pairs_with:
        return None
    return result
