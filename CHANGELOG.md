# Changelog

All notable changes to MyACE are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0-pre.1] — 2026-11-22

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
  kept.
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
  it too. The Python package manager canonicalises `2.0.0-pre.1` to
  `2.0.0rc1`, which is what the CLI prints.

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
