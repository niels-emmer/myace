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

from app.core.database import get_session_factory
from app.services.seed_reconcile import ReconcileReport, reconcile_seeded_collections


def _print_report(report: ReconcileReport, *, show_content: bool) -> None:
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
            print(f"  + add:      {', '.join(sorted(pack.added))}")
        if pack.removed:
            print(f"  - remove:   {', '.join(sorted(pack.removed))}")
        if pack.duplicates_removed:
            print(f"  - duplicate: {', '.join(sorted(pack.duplicates_removed))}")
        if pack.content_updated:
            print(f"  ~ updated:  {', '.join(sorted(pack.content_updated))}")
        if show_content and pack.content_changed:
            print(f"  ~ differs:  {', '.join(sorted(pack.content_changed))} (not applied)")
        print()

    packs = f"{len(changed)} pack(s)"
    if report.applied:
        print(f"Applied to {packs}. Stale items were soft-deleted, not removed.")
    else:
        print(f"Dry run: {packs} need changes, nothing was written. Re-run with --apply.")
        if any(pack.content_changed for pack in changed):
            print("Add --update-content to also rewrite those items' text.")


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

    session_factory = get_session_factory()
    async with session_factory() as session:
        report = await reconcile_seeded_collections(
            session,
            apply=args.apply,
            update_content=args.update_content,
            only=args.only,
        )

    _print_report(report, show_content=not args.update_content)


if __name__ == "__main__":
    asyncio.run(main())
