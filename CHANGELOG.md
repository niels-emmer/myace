# Changelog

All notable changes to MyACE are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`scripts/deploy.sh`**: a diff-driven deploy for a running install. It works out
  from the changed files whether a change needs a backend restart or image
  rebuild, a migration, a frontend or `mcp` rebuild, and a reconcile; backs up the
  database first; gates the reconcile behind a person reading its dry run; and
  checks that users, ratings, verifications, tokens and settings did not change.
  `--status`, `--plan-only` and `--check` (pack drift, exit 3) are read-only. See
  [docs/deployment.md](docs/deployment.md#deploying-updates).

### Removed

- The unused `COMMUNITY_REPO` setting (default `nemmer/MyACE`, a stale handle that
  nothing read). A leftover `COMMUNITY_REPO` in an existing `.env` is ignored.

## [2.4.0] — 2026-11-28

The pack page and discovery release. One additive migration
(`c1d2e3f4a5b6`: nullable `collections.relations` and `content_updated_at`); no
removed routes and no changed response shapes (new fields and one new anonymous
read). Existing deployments run `alembic upgrade head`, restart the backend,
rebuild the frontend and `mcp` images, then
`reconcile_seeded_collections --apply --update-content --update-metadata`
(dry run first).

### Added

- **Pack page: related packs and "Updated".** Seeded packs can declare `layers_on`
  and `pairs_with` (registry entries; the cloud packs layer on `iac-expert`). The
  public pack page shows them as links and shows when the pack's items last
  changed. Adding a pack to a setup warns, without blocking, when the setup lacks a
  pack it layers on, and offers to add it when creating a new setup. New nullable
  columns `collections.relations` and `collections.content_updated_at` (migration
  `c1d2e3f4a5b6`, run `alembic upgrade head`); the MCP's `get_pack` returns both.
- **Preview install tab** on public pack pages: what a pack compiles to for any
  framework, with warnings, a zip download, the install URL for coding agents and,
  where the MCP server is enabled, the `claude mcp add` command. Read-only, no
  account needed, and it does not count as a use.
- **Library discovery:** topic chips and search over topics, derived from item tags
  (new anonymous `GET /collections/community/topics`); filters are kept in the URL;
  and a new "Languages & Platforms" category for the language and platform add-ons.
- **`reconcile_seeded_collections --update-metadata`** rewrites a seeded pack's
  name, category, description and relations from the registry (dry run lists each
  old and new value), so pack-card text no longer drifts from the registry on a
  long-lived deployment. It never touches ratings, verification or moderation.

### Changed

- **Documentation audit.** README counts (30 starter packs, 6 community add-ons,
  439 items, 9 categories, 223 tags), the anonymous-read lists (README, API.md,
  invariants, ADR-0014 amendment) and the pack-page notes in AGENTS.md are
  current; a new "Adding a pack to the shipped set" guide in `docs/extending.md`;
  two new `docs/debugging.md` entries. AGENTS.md had two rules numbered 42 and two
  numbered 43: the base-pack governance core is now rule 44 and permissions rule
  45 (references updated).
- Stamped `content_updated_at` on seeded packs now reflects the last real content
  change rather than the time reconcile ran.

### Fixed

- The anonymous pack library no longer silently stops at 100 packs; it pages
  through the whole listing.
- **Add-ons and base packs now list pi.dev under "Works with".** Every item's
  `compatibility` list stopped at 11 adapters, so the pack page showed 11
  frameworks while the product compiles to 12. All 229 lists now name `pi-dev`,
  and a test keeps them in step with the adapter registry. Existing deployments
  need `reconcile_seeded_collections --apply --update-content`.
- The Google Cloud pack description says "Well-Architected" instead of the old
  "Architecture Framework" name.

## [2.3.0] — 2026-11-28

The add-on pack expansion release. Content only: no migration, no changed routes or
response shapes, and no frontend or MCP code changes. New packs seed on the next
backend restart; existing deployments then run
`reconcile_seeded_collections --apply --update-content` for the new items in
existing packs and the renames (dry run first; it soft-deletes the old rows).

### Added

- **Eight new add-on packs.** Language packs for Python, TypeScript / Node, Go and
  Rust (typed errors, boundary validation, concurrency and async care, supply-chain
  hygiene, test patterns); Kubernetes (least-privilege pods, RBAC and network
  policy, confirm-before-apply rollouts, ingress-nginx retirement); Accessibility
  (WCAG 2.2 AA); Observability & Incident Review (telemetry conventions, SLOs,
  blameless postmortems); and Privacy & Data Protection (data inventory, DPIA,
  subject requests and breach runbooks, drafts only). Each has a builder/reviewer
  pair where applicable, read-only reviewers with `edit: deny`, tiered rules and
  skills. Python, TypeScript / Node, Kubernetes, Accessibility, Observability and
  Privacy seed as starters; Go and Rust seed on the community shelf. Fresh installs
  get them on boot; existing deployments pick them up on the next restart (new
  collections need no reconcile).
- **Gap-filling items in existing packs:** `llm-evals` and `rag-design` skills
  (ai-engineering), a Spring Security rule and skill (java-spring), a pinning and
  deletion-protection rule and skill (iac-expert), a supply-chain rule and skill
  (devops), and a guardrails skill for each of AWS, Azure, GCP and Scaleway
  (SCP/RCP, Azure Policy, Organization Policy, and IAM design where no deny layer
  exists). Existing deployments need
  `reconcile_seeded_collections --apply --update-content` to receive them.
- Cloud packs gain vendor-specific depth: a `<cloud>-service-patterns` skill, a
  "Pick The Service For The Workload" rule, and a read-only `<cloud>-reviewer`
  agent in each of AWS, Azure, GCP and Scaleway.
- A convention test that add-on item names are unique across every pack (rule 29).

### Changed

- **Frontend accessibility** now targets WCAG 2.2 AA: the rule and the Accessibility
  Checklist skill add the 2.2 criteria and point to the new Accessibility pack
  for the full review. No item renamed.
- **Renamed items that carried the wrong framework label** (names are identity, so
  reconcile soft-deletes the old rows and adds the new ones): AWS rule "AWS
  Governance By Design (CAF)" is now "AWS Governance By Design" and skill "AWS CAF
  Landing Zones" is "AWS Landing Zones"; GCP rule "Governance By Design (GCAF)" is
  "GCP Governance By Design", rule "Map Changes To GCP Architecture Framework
  Pillars" is "Map Changes To GCP Well-Architected Pillars", and skill "GCP
  Architecture Framework Pillar Review" is "GCP Well-Architected Review". Azure's
  CAF labels are correct and unchanged.

- **Add-on pack overlaps trimmed in place** (no pack or item renamed): one
  AI-authorship marker (`[ai]` line in the body) across enterprise-ai-governance,
  auditor, git-practices, design-and-scaffold and self-hosted-deploy; the auditor
  classification tiers map onto the four-class scheme and REGULATED routing allows
  a documented exception; fullstack E2E no longer says to retry flaky tests;
  the DevOps add-on says it supplements the DevOps base; backend's rollback rule
  points at its skill. Existing deployments need
  `reconcile_seeded_collections --apply --update-content`.

- **Add-on pack currency**: iOS state management now leads with the Observation
  framework (`@Observable`, iOS 17+) and the 6.9" screenshot baseline; the
  security audit checklist names the OWASP Top 10 edition (2025 renumbered the
  categories); Google Cloud's framework is called the Well-Architected Framework;
  Scaleway tag and billing-unit wording corrected and WAF flagged as beta;
  `devops` incident wording no longer calls rollback "fix forward";
  `ai-engineering` credits 12-factor-agents' content licence. Existing
  deployments need `reconcile_seeded_collections --apply --update-content`.

- **Add-on packs follow the base-pack conventions**: every add-on rule now
  carries a priority tier (90 security/safety, 70 quality gate, 50 process),
  read-only add-on agents declare `permissions: {edit: deny}`, every add-on agent
  has the no-subagent fallback, and cross-pack references (cloud packs ->
  `iac-expert`, `docker-patterns` -> `container-build`, base-agent handoffs) say
  what to do when the companion pack is absent. This changes compiled rule order
  for add-ons. A new test keeps them in line. Existing deployments need
  `reconcile_seeded_collections --apply --update-content`.

- **Add-on pack accuracy fixes** (audit `docs/plans/addon-pack-quality-audit.md`):
  Android (LiveData/Flow collection, modifier order, Play target API 36), AWS
  (OIDC trust policies must pin `aud` and `sub`, SCP/NACL/hub-spoke wording,
  federation for human access), Azure (tags do not inherit from the resource
  group), GCP (correct org-policy constraint names), Java/Spring (`@Cacheable`
  placement, Maven has no lockfile), EU AI Act (Art 49 and Art 50(2) dates),
  `git-practices` release (via a release PR, never a direct push to the default
  branch), and `dev-writing` reframed as a plain style guide (one integrity
  rule; the style rules now live in its skills; it never changes AI-authorship
  marking). Existing deployments need `reconcile_seeded_collections --apply
  --update-content`; the four removed `dev-writing` rules are soft-deleted by
  that run.

## [2.2.0] — 2026-11-28

The permissions and governance release. One additive migration
(`b7c8d9e0f1a2`, a nullable `artifacts.permissions` column); no removed routes
and no changed response shapes. Existing deployments run `alembic upgrade head`,
then `reconcile_seeded_collections --apply --update-content` (it also repairs
stored item counts, see below), and rebuild the frontend and MCP images.

### Added

- **Agent-level permissions** (ADR-0019). Agents can declare
  `permissions: {edit: deny, ...}`; Claude Code gets `disallowedTools`, OpenCode
  a `permission:` block, and Cursor (`readonly`) and Copilot CLI (`tools`) a
  native agent file, each in the agent's own file. Restrict-only, and no adapter
  writes a shared config file. The new `permissions_not_enforced` compile warning
  names what a target can't express. Read-only starter-pack agents (reviewers,
  auditor, verifier, orchestrator) are now restricted.
