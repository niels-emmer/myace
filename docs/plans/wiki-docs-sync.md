# Feature: Publish docs/ to the GitHub Wiki, Auto-Synced

## Overview

`docs/` already contains ~13,000 words of real documentation (architecture,
data model, invariants, extending guide, debugging guide, 6 ADRs, adapter
research). The GitHub Wiki is a better landing surface for it than browsing
raw files in a repo — it gets its own nav, its own search, and shows up as a
distinct tab most visitors check before cloning. This plan publishes that
content to the Wiki **without** creating a second, driftable copy: `docs/`
stays the single source of truth (edited in the same PR as code, per
[AGENTS.md rule 14](../../AGENTS.md)), and the Wiki becomes a generated
mirror, pushed by CI on every merge to `main`. Nobody hand-edits the Wiki.

Context: the Wiki is currently disabled (`has_wiki: false`) — it was turned
off because it was empty. Step 1 re-enables it.

## Why not just hand-maintain the Wiki

The Wiki is its own git repo (`niels-emmer/myace.wiki.git`) with no CI, no
branch protection, and no review — anyone editing it directly bypasses
`AGENTS.md` rule 14 immediately, and at this repo's merge cadence
(~20 PRs/day some days) the two copies would be visibly stale within a week.
The only durable version of "keep docs up to date" here is: one source of
truth, one automated one-way sync.

## Scope: which docs go to the Wiki

Human-facing, not agent-facing — the Wiki is for people evaluating or
contributing to the project, not for the AI-agent rule files.

| Source | Wiki page | Include? |
|---|---|---|
| `docs/architecture.md` | `Architecture` | Yes |
| `docs/data-model.md` | `Data-Model` | Yes |
| `docs/invariants.md` | `Invariants` | Yes |
| `docs/extending.md` | `Extending-MyACE` | Yes |
| `docs/debugging.md` | `Debugging` | Yes |
| `docs/adr/*.md` | `ADR-000N-slug` (one page per ADR) | Yes |
| `docs/ADAPTERS_RESEARCH.md` | `Adapter-Research` | Yes |
| `docs/README.md` | becomes the Wiki `Home` page (rewritten) | Yes, transformed |
| `docs/plans/*.md`, `docs/plan-*.md` | — | No — these are point-in-time design records, not reference docs; keep them repo-only |
| `AGENTS.md` / `CLAUDE.md` | — | No — agent-facing, not for Wiki visitors |
| `docs/images/*.png` | same filenames | Yes — copied alongside |

## Implementation

### 1. Re-enable the Wiki
`gh api -X PATCH repos/niels-emmer/myace -F has_wiki=true` (one-line revert
of the earlier disable).

### 2. Sync script
`scripts/sync_wiki.py` (or `.sh`) — pure transform + git push, no new
runtime dependency:
1. Clone `https://x-access-token:${GITHUB_TOKEN}@github.com/niels-emmer/myace.wiki.git`
   into a temp dir (create if it doesn't exist yet — GitHub lazily
   initializes the wiki repo on first push).
2. Copy the included files per the scope table above into the wiki clone,
   renaming to Wiki page-name conventions (spaces/slashes → `-`).
3. Rewrite relative links (`[invariants](invariants.md)` →
   `[invariants](Invariants)`) and image paths so they resolve inside the
   Wiki's flat namespace.
4. Generate `_Sidebar.md` (nav: Home, Architecture, Data Model, Invariants,
   Extending, Debugging, ADRs submenu, Adapter Research) and `_Footer.md`
   (link back to the repo + "auto-generated, edits go through `docs/`, see
   CONTRIBUTING").
5. `git add -A && git commit -m "sync from <main SHA>" && git push` — no-op
   commit if nothing changed.

### 3. GitHub Action
`.github/workflows/wiki-sync.yml`, triggered on `push` to `main` with a
`paths:` filter on `docs/**`, plus `workflow_dispatch` for manual re-runs.
Runs after the existing CI workflow's other jobs (or independently — it only
touches the wiki repo, never `main`, so it doesn't need to gate on anything).
Uses the default `GITHUB_TOKEN` (wiki push just needs repo write, which the
default token already has for same-repo workflows).

### 4. Guardrail against drift
Add a short section to `AGENTS.md` rule 14 (Documentation Maintenance)
stating: the Wiki is a generated mirror of `docs/`, published by
`.github/workflows/wiki-sync.yml` — never edit Wiki pages directly, edit
`docs/` and let CI publish it. This is the same "fix the doc in the PR that
changes the behavior" discipline already in that rule, just naming the new
downstream target.

### 5. Test
1. Run the sync script locally against a scratch clone of the wiki repo
   first, to check link rewriting and sidebar generation before wiring it
   to CI.
2. Merge a trivial `docs/` change, confirm the Action fires and the Wiki
   page updates within the run.
3. Confirm Wiki search finds content (GitHub indexes Wiki pages
   separately from repo code).

## Out of scope / explicitly not doing
- Two-way sync (Wiki → docs/) — the Wiki is push-only, read-only for humans.
- Hosting a full docs site (mkdocs/Docusaurus on the `myace.macjuu.com`
  domain) — bigger lift, different epic, revisit only if Wiki traffic
  suggests it's worth it.
- Syncing `docs/plans/*.md` or `AGENTS.md`/`CLAUDE.md` — out of scope per
  the table above.

## Rough sizing
Content already exists, so this is almost entirely plumbing: script +
Action + one AGENTS.md edit + testing. Roughly a single half-day PR, not a
multi-week epic.
