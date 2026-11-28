# Plan: Pack Relationships, Version and "Updated" on the Pack Page

Status: **Planned — not started.** Found during a walk of the live pack page
(2026-11-28). Branch it separately from the content work.

## Problem

An add-on's relationship to other packs lives only in prose. "Layers on the
cloud-agnostic iac-expert collection" and "pair with a base pack" are in
descriptions; the pack page has no "requires" or "works well with", no
indication of when a pack last changed, and no version. Someone composing a
setup finds out a cloud pack wanted `iac-expert` from a compile warning or a
dangling handoff, after the fact. The collision preview (`lib/collisions.ts`)
covers name clashes, not missing companions.

## Goals

1. The pack page says what a pack **layers on** (hard-ish dependency) and what
   it **pairs with** (suggestion), with links.
2. Adding a pack to a setup warns, softly, when its `layers_on` pack is missing.
3. The page shows a real "last updated" and which release last changed it.

Non-goals: enforcing dependencies (advisory only, like `handoff_to`, rule 34);
user-authored relationship editing in v1; per-pack changelogs.

## Design

### Data
- New nullable `Collection.relations` JSON-text column (migration, reversible,
  rule 2): `{"layers_on": ["<slug>"], "pairs_with": ["<slug>"]}`. Slugs, not
  ids, because ids differ per deployment; the API resolves them to the
  deployment's `seed://` collections and drops any it cannot find.
- Source of truth for seeded packs: two optional keys in the registry entries
  in `seed_collections.py`. `iac-expert` for the four cloud packs;
  `software-engineer`/`devops-engineer` as `pairs_with` where it is true.
  Seeding sets it on create; the reconcile metadata option (see "Prerequisite")
  keeps it current.
- "Updated": add `Collection.content_updated_at` (nullable datetime) stamped by
  seeding and by reconcile when it changes a pack's items. Release: registry
  `since` is overkill; instead show the app version that was running at stamp
  time (`settings.app_version`), stored in `content_updated_in`.

### API
- Add `relations` (resolved to `{id, name, slug}` lists), `content_updated_at`
  and `content_updated_in` to the public community detail and `CollectionRead`.
  Additive, within `/api/v1/`. Mirror in the MCP `get_pack` output (ADR-0018:
  the MCP only wraps backend routes, so this is a passthrough).

### Frontend
- `PackDetail` Overview: a "Works with other packs" card — "Layers on: X"
  (links; amber note if the viewer's selected setup lacks it) and "Pairs well
  with: Y, Z". "Updated <date> (v2.3.0)" next to "used N times".
- `AddToSetup`: when `layers_on` is not in the setup, show a non-blocking
  notice offering to add it. Never block (rule 42: the user decides).
- Query keys per rule 12; reuse `packHref()`/`packSource()` from `lib/packs.ts`.

## Prerequisite

Reconcile must be able to update pack metadata (name, category, description,
relations): today it rewrites items only (rule 25), so seeded pack descriptions
drift from the registry. Build that first (an `--update-metadata` option with a
dry-run diff). Without it `relations` only reaches fresh installs.

## Tests

- Backend: migration up/down; registry → rows; unresolved slug dropped; public
  detail returns `relations` only for approved packs (rule 43 visibility).
- Frontend: PackDetail renders both lists and nothing when empty; AddToSetup
  notice appears and never disables the button.

## Open questions

- Is `pairs_with` worth curating, or only `layers_on`? Start with `layers_on`.
- Show the version for user-published packs, where there is no release?
  Probably only the date.