- **Global permission rules.** Packs can ship ask/deny rules (`permissions.json`)
  as a sidecar the tool never loads on its own, and `myace pull
  --apply-permissions` merges them into your config with a diff — additively,
  never overriding your own entries, reversible with `myace permissions-remove`.
  OpenCode 2.x configs are merged in their v2 form; Codex CLI gets a real
  `.codex/rules/myace.rules` for global shell rules.
- **Edit an agent's permissions on the owner page:** five capabilities, each
  Inherit / Ask first / Block (restrict-only; there is no allow).
- **Install preview explains permission files.** A sidecar such as
  `.claude/myace.permissions.json` is labelled "not active yet" with how to merge
  it; Codex's rules file is labelled as live.
- **Rules can carry a priority and tags** (`<!-- myace: priority=90 tags=security -->`
  under a rule's heading); both scanners read it and export writes it back. Base
  packs now use deliberate tiers (90 safety/security, 70 quality gates, 50
  process), which changes the order rules appear in compiled output.
- **New pack content:** Vibecoder gets a light "Run What You Changed" testing
  rule; Software Engineer gets "Dependency Hygiene", "Observability Baseline"
  and a read-only `architect` agent (wired into its orchestrator); Data Scientist
  gets a read-only `data-privacy-reviewer` agent wired into its handoffs and a
  "Handle Personal Data Deliberately" rule.

### Changed

- **Base packs share one governance core.** Change Control, Secrets And
  Destructive Actions, Provenance And Attribution and Rule Of Least Power are
  written once in `collections/_shared/` and generated into each base pack's
  `AGENTS.md` (`scripts/sync_shared_core.py`, drift-checked in tests); the
  memory-system rule and skill, the plan-tracking skill and Testing Discipline
  are generated the same way for Software Engineer and DevOps. Packs stay
  self-contained. Vibecoder's overlapping rules merged into the core and its
  opencode-only model config was removed.
- **No-subagent fallback** is spelled out in the Software Engineer and DevOps
  orchestrators, every agent's Handoff and the `verify` workflow: do each stage
  yourself as a separate pass instead of skipping it.
- **Pack and owner pages show permissions properly.** A pack's global rules appear
  under their own "Permission rules" filter as a readable list instead of a raw
  `model_config` JSON blob, and agents with restrictions show them as sentences
  ("Cannot edit files"). The owner page uses the same view; the raw JSON stays
  editable.
- **Pack item counts no longer include the permission policy** (`artifact_count`,
  compile's count and the MCP `item_count`), so "Vibecoder: 12 items" is true
  again.
- **Cursor and Copilot CLI downloads gain native agent files**
  (`.cursor/agents/<name>.md`, `.github/agents/<name>.agent.md`); the existing
  rule and instruction files are unchanged. These, the Claude Code output and
  Codex's rules file are checked against vendor docs and unit tests only; only
  OpenCode 2.3.2 was run for real.

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
