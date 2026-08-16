# Plan: Platform Enhancements (Validation, Sync, Orchestration, Trust)

**Status: Complete.** All 4 phases (9 features) built, one branch/PR per
phase as specified below: Phase 1 ([#109](https://github.com/niels-emmer/myace/pull/109)),
Phase 2 ([#110](https://github.com/niels-emmer/myace/pull/110)), Phase 3
([#111](https://github.com/niels-emmer/myace/pull/111)), Phase 4
([#112](https://github.com/niels-emmer/myace/pull/112)) — each squash-merged
to `main` in order after a 4-angle code-review pass and a full green
test/lint/typecheck run. Backend 330 tests, CLI 81 tests, frontend 49
tests, all passing on `main` post-merge. Version bumped to 1.8.0. See each
PR's description for its epic-by-epic detail, and the conversation that
built this for the specific bugs the review passes caught (a
name-vs-ID collision-detection bug in Phase 1, a `watch --auto-pull`
manifest-integrity bug in Phase 2, and a missing transport-level body-size
cap on the new public demo endpoint in Phase 4, among smaller fixes).

One known follow-up, not yet done: Phase 3's `handoff_to` frontmatter
added to the `software-engineer` starter-pack agents will not reach an
already-seeded deployment (including this project's own VPS) without a
manual reseed — `seed_starter_collections()` only seeds a collection once
(see AGENTS.md rule 25 and docs/debugging.md's matching entry).

## Overview

Nine features, grouped into four independent phases:

| # | Feature | Persona | Phase |
|---|---|---|---|
| 9 | Compile-time cross-artifact validation | General | **Phase 1 — Validation** |
| 1 | Drift & Sync Dashboard | Multi-IDE users | **Phase 2 — Sync** |
| 2 | `myace watch` live-sync mode | Multi-IDE users | **Phase 2 — Sync** |
| 10 | CI drift-check Action (`myace-check`) | Teams | **Phase 2 — Sync** |
| 3 | Orchestration Recipe Gallery + flow visualizer | Orchestration-curious | **Phase 3 — Orchestration** |
| 4 | "Compose your pipeline" wizard | Orchestration-curious | **Phase 3 — Orchestration** |
| 5 | Setup Health-Check / Audit Report | "What does this do for me" | **Phase 4 — Trust** |
| 6 | Live before/after demo on landing page | "What does this do for me" / acquisition | **Phase 4 — Trust** |
| 7 | Automated freshness/staleness checker | Differentiation vs. static lists | **Phase 4 — Trust** |

## How to use this document

Unlike `community-enhancements.md`, **this plan is four separate branches,
not one.** The seven requirements in that plan were tightly interdependent
(role model → moderation state machine → everything else); these 9 features
are largely orthogonal, span unrelated subsystems, and bundling them into
one branch would produce an unreviewable PR and couple unrelated risk (a
bug in the orchestration wizard would block shipping the CI Action). Build
and merge the phases **in the order below** — each has its own branch, its
own PR, its own review, and can ship independently once its epics are done.
Within a phase, commit one epic at a time, same convention as before.

**Sequencing rationale:** Phase 1 (validation) is smallest and is a
dependency for Phase 3 (the orchestration gallery's dangling-reference
check reuses Phase 1's warnings plumbing). Phase 2 (sync) is independent
but benefits from Phase 1 shipping first (`myace check` can surface compile
warnings alongside drift). Phase 4 (trust) is last and is mostly
independent, except one sub-feature (freshness re-verification) that
assumes the `moderator` role exists — see that phase's notes for the
fallback if `docs/plans/community-enhancements.md` hasn't shipped yet.

## Decisions made while planning

No build-blocking product ambiguity came up for this set (unlike
community-enhancements, which needed five user calls) — these are mostly
new, additive capabilities without a legacy behavior to reconcile. A few
implementation calls were made and are flagged here so the build doesn't
re-litigate them:

- **Drift detection is manifest-based, not a new source of truth.** `pull`
  starts writing a local manifest file recording what it wrote and its
  hash; there is no existing lockfile/manifest concept to build on (CLI
  `pull` currently writes only the compiled files themselves — confirmed
  via research). This is a new, additive file, not a change to existing
  `pull` output.
- **Sync-status "phone home" to the dashboard is opt-in per invocation**
  (`--report` flag on `myace check`/`watch`), never automatic — a CLI tool
  silently reporting a user's local file state to a server by default
  would be a privacy regression worth avoiding without asking first.
- **Agent handoffs become a structured frontmatter field
  (`handoff_to: list[str]`), not prose-parsing.** The existing
  `orchestrator.md` only expresses routing in a "## Handoff" prose section
  — parsing free text to build a flow diagram or validate references would
  be fragile. A new optional Canonical IR field is added instead, and the
  existing starter-pack orchestration agents are updated to declare it as
  part of Phase 3 (content change, not just schema).
- **The public demo endpoint (Phase 4) is scoped to pasted rule-type
  markdown only — no file upload, no git URL, nothing persisted.** No
  fully-public, unauthenticated route exists anywhere in the backend today
  and no rate-limiting middleware exists at all — both are new attack
  surface. Scoping the input to "one pasted `AGENTS.md`-shaped text block,
  parsed with the same `_parse_agents_md` used elsewhere, rendered through
  existing adapters, nothing written to the DB" keeps the new surface
  small and reuses already-trusted parsing code instead of adding a new
  parser.
- **The "freshness checker" is manual attestation + expiry reminders, not
  automated content diffing against external tool docs.** Reliably
  detecting "does this collection's advice still match tool X's current
  behavior" would require scraping and diffing each target tool's live
  documentation — fragile, high false-positive risk, and really its own
  R&D project. Scoped down to something an unattended build can actually
  deliver: collections get a `last_verified_at` date a moderator/admin
  sets by hand, a scheduled job flags anything older than a threshold, and
  that's surfaced as a queue + a badge. Automation here means "automated
  reminder," not "automated verification" — say so in the UI copy too, not
  just internally, so it doesn't overclaim.

## New dependencies

| Package | Where | Why | License |
|---|---|---|---|
| `watchfiles` | `cli/` | Filesystem watching for `myace watch` — no such library exists in the CLI today | Apache-2.0 |
| `slowapi` | `backend/` | Rate limiting — no rate-limiting middleware exists anywhere in the backend today, and Phase 4 adds the first fully-public unauthenticated route | MIT |
| `@xyflow/react` (React Flow) | `frontend/` | Flow-diagram rendering — no diagram/graph library exists in the frontend today (checked `package.json`) | MIT |

## Preflight checks (do once, before Phase 1)

- Confirm the current Alembic head (`alembic heads` in `backend/`) —
  multiple phases add migrations; don't guess `down_revision`.
- Check `ls docs/adr/` for the actual next free ADR number before writing
  any ADR in this plan — if `community-enhancements.md` (which reserves
  0007/0008) has shipped by the time a phase here reaches its docs epic,
  start numbering after that instead of assuming 0007.
- Confirm `POST /collections/{id}/artifacts` (or equivalent) already
  exists as the artifact-create endpoint the orchestration wizard (Phase
  3) will reuse — research assumed it exists (ImportPage/scanner push
  artifacts through *something*) but didn't pin the exact route.

---

## Phase 1 — Compile-Time Validation

**Branch:** `feat/compile-validation`

### Overview
Surface two classes of problems that exist today but are silently
swallowed or left to a human running a documented `grep` (`AGENTS.md` rule
29): artifact name collisions across composed collections, and (once
Phase 3 adds it) dangling agent-handoff references.

### Architecture decision
`compile_profile()` gains a `warnings: list[ValidationIssue]` field,
additive to its existing `{profile_id, profile_name, target,
artifact_count, files}` return shape — existing consumers that only read
`files` are unaffected. `ValidationIssue = {level: "warning", code: str,
message: str}`. This plumbing is the foundation Phase 2 and Phase 3 both
build on, which is why it ships first.

### Epic 1.1: Backend — warnings plumbing + name-collision rule
**Files:** `backend/app/services/compiler.py`, `backend/app/schemas/` (or
wherever `ProfileCompileResponse` lives), `backend/app/api/profiles.py`

**Tasks:**
1. Define `ValidationIssue` Pydantic model.
2. In `compile_profile()`'s existing dedup step (step 4 per its
   docstring), track every `(name, artifact_type)` seen per source
   collection; when a later collection overrides an earlier one, emit a
   `name_collision` warning naming both collections and which one won.
3. Add `warnings` to the compile response schema and to
   `POST /profiles/compile`'s JSON body.
4. `POST /profiles/compile/zip`: append a `_myace_warnings.txt` file
   inside the zip listing any warnings when present (can't embed JSON
   warnings in a zip's HTTP response body the way the JSON route can).
5. Tests: two collections in one profile sharing an artifact name
   produces exactly one `name_collision` warning with both collection
   names in the message; zero warnings when no collisions exist; zip
   route includes `_myace_warnings.txt` only when warnings exist.

**Commit:** `feat: surface compile-time validation warnings`

### Epic 1.2: CLI — display warnings, `--strict` flag
**Files:** `cli/myace_cli/main.py`, `cli/myace_cli/sync.py`

**Tasks:**
1. `SyncEngine.pull_profile()` parses the new `warnings` field from the
   compile response.
2. `pull` prints warnings (yellow, Rich) after the file table, doesn't
   block by default.
3. New `--strict` flag on `pull`: exit code 1 if any warnings are
   present (after files are still written — strict mode flags, doesn't
   prevent the pull, since the compiled output is still valid, just
   worth a human look).
4. Tests: `pytest-httpx`-mocked compile response with warnings renders
   and exits correctly with/without `--strict`.

**Commit:** `feat: display compile warnings in CLI, add --strict flag`

### Epic 1.3: Frontend — warnings panel on compile page
**Files:** `frontend/src/pages/TargetExporter.tsx`, `frontend/src/lib/api.ts`, `frontend/src/types/index.ts`

**Tasks:**
1. Add `warnings` to the frontend compile-response type.
2. Render a dismissible warnings panel above the file output when
   present (amber, not red — these are advisory, not errors).
3. Manual verification: compile a profile with two collections sharing
   an artifact name, confirm the panel appears with both collection
   names.

**Commit:** `feat: show compile warnings in TargetExporter UI`

### Epic 1.4: Docs
**Files:** `docs/data-model.md` (note the warnings field isn't persisted, it's response-only), `AGENTS.md` (add a numbered rule pointing at this mechanism, and update rule 29 to reference it instead of only describing the manual `grep` workaround)

**Commit:** `docs: document compile-time validation warnings`

---

## Phase 2 — Sync & Drift Tooling

**Branch:** `feat/sync-drift-tooling`

### Overview
Three features sharing one primitive: knowing whether a locally-pulled
target directory still matches what the source profile would compile
*right now*, and whether it's been hand-edited since pull.

### Architecture decisions

**Compiled-output hashing.** Add a `compiled_hash` field to the compile
response: `sha256` over a deterministic serialization of the `files` dict
(sort by filename, concatenate `filename\0content\0`, hash the result).
Follows the existing `content_hash` precedent in
`backend/app/services/doc_verifier.py`/`DocCacheEntry` — same primitive,
new call site.

**Local manifest, not a new server-side source of truth.** `pull` writes
a `.myace/<target>.manifest.json` file (new `.myace/` directory alongside
whatever it just wrote) containing `{profile_id, profile_name, target,
compiled_hash, pulled_at, files: {filename: sha256(content)}}`. This is
what `myace check`/`watch` diff against — no new state on the server is
required just to detect local drift; the server is only consulted to get
the *current* `compiled_hash` for the staleness half of the check.

**A cheap hash-only endpoint**, not a full recompile, for `check`/`watch`
to poll: `GET /api/v1/profiles/{id}/compile-status?target=X` returns just
`{compiled_hash, updated_at}` — avoids paying full `translate()` cost on
every drift check, especially under `watch`'s timer loop.

**Sync-status dashboard is opt-in reporting**, per the Decisions section
above — nothing is sent to the server unless the user passes `--report`.

### Epic 2.1: Backend — compile-status endpoint + hash
**Files:** `backend/app/services/compiler.py`, `backend/app/api/profiles.py`

**Tasks:**
1. `compute_compiled_hash(files: dict[str, str]) -> str` helper.
2. Add `compiled_hash` to the full compile response (Phase 1's schema).
3. New `GET /profiles/{id}/compile-status?target=X` — same authz as
   `/compile` (owner or public profile), returns `{compiled_hash,
   updated_at}` without running the full adapter `translate()` where
   avoidable (still needs to gather artifacts + resolve overrides to
   compute the hash accurately — this endpoint saves the *serialization*
   cost, not necessarily the artifact-gathering cost; note this
   trade-off in the docstring, don't oversell it as free).
4. Tests: hash is stable for identical input, changes when any file
   content changes, endpoint 404s same as `/compile` for unauthorized
   profiles.

**Commit:** `feat: add compiled-output hashing and compile-status endpoint`

### Epic 2.2: CLI — manifest writing on `pull`
**Files:** `cli/myace_cli/main.py`, `cli/myace_cli/sync.py`

**Tasks:**
1. After writing files, write `.myace/<target>.manifest.json` with the
   shape described above. Create `.myace/` if absent; add a
   `.myace/` entry suggestion to the task output ("add `.myace/` to your
   `.gitignore` if you don't want to commit sync manifests" — this is
   local tooling state, not something to force into version control,
   but don't decide the user's `.gitignore` for them, just suggest it).
2. Tests: manifest content matches what was actually written; re-running
   `pull` overwrites the manifest, doesn't append.

**Commit:** `feat: write local sync manifest on pull`

### Epic 2.3: CLI — `myace check`
**Files:** `cli/myace_cli/main.py`, `cli/myace_cli/sync.py`

**Tasks:**
1. New command `myace check [--target NAME | --all] [--json] [--report]`.
   Locates manifest(s) (specific target, or all `.myace/*.manifest.json`
   in cwd). For each: recompute local file hashes, diff against
   manifest → `locally_modified: list[str]`; call the new
   `compile-status` endpoint → diff `compiled_hash` against manifest's
   stored value → `stale: bool`.
2. Human-readable Rich table by default; `--json` for machine-readable
   output (consumed by the Phase 2.5 CI Action).
3. Exit code 0 only if every checked target is fully in sync; 1
   otherwise.
4. `--report`: after checking, `POST /api/v1/sync/report` (Epic 2.4)
   with the result, only when this flag is passed.
5. Tests: in-sync manifest → exit 0; hand-edited file → `locally_modified`
   populated, exit 1; server hash changed → `stale: true`, exit 1;
   `--report` calls the report endpoint only when passed.

**Commit:** `feat: add myace check command for drift detection`

### Epic 2.4: Backend + Frontend — Sync Dashboard
**Files:** `backend/app/models/sync_status.py` (new), `backend/app/api/sync.py` (new), `backend/alembic/versions/`, `frontend/src/pages/SyncDashboard.tsx` (new), `frontend/src/components/Layout.tsx`, `frontend/src/App.tsx`

**Tasks:**
1. New `SyncStatus` model: `id` (uuid), `user_id` (FK), `profile_id`
   (FK), `target`, `machine_label` (free text, user-supplied or
   hostname), `in_sync: bool`, `locally_modified_files: str` (JSON text,
   same pattern as `Artifact.tags` — convert through a read schema per
   rule 11, never return the raw row), `last_checked_at`. Unique
   constraint on `(user_id, profile_id, target, machine_label)` —
   upsert on report.
2. `POST /api/v1/sync/report` — `Depends(get_current_user)`, upserts the
   caller's own row (ownership always from `current_user.id`, never a
   client-supplied user id, per rule 13).
3. `GET /api/v1/sync/status` — lists only the caller's own rows (no
   cross-user visibility — this is local machine state, not a community
   feature).
4. `SyncDashboard.tsx` at `/sync`: table of profile / target / machine /
   status / last-checked, with a hint ("run `myace pull`" for stale,
   "review your local edits" for locally-modified). Nav item for all
   authenticated users (not admin-gated — this is personal data).
5. Tests (backend): report upserts rather than duplicates; a user
   cannot see another user's `SyncStatus` rows.

**Commit:** `feat: add sync status reporting and dashboard`

### Epic 2.5: CLI — `myace watch`
**Files:** `cli/myace_cli/main.py`, `cli/pyproject.toml`

**Tasks:**
1. Add `watchfiles` dependency.
2. `myace watch [--target NAME | --all] [--interval SECONDS=300] [--auto-pull] [--report]`:
   watches manifest-covered directories for filesystem events (catches
   local edits promptly) and also polls on the interval (catches
   server-side changes, which aren't local fs events). On each trigger,
   runs the same logic as `check`. If `stale` and `--auto-pull`, re-runs
   `pull` for that target. If `locally_modified`, only warns — **never**
   silently overwrites local hand-edits, `--auto-pull` or not.
3. Tests: mock the watch loop's single iteration logic (don't test the
   actual `watchfiles` event loop end-to-end — assert the
   check-then-maybe-pull decision function directly).

**Commit:** `feat: add myace watch for continuous drift monitoring`

### Epic 2.6: CI drift-check Action
**Files:** `.github/actions/myace-check/action.yml` (new composite action, this repo hosts and documents it), `docs/` (new usage doc, e.g. `docs/ci-drift-check.md`)

**Tasks:**
1. Composite action (template: `.github/workflows/wiki-sync.yml`'s
   minimal shape) that installs `myace-cli`, runs
   `myace check --all --json` against a repo's committed compiled output,
   and fails the job on drift. Inputs: `server-url`, `token` (secret).
2. This is **not** wired into MyACE's own CI — this repo's `collections/`
   directory is canonical source, not compiled output, so there's
   nothing here to dogfood it against. It's a distributable artifact for
   *other* repos that consume MyACE-compiled configs.
3. Write `docs/ci-drift-check.md`: how another repo adds this to its own
   `.github/workflows/`, with a copy-pasteable example workflow snippet.
4. Link this doc from `README.md`'s feature list.

**Commit:** `feat: add distributable CI drift-check GitHub Action`

### Epic 2.7: Docs
**Files:** `docs/adr/00XX-manifest-based-drift-detection.md` (new — this is ADR-worthy: introduces a new client-side state file and a new data flow for the sync dashboard, non-trivial to reverse once users depend on it), `docs/data-model.md` (`sync_status` table), `docs/invariants.md` (sync reporting is always self-scoped to `current_user.id`), `AGENTS.md` (new rule describing the manifest format + the compile-status endpoint's cost trade-off), `README.md` (feature list)

**Commit:** `docs: document sync/drift tooling; bump version`

---

## Phase 3 — Orchestration UX

**Branch:** `feat/orchestration-ux`

### Overview
Make the multi-agent pipeline pattern that already exists
(`orchestrator.md`) discoverable, visualizable, and composable by someone
who's never hand-written agent routing logic before.

### Architecture decision
Add `handoff_to: list[str] | None` to the Canonical IR (new optional
frontmatter field on agent artifacts) — JSON-text column on `Artifact`,
same storage pattern as `tags`/`target_compatibility` (rule 11: always
convert through `_artifact_to_read()`/`_db_to_canonical()`, never return
the raw row). This is a Canonical IR schema change — write it up as an
ADR in this phase's docs epic (claim the next free number per the
preflight check).

### Epic 3.1: Backend — `handoff_to` field
**Files:** `backend/app/models/artifact.py`, `backend/app/services/scanner.py` (`_parse_agent_file`), `backend/app/services/compiler.py`, `backend/alembic/versions/`

**Tasks:**
1. Migration: add `handoff_to` text column (nullable) to `artifacts`.
2. `Artifact.handoff_to: list[str] | None`, `CanonicalArtifact` too;
   expose on `ArtifactRead` via the existing JSON-decode conversion
   path (rule 11).
3. `_parse_agent_file` reads an optional `handoff_to: [...]` frontmatter
   key.
4. Extend Phase 1's validation: for every compiled agent artifact with
   non-empty `handoff_to`, check each referenced name exists in the
   compiled artifact set; emit a `dangling_handoff` `ValidationIssue` if
   not. (Small addition to `compile_profile()`'s existing warnings step
   from Phase 1 — don't duplicate the plumbing.)
5. Tests: valid handoff chain produces no warning; a `handoff_to`
   referencing a nonexistent agent name produces exactly one
   `dangling_handoff` warning.

**Commit:** `feat: add handoff_to field to agent artifacts`

### Epic 3.2: Content — declare handoffs in starter collections
**Files:** `collections/base/software-engineer/agents/orchestrator.md`, `builder.md`, `verifier.md`, `security-auditor.md`, `code-reviewer.md`, `docs-writer.md` (whichever of these exist as separate agent files — confirm the actual set under `collections/base/software-engineer/agents/`)

**Tasks:**
1. Add `handoff_to:` frontmatter to each pipeline agent reflecting the
   existing prose "## Handoff" section's actual routing (builder →
   verifier → security-auditor (conditional) → code-reviewer →
   docs-writer, per the orchestrator's own routing logic) — this is a
   metadata addition, the prose stays as human-readable documentation,
   the frontmatter becomes the machine-readable version of the same
   fact. Keep them consistent; don't let them drift.
2. Verify starter-pack re-seeding picks up the change (`seed_starter_collections()` re-parses on next backend start — per rule 25, idempotent by `(name, is_starter_pack)`, but content updates need to actually get re-synced; check whether existing artifact rows get updated on a content change or only created-if-missing, and if it's the latter, note that in the docs epic as a known limitation rather than silently shipping a no-op content update).

**Commit:** `feat: declare handoff_to in starter-pack orchestration agents`

### Epic 3.3: Frontend — Orchestration Recipe Gallery
**Files:** `frontend/src/pages/OrchestrationGallery.tsx` (new), `frontend/package.json`, `frontend/src/components/Layout.tsx`, `frontend/src/App.tsx`

**Tasks:**
1. Add `@xyflow/react` dependency.
2. New page at `/orchestration`: lists agents with `mode: primary` and
   non-empty `handoff_to` across the user's collections (and community
   collections) as gallery cards; selecting one renders a flow diagram
   (nodes = agents in the chain, edges = handoff direction) built
   entirely client-side from already-available artifact data — no new
   backend endpoint needed beyond Epic 3.1's exposed field.
3. Nav item, visible to all authenticated users.
4. Manual verification: browse to the gallery, find the
   software-engineer orchestrator, confirm the diagram matches the
   actual builder→verifier→security-auditor→code-reviewer→docs-writer
   chain.

**Commit:** `feat: add orchestration recipe gallery with flow visualizer`

### Epic 3.4: Frontend — "Compose your pipeline" wizard
**Files:** `frontend/src/pages/OrchestratorBuilder.tsx` (new), `frontend/src/lib/api.ts`, `frontend/src/App.tsx`

**Tasks:**
1. New page at `/orchestration/build`: pick a profile, see its available
   agents, reorder them into a sequence (simple linear chain for v1 —
   conditional branching like the security-relevance check is a
   documented non-goal for this wizard, call it out explicitly rather
   than half-implementing it), preview the resulting flow diagram
   (reuse Epic 3.3's diagram component), then generate a new agent
   artifact: frontmatter (`mode: primary`, `handoff_to` reflecting the
   chosen order) + an auto-generated body with a "## Handoff" section
   listing the sequence in prose (mirrors Epic 3.2's pattern so
   generated agents look like hand-written ones).
2. Save flow: user picks (or the confirmed-in-preflight endpoint
   creates) one of their own collections to save the new orchestrator
   artifact into.
3. Manual verification: build a 3-step pipeline from an existing
   profile's agents, save it, confirm it appears correctly in the
   Gallery.

**Commit:** `feat: add pipeline composition wizard`

### Epic 3.5: Docs
**Files:** `docs/adr/00XX-structured-handoff-field.md` (new), `docs/data-model.md`, `README.md`

**Commit:** `docs: document orchestration UX; bump version`

---

## Phase 4 — Trust & Onboarding

**Branch:** `feat/trust-onboarding`

### Overview
Three loosely-related features that all answer "why should I trust/use
this": an audit of your actual local setup, a zero-friction public demo,
and an honest (manual-attestation-based) freshness signal on community
content.

### Epic 4.1: Backend — adapter `expected_paths()` + companion-server `/audit`
**Files:** `backend/app/adapters/base.py`, all 11 adapter files, `cli/myace_cli/local_server.py`, `cli/myace_cli/scanner.py`

**Tasks:**
1. Add `expected_paths(self) -> list[str]` to `BaseAdapter` — each
   adapter returns its conventional local file/directory names (e.g.
   claude-code → `["CLAUDE.md", ".claude/"]`, cursor → `[".cursor/"]`).
   Implement for all 11 adapters.
2. New `POST /audit` on `local_server.py`, **same security model as the
   existing `/scan` route** (loopback-only, `X-MyACE-Companion` header,
   Origin check, PNA preflight — rule 24's guardrails apply here too,
   don't relax any of them for the new route). Given a root path, scans
   every adapter's `expected_paths()` location that exists, runs the
   existing `scan_directory()`-style parsers against each, and returns
   per-target artifact lists.
3. New scoring/comparison logic (entirely new — nothing like this
   exists yet): for the returned per-target artifact lists, compute (a)
   coverage gaps — an artifact name present in one target's directory
   but absent from another's, (b) within-target duplicate names, (c) a
   simple 0–100 score (e.g. weighted: coverage parity across detected
   targets, no duplicates, non-zero artifact count). Keep the scoring
   formula simple and documented inline — this is a rough signal, not a
   certified metric, and the UI copy should say so.
4. Tests: two target dirs with divergent artifact sets produce the
   expected gap list; identical sets produce zero gaps and a full
   coverage score.

**Commit:** `feat: add local setup audit to companion server`

### Epic 4.2: Frontend — Setup Audit page
**Files:** `frontend/src/pages/SetupAudit.tsx` (new, or a new tab on `ImportPage.tsx` — check which reads better given `ImportPage.tsx` already talks to the companion server for scans), `frontend/src/App.tsx`

**Tasks:**
1. Calls the companion server's `/audit` directly (same pattern as
   `ImportPage.tsx`'s existing scan calls) — polls `/health` first,
   shows the same "companion server not running" setup panel
   `ImportPage.tsx` already has if unreachable, don't reinvent that.
2. Renders the score, gap list, and duplicate list with plain-language
   explanations ("Cursor is missing 2 rules that Claude Code has").
3. Manual verification: run against a machine with at least two tool
   configs present, confirm gaps are reported correctly.

**Commit:** `feat: add setup audit page`

### Epic 4.3: Backend — public demo compile endpoint
**Files:** `backend/app/api/demo.py` (new), `backend/pyproject.toml`, `backend/app/main.py`

**Tasks:**
1. Add `slowapi` dependency; configure a rate limiter scoped to this
   route only (e.g. 10 requests/minute/IP) — don't apply it globally,
   every other route keeps its existing (auth-based) protection.
2. `POST /api/v1/demo/compile` — **no** `Depends(get_current_user)**,
   the first fully-public route in the backend besides the documented
   auth-entry list, so call this out explicitly in the docs epic as a
   deliberate, reviewed exception to rule 13's "every route requires
   auth" pattern, not an oversight. Body: `{markdown: str}` capped at
   20KB (422 if larger). Parses with the existing `_parse_agents_md`
   parser (rule-type artifacts only — no skills/agents/model-configs,
   no git URLs, no file uploads), builds ephemeral in-memory
   `CanonicalArtifact` objects, runs them through 2–3 adapters
   (claude-code, cursor, opencode — a fixed small set, not all 11, to
   bound response size), returns the compiled previews. **Nothing is
   persisted** — no DB writes, no `owner_id`, stateless request/response.
3. Tests: valid markdown compiles; oversized input 422s; rate limit
   triggers on the 11th request in a minute from one IP; confirm no DB
   rows are created as a side effect.

**Commit:** `feat: add public demo compile endpoint`

### Epic 4.4: Frontend — landing page + live demo
**Files:** `frontend/src/pages/Landing.tsx` (new), `frontend/src/App.tsx` (new unauthenticated route, e.g. `/welcome`, and reconsider whether unauthenticated `/` should redirect here instead of straight to `/login` — check with a quick UX pass, not a big redesign)

**Tasks:**
1. New unauthenticated landing page: brief pitch (reuse
   `docs/architecture.md`'s existing "packages vs. lockfile" framing),
   and an embedded live demo widget — a textarea pre-filled with a
   short sample `AGENTS.md`, calling the Epic 4.3 endpoint on submit,
   showing 2–3 compiled outputs side by side.
2. Route unauthenticated visitors to `/welcome` instead of straight to
   `/login`; add a clear "Log in" / "Sign up" call to action from
   there.
3. Manual verification: as a logged-out visitor, load `/welcome`, edit
   the sample text, see live compiled output for multiple targets
   without ever authenticating.

**Commit:** `feat: add public landing page with live demo`

### Epic 4.5: Backend + Frontend — freshness expiry
**Files:** `backend/app/models/collection.py`, `backend/app/api/collections.py` (or a new small router), `backend/app/scripts/check_collection_freshness.py` (new), `backend/app/services/email.py`, `frontend/src/pages/CommunityCollections.tsx`, `frontend/src/pages/CommunityCollectionDetail.tsx`, `backend/alembic/versions/`

**Dependency note:** this epic's queue/verify actions are gated on
`role in ("moderator", "admin")`. **If `community-enhancements.md` hasn't
shipped yet** (no `role` column exists), gate on `is_admin` instead and
leave a `# TODO: switch to require_moderator_or_admin once the moderator
role ships` comment — don't block this phase on the other plan, and don't
duplicate a role column here either.

**Tasks:**
1. Migration: `Collection.last_verified_at: date | None`,
   `Collection.verified_by: uuid | None` (FK `users.id`, nullable).
2. `GET /admin/freshness-queue` (mod/admin, or admin-only per the
   dependency note) — collections where `last_verified_at IS NULL OR
   last_verified_at < today - threshold` (threshold configurable,
   default 6 months), oldest first.
3. `POST /collections/{id}/verify` (mod/admin) — sets
   `last_verified_at = today`, `verified_by = current_user.id`.
4. `backend/app/scripts/check_collection_freshness.py` — cron-invoked
   (weekly), counts collections past threshold, emails
   admins/moderators a digest via a new `build_freshness_digest_email`
   if count > 0 (same "email failure never blocks the DB operation"
   pattern used elsewhere — though here there's no DB operation to
   protect, just don't let a send failure crash the script for the next
   recipient).
5. Frontend: badge on community collection cards/detail —
   "Verified `{date}`" or "Needs re-check" (age > threshold) — with
   copy that's honest about what "verified" means (a human confirmed it
   recently, not "automatically checked against live tool docs").
6. Tests: queue correctly filters by threshold; verify sets both fields;
   digest script only emails when count > 0.

**Commit:** `feat: add collection freshness verification and expiry queue`

### Epic 4.6: Docs
**Files:** `docs/adr/00XX-public-demo-sandbox.md` (new — public unauthenticated route + new rate-limiting dependency is a security-relevant, non-trivial-to-reverse decision), `docs/data-model.md`, `docs/invariants.md` (new invariant: the demo endpoint never persists), `AGENTS.md` (new rule for the public-route exception + rate-limiter pattern, in case a future public route gets added), `docs/deployment.md` (cron entry for the freshness script, next to the community-enhancements digest cron if that's landed), `README.md`

**Commit:** `docs: document trust/onboarding features; bump version`

---

## Definition of Done (per phase)

- All epics committed in order on the phase's branch.
- `pytest` (backend, cli), `npm run test` + `npm run lint` (frontend),
  `mypy app`, `ruff check .` all green.
- `code-review` (or `/code-review`) run before merge; `security-review`
  run once per phase before opening the PR — every phase here touches
  either a new public surface, new local file-writing behavior, or a new
  cross-user data path, all worth a dedicated pass.
- Docs epic complete: no stale references to pre-phase behavior left in
  `README.md`/`AGENTS.md`/`docs/`.
- Version bumped (minor) in the four version-bearing files, following
  the existing precedent (no `CHANGELOG.md` in this repo — the PR
  description is the release note, same as `community-enhancements.md`).

## Risk Assessment

| Risk | Phase | Mitigation |
|---|---|---|
| Public demo endpoint becomes an abuse/cost vector (large inputs, scraping) | 4 | 20KB input cap, per-IP rate limit, no persistence, no outbound network calls from the parser |
| `myace watch --auto-pull` silently clobbers a user's hand-edited files | 2 | Explicitly never auto-pulls over `locally_modified` files — only auto-pulls when the *only* issue is staleness, not local edits |
| `handoff_to` frontmatter drifts from the prose "## Handoff" section it mirrors | 3 | Called out explicitly in Epic 3.2; the dangling-reference validator (Epic 3.1) catches broken references but not prose/frontmatter prose *disagreement* — accept as a known gap, don't over-engineer a text-similarity checker for it |
| Compile-status endpoint (Epic 2.1) doesn't actually save much cost since it still needs artifact resolution | 2 | Documented honestly in the endpoint's own docstring rather than oversold; still saves adapter `translate()` cost, which is the more expensive half for large profiles |
| Freshness queue depends on a role model from a different, unshipped plan | 4 | Explicit `is_admin` fallback specified in Epic 4.5, no hard dependency |
| Four separate branches drift out of sync with `main` if phases take a long time | All | Merge each phase's PR before starting the next phase's branch (sequencing section) rather than developing all four in parallel |
