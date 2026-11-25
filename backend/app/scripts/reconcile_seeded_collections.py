"""Reconcile already-seeded packs with the content on disk (AGENTS.md rule 25).

    python -m app.scripts.reconcile_seeded_collections                  # dry run
    python -m app.scripts.reconcile_seeded_collections --apply
    python -m app.scripts.reconcile_seeded_collections --apply --update-content
    python -m app.scripts.reconcile_seeded_collections --apply --only editor

`seed_starter_collections()` never re-reads a pack it has already seeded, so a
rename or an added skill in an existing pack reaches a fresh install and
nothing else. This command is the deliberate way to bring a long-lived
deployment back in line: it adds what the files have and the database lacks,
soft-deletes what the database has and the files dropped, collapses duplicate
names, and (with `--update-content`) rewrites items that exist on both sides
but whose text changed.

Dry run unless `--apply` is passed, and it never touches a collection that did
not come from `collections/`.

Inside Docker:

    docker compose exec -T backend \\
        python -m app.scripts.reconcile_seeded_collections --apply

Take a backup first — `docs/deployment.md` covers the database dump.
"""

import argparse
import asyncio
import sys

from app.core.database import get_session_factory
from app.services.seed_collections import (
    COMMUNITY_CONTRIBUTED_COLLECTIONS,
    STARTER_COLLECTIONS,
)
from app.services.seed_reconcile import ReconcileReport, reconcile_seeded_collections


def _known_slugs() -> set[str]:
    return {
        slug
        for registry in (STARTER_COLLECTIONS, COMMUNITY_CONTRIBUTED_COLLECTIONS)
        for packs in registry.values()
        for slug in packs
    }


def _print_report(report: ReconcileReport, *, show_content: bool) -> None:
    if report.skipped:
        print("Skipped — no source directory (nothing deleted for these):")
        for ref in report.skipped:
            print(f"  {ref}")
        print()

    if report.missing_packs:
        print("Not seeded yet (they seed on the next backend start):")
        for ref in report.missing_packs:
            print(f"  {ref}")
        print()

    changed = report.changed_packs
    if not changed:
        print("Nothing to reconcile: every seeded pack matches its files.")
        return

    for pack in changed:
        print(pack.name)
        if pack.added:
            print(f"  + add:       {', '.join(sorted(pack.added))}")
        if pack.removed:
            print(f"  - remove:    {', '.join(sorted(pack.removed))}")
        if pack.duplicates_removed:
            print(f"  - duplicate: {', '.join(sorted(pack.duplicates_removed))}")
        if pack.content_updated:
            print(f"  ~ updated:   {', '.join(sorted(pack.content_updated))}")
        if show_content and pack.content_changed:
            print(f"  ~ differs:   {', '.join(sorted(pack.content_changed))} (not applied)")
        print()

    structural = len(report.structural_packs)
    content_only = len(report.content_only_packs)

    if report.applied:
        print(
            f"Applied changes to {structural} pack(s). "
            "Stale items were soft-deleted, not removed."
        )
    else:
        print(f"Dry run: {len(changed)} pack(s) need changes, nothing was written.")
        if structural:
            print("Re-run with --apply to write them.")
    if content_only and show_content:
        print(
            f"{content_only} pack(s) also have text changes on disk. "
            "Add --update-content to rewrite those items."
        )


async def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcile seeded collections with the content in collections/, "
            "which the boot-time seed never re-reads."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the changes; without this flag the command is a dry run",
    )
    parser.add_argument(
        "--update-content",
        action="store_true",
        help=(
            "also rewrite items whose text changed on disk (overwrites any "
            "in-app edit to a seeded item); requires --apply"
        ),
    )
    parser.add_argument(
        "--only",
        metavar="SLUG",
        help="limit the run to one registry slug, e.g. editor or software-engineer",
    )
    args = parser.parse_args()

    if args.update_content and not args.apply:
        parser.error("--update-content requires --apply")
    if args.only is not None and args.only not in _known_slugs():
        parser.error(
            f"unknown pack slug {args.only!r}; known slugs: {', '.join(sorted(_known_slugs()))}"
        )

    session_factory = get_session_factory()
    async with session_factory() as session:
        report = await reconcile_seeded_collections(
            session,
            apply=args.apply,
            update_content=args.update_content,
            only=args.only,
        )

    if report.root_error:
        print(f"error: {report.root_error}", file=sys.stderr)
        sys.exit(1)

    _print_report(report, show_content=not args.update_content)


if __name__ == "__main__":
    asyncio.run(main())
