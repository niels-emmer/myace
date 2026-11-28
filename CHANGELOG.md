# Changelog

All notable changes to MyACE are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Agent-level permissions** (ADR-0019). Agents can declare
  `permissions: {edit: deny, ...}`; Claude Code gets `disallowedTools` and
  OpenCode a `permission:` block in the agent's own file. Restrict-only, and no
  adapter writes a shared config file. Packs can ship global ask/deny rules
  (`permissions.json`) as a sidecar, and `myace pull --apply-permissions` merges
  them into your config with a diff, additively and reversibly
  (`myace permissions-remove`). New `permissions_not_enforced` compile warning
  for targets that can't express them. Read-only starter-pack agents
  (reviewers, auditor, verifier, orchestrator) are now restricted. Needs the
  `b7c8d9e0f1a2` migration.

### Changed

- **Base packs share one governance core.** Change Control, Secrets And
  Destructive Actions, Provenance And Attribution and Rule Of Least Power are
  now written once in `collections/_shared/` and generated into each base
  pack's `AGENTS.md` (`scripts/sync_shared_core.py`, drift-checked in tests).
  Packs stay self-contained. Vibecoder's overlapping rules merged into these
  and its opencode-only model config was removed. Data Scientist gains a
  data-governance rule; Software Engineer and DevOps rules now say what to do
  on tools without subagents. Existing deployments need
  `reconcile_seeded_collections --apply --update-content`.

## [2.1.0] — 2026-11-25

The MCP release: MyACE's public packs become usable by any coding agent, not
just a browser session or the CLI. API and database changes are additive —
no migrations, no removed routes, no changed response shapes.

### Added

- **Read-only MCP server** (`mcp/`) — any MCP-capable coding agent can browse
  public packs, read an item's full text, and fetch a pack compiled for a
  chosen framework, with no account and no CLI. Five tools
  (`search_packs`, `get_pack`, `get_item`, `list_targets`, `download_pack`)
  and four resource templates over Streamable HTTP at `/mcp`; opt-in via the
  `mcp` compose profile and proxied through the frontend's nginx. It has no
  database, no credentials and no write tool — installing stays a human
  decision. See [ADR-0018](docs/adr/0018-public-read-only-mcp-server.md) and
  [docs/mcp.md](docs/mcp.md).
- **Agent-fetchable pack install document** —
  `GET /api/v1/collections/community/{id}/install.md?target=…` returns a
  self-describing Markdown document (or `format=json`/`zip`) for a public
  pack, with an ETag and a 2 MiB cap. Hand the URL to any agent that cannot
  speak MCP. See [docs/plans/agent-install-url.md](docs/plans/agent-install-url.md).
- **`GET /api/v1/frameworks`** — the public list of compile targets, so a
  typed client can offer a picker without the authenticated adapter route.
- **`compile_pack()`** — pack-scoped compilation over the same
  `_compile_collections()` body `compile_profile()` uses, so a pack and a
  setup can never drift apart.
