---
name: Migration Safety
description: Checklist for shipping schema migrations that roll back cleanly and won't lock up a production table.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [database, migrations, schema]
---
## Purpose

A schema migration is one of the few changes in a backend codebase that's genuinely hard to undo once it's run against production data. This skill is a checklist for writing migrations that are safe to ship: they roll back cleanly, they don't quietly lock a hot table, and they never get hand-edited after the fact.

## When to use it

Every time a change requires adding, altering, or removing a table, column, index, or constraint — not just for "big" migrations. Small migrations cause outages just as often as big ones; the discipline should be automatic, not reserved for changes that look risky.

## The working-rollback requirement

- Write `downgrade()` (or your migration tool's equivalent) at the same time as `upgrade()`, not as a stub to fill in later.
- Actually run the rollback locally against a database that has the upgrade applied, and confirm the schema afterward matches pre-migration state. A `downgrade()` that's never been executed is unverified code, no different from an untested code path anywhere else.
- If a migration is genuinely irreversible (e.g. it drops a column and the data is gone), say so explicitly in the migration and think hard about whether that's really necessary now, versus deprecating the column first and dropping it in a later, separate migration once you're sure nothing needs it.

## Never edit a committed migration

- Once a migration has been merged (and especially once it's been applied anywhere outside your own branch), treat the file as immutable. If you find a mistake, write a new migration that corrects it — don't go back and change the original.
- Editing an already-applied migration means the migration history table (whatever tracks "which migrations have run") no longer matches what the file actually says, which silently desyncs anyone who already ran the old version from anyone running the edited one. This is one of the few migration mistakes that's genuinely hard to recover from cleanly.

## Locking and performance review

Before merging, ask what the migration actually does to the table at execution time, especially for tables that are large or under constant write load:

- Does it take a lock that blocks reads, writes, or both, and for how long — an instant metadata change, or a full table rewrite?
- Adding a nullable column is typically cheap. Adding a `NOT NULL` column with a default, adding an index without a "concurrent"/online mode, or changing a column type often are not — check what your specific database actually does for the operation you're using.
- For anything that would lock a large or busy table for more than a trivial amount of time, split it into additive, backward-compatible steps instead of one blocking change:
  1. Add the new column/constraint as nullable/not-yet-enforced.
  2. Backfill existing rows in batches (a separate script or migration, not one giant transaction).
  3. Tighten the constraint (`NOT NULL`, index, foreign key) once backfill is confirmed complete.
- Consider what happens if the migration runs while the *old* application code is still deployed (rolling deploys almost always have a window like this) — a migration that breaks the currently-running code mid-deploy is a self-inflicted outage.

## Expected output

A migration file with a real, exercised `downgrade()`, reviewed for its locking behavior against realistic table size, split into additive steps if a single-shot version would block production traffic, and never modified in place once it's been applied anywhere but your own local branch.