- **Four public starter-pack add-ons** — Git Practices, Design & Scaffold,
  Self-Hosted Deployment, and Enterprise AI Governance, seeded as public
  starter packs (#213).
- **Specialized add-ons as community packs** — EU AI Act, Scaleway, iOS and
  Android now seed as community-contributed packs (`is_starter_pack=False`)
  while staying published, approved and public (#214).
- **`deploy-live-debug` skill** in the DevOps Engineer starter pack: a
  fix-validate-deploy loop for a live host, with rollback guidance (#212).

### Changed

- Optional `q` filter (case-insensitive name/description) on the anonymous
  community listing, so an agent can search server-side.
- Seeding matches existing rows by their stable `seed://` ref and reconciles
  the starter flag in place, so reclassified packs update instead of
  duplicating (#214).
- **Dependencies (frontend):** Tailwind CSS 3.4.19 → 4.3.5 (#191),
  `@xyflow/react` 12.12.1 → 13.0.2, `@testing-library/jest-dom` 7.0.1 → 8.0.0,
  `@tanstack/react-query` 5.108.0 → 5.108.1 (#219).

### Fixed

- MCP tool calls present the public `Host` header, so a backend running
  `TrustedHostMiddleware` no longer rejects every tool with `400 Invalid host
  header`; they also forward the caller's IP so per-IP rate limits stay
  per-client instead of collapsing into one shared bucket (#222).
- MCP surfaces the install route's guidance document for an unknown or
  aliased `target` instead of failing with a JSON decode error, and never
  returns that Markdown as an archive. The compile-time size guard now names
  the right remedy per format.
- Pipelines diagrams draw their handoff connectors: `PipelineNode` had no
  React Flow `<Handle>` pair, and React Flow silently drops edges whose
  endpoint node exposes no handle (#220).
- Pipeline setup metadata now renders on the pipeline detail (#220).
- `deploy-live-debug` skill: explicit approval gate before any live-host
  mutation, rollback via the last good tag instead of a detached HEAD,
  consistent read-only prechecks (#215).

### Documentation

- [ADR-0018](docs/adr/0018-public-read-only-mcp-server.md) (public read-only
  MCP server), [docs/mcp.md](docs/mcp.md) (agent/operator guide), and
  [docs/plans/mcp-server.md](docs/plans/mcp-server.md) (implementation record).
- Public-route counts corrected across `README.md`, `SECURITY.md`,
  `docs/architecture.md`, `docs/invariants.md` and `docs/data-model.md` as
  the anonymous surface grew from five routes to seven; ADR-0014 carries an
  amendment note rather than rewritten history (#223).
- `docs/debugging.md` gains the two production-only MCP gotchas (internal
  `Host` header, guidance-vs-JSON), and `docs/extending.md` gains an
  "Adding an MCP tool" guide (#223).
- `docs/mcp.md` added to the wiki page map, so it publishes with the rest of
  `docs/` (#223).
- Stale claims corrected across the root docs after 2.0.0 (#210).

### Security

- The new pack install document compiles a pack for unauthenticated callers,
  so its safety does not rest on the visibility predicate alone:
  `compile_pack()` hard-codes `can_use_frozen=False` (never serves a snapshot
  of an unpublished pack), only enabled items are compiled, and no read route
  moves `download_count`. `GET /frameworks` compiles nothing — it only lists
  the adapter names an admin has enabled. Both are covered by
  `storefront_rate_limit`.
- The MCP container is non-root, binds no host port, holds no database
  credential, and enables DNS-rebinding protection (`MCP_ALLOWED_HOSTS`),
  failing closed with `421` rather than open.

## [2.0.0] — 2026-11-22

The onboarding and usage revamp: MyACE now speaks in **packs**, **setups** and
**installs**, opens with a storefront, and installs one setup into several
frameworks instead of one at a time. API and database changes are additive;
existing deployments keep working through the upgrade.

### Added

- **First-run wizard** at `/onboarding` — five single-decision steps:
  frameworks, packs, review/name, project-vs-machine location, install.
  Resumable via URL and local draft, skippable, and remembered across devices.
  Includes an "I already have configs" branch into the import flow.
- **Public storefront** at `/welcome` and anonymous read-only browsing of
  starter and community packs at `/packs` — listings, detail pages, contents
  and aggregate ratings, rate-limited and narrowly allowlisted (ADR-0014).
- **Multi-framework setups** — `Profile.target_frameworks` lets one setup
  target several frameworks, with a per-framework install/verification matrix
  on the setup page.
- **Install claims** (`profile_installs`) — records "installed, not verified"
  per setup/framework/location. Verified state still comes only from
  `myace check --report`.
- **Companion direct install** — opt-in `POST /apply/preview` and `/apply`
  write the compiled output to the machine or project with a per-file diff,
  single-use confirmation, timestamped backups, atomic writes and path
  confinement. Off by default (ADR-0016).
- **Publish wizard** at `/packs/:id/publish` with a description step, preview,
  optional SPDX-style license, and a Draft → In review → Approved / Changes
  requested → Unpublished status tracker.
- **Pack reference snapshots** — adding a pack to a setup records the artifact
  set so a later unpublish or denial cannot silently break an install.
  Owner/admin-only frozen fallback, with a `pack_unavailable` compile warning
  for everyone else (ADR-0015).
- **Command palette** (⌘K / Ctrl-K) for pages, packs, setups and common
  actions.
- **Bundles** — curated starting-point + add-on combinations presented as
  single cards; a frontend constant, not a new table.
- **Pipelines** tab under Packs, unifying the orchestration gallery and
  composition wizard with the pack library.

### Changed

- **User-facing vocabulary is now Pack / Setup / Install / Item / Pipeline.**
  API routes, models and compiler internals keep Collection / Profile /
  Artifact / compile. See AGENTS.md rule 42 for the mapping.
- **Navigation is four task-based areas** — Home, Setups, Packs, Settings —
  with "My machine" as a secondary link. The old Collections / Build /
  My Machine groups are gone; every legacy path redirects.
- **Landing page is a storefront**, not a members-only pitch: featured packs,
  the four-step story and the framework strip, with the live compile demo
  kept. Copy states plainly that accounts are free and that browsing needs no
  account, and the primary calls to action point at the right destinations.
- **Pack detail is unified** — owned, starter and community packs share one
  page; `/packs/community/:id` redirects to `/packs/:id`.
- **Frozen compile content is owner-scoped.** A setup owner (or an admin) can
  reinstall after a pack is withdrawn; other readers of a public profile get
  `pack_unavailable` and no frozen artifacts. Unpublish remains a real
  retraction for third parties.
- **`download_count` is advisory**, displayed as "used N times" and never
  used for ranking or "most used" sorting.
- **`myace --version` now reports the release version**, derived from package
  metadata (`importlib.metadata`) instead of the stale hardcoded `0.1.0` —
  the same value recorded as the client version in stored credentials, and
  PyInstaller release binaries now bundle the package metadata so they report
  it too.

### Security

- The five public `GET /collections/community*` reads are a deliberate,
  rate-limited auth exception; every neighbouring route still requires auth.
- Companion `/apply` is off by default, requires the companion header and an
  exact Origin, rejects lexical and symlink escapes, backs up overwritten
  files, never deletes, and refuses project-only targets for machine installs.
- Frozen snapshots bypass collection visibility only for the profile owner
  and admins; the bypass is scoped and documented in ADR-0015.

### Upgrade notes

- Run `alembic upgrade head`. The release adds `profiles.target_frameworks`,
  `profiles.pack_snapshots`, `collections.license`,
  `users.onboarding_completed_at`, and the `profile_installs` table; the legacy
  `target_framework` column is retained.
- No API removals. `Profile` reads include `target_frameworks`; clients may
  continue sending `target_framework`.
- Companion direct install requires `myace serve --allow-apply` (or
  `MYACE_COMPANION_ALLOW_APPLY=1`). Without it the write routes return 403.
- All pre-2.0 frontend paths redirect; update bookmarks at your leisure.

### Known issues

None specific to this release. Starter-pack *content* edits still do not
reach an already-seeded deployment without a reseed (AGENTS.md rule 25).
