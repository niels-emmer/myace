# Invariants

These are the rules MyACE's code is expected to enforce everywhere, all the
time. If you're changing anything related to auth, ownership, or the
canonical IR, check this list before and after your change. Each invariant
names where it's enforced so you can verify it hasn't regressed.

## Authorization

1. **Every API route requires an authenticated user**, except the explicit
   public list: `/health`, `/auth/register`, `/auth/login`,
   `/auth/login/mfa`, `/auth/logout`, `/auth/forgot-password`,
   `/auth/reset-password`, `/auth/login/{provider}`,
   `/auth/callback/{provider}`, `/auth/providers`,
   `POST /demo/compile` (see
   [ADR-0011](adr/0011-public-demo-sandbox.md) and AGENTS.md rule 36 for
   why this one earns the exception, and invariant 22 below for what makes
   it safe to leave public), and the five anonymous storefront reads
   `GET /api/v1/collections/community`, `/community/top`,
   `/community/categories`, `/community/{id}`, and
   `/community/{id}/artifacts` (added in Phase 5 — see
   [ADR-0014](adr/0014-public-pack-browsing.md) and AGENTS.md rules 13/42:
   approved-only, sanitized response, read-only, rate-limited).
   Enforced by `Depends(get_current_user)` — `backend/app/core/deps.py`.
   *If you add a route and forget this dependency, it's open to anyone.*

2. **A regular user can read and write their own resources**, read (never
   write) resources another user marked public, and cannot see or touch
   anything else. Enforced by `authorize_access()` (single resource) and
   `owner_or_public_clause()` (list endpoints) — `backend/app/core/authz.py`.
   *Don't hand-roll an owner check inline; use these two functions so the
   rule stays in one place.*

3. **`current_user.is_admin` bypasses ownership and visibility entirely.**
   Both functions in rule 2 check this first. `is_admin` itself is a single
   global flag with no per-resource variant. The one narrower role that
   *does* exist — `moderator`, via `User.role` — is deliberately **not**
   plugged into `authorize_access()`/`owner_or_public_clause()` at all; see
   rule 8 and [ADR-0007](adr/0007-additive-user-role-column.md).

4. **Denied access returns 404, not 403.** This is deliberate: a 403 tells
   an attacker the resource exists but they can't see it; a 404 doesn't.
   Every route that fails an `authorize_access()` check gets a 404 for
   consistency with the rest of the API (e.g. "collection truly doesn't
   exist" and "collection exists but isn't yours" are indistinguishable from
   the outside).

5. **`Artifact` has no owner of its own.** Every route touching an artifact
   must first load its parent `Collection` and authorize against
   *that* — never assume an artifact ID alone is enough to check access.

6. **Bulk/cross-resource operations authorize every resource they touch, not
   just the first one.** `bulk_export_artifacts`'s source collection needs a
   *read* check; its target collection (if it already exists) needs an
   independent *write* check. This was a real bug once — see
   [ADR-0003](adr/0003-ownership-based-authorization.md) — don't reintroduce
   it in a new bulk operation.

7. **Creation always derives ownership from `current_user.id`, never from a
   client-supplied field.** If you see a route accepting `owner_id`/
   `user_id` as a request parameter and trusting it, that's the exact bug
   class this whole auth system was built to close. There is no more
   "placeholder user" concept — see
   [ADR-0005](adr/0005-email-password-baseline-auth.md).

8. **Moderator scope is community-content-only, and never mixes with
   `is_admin`'s ownership bypass.** `require_moderator_or_admin`
   (`backend/app/core/deps.py`) reads `current_user.role` only and grants
   no `require_admin`-only capability (user management, system settings,
   adapter toggles). It gates `/api/v1/moderation/*` plus two Phase-4
   additions that are the same kind of community-content review capability
   under a different URL prefix: `GET /admin/freshness-queue` and
   `POST /collections/{id}/verify` (AGENTS.md rule 37) — never widen it to
   accept `is_admin` alone, never merge it with `require_admin`, and never
   use `authorize_access()`'s owner-bypass on any route it gates — see
   [ADR-0007](adr/0007-additive-user-role-column.md).

9. **A collection's own owner can never approve or deny their own
   submission, even if they're also a moderator or admin viewing it through
   a different capability.** `POST /moderation/{id}/approve` and `.../deny`
   are gated by `require_moderator_or_admin` alone — there is no
   ownership-based bypass on these two routes, unlike almost every other
   route in the app. This is deliberate, not an oversight: it's the entire
   point of moderation existing as a state machine — see
   [ADR-0008](adr/0008-collection-moderation-state-machine.md).

10. **Ratings and comments gate on `Collection.moderation_status ==
    "approved"`, never on `published`/`visibility` alone.** Those two
    fields are only ever set together with `moderation_status = "approved"`
    today, but `moderation_status` is the field a future change should
    check — `published` could in principle drift from it if a bug
    elsewhere set it directly. Self-rating is additionally blocked
    (`owner_id == current_user.id` → 400) regardless of
    `moderation_status`.

## Canonical IR

11. **The Canonical IR schema (`type`, `name`, `version`,
   `target_compatibility`, `priority`, `tags`, `description`, `body`) is the
   single source of truth.** Every adapter's `translate()` reads only from
   `CanonicalArtifact` — never from a framework-specific shape. If a target
   framework needs a field the IR doesn't have, that's a schema change (with
   a migration), not a special case in one adapter.

12. **Adapters are stateless and pure.** `translate(artifacts) -> {filename:
   content}` must not touch the database, the filesystem outside its return
   value, or any other adapter. This is what would make `cli/myace_cli/adapters/`
   a safe local-rendering copy of `backend/app/adapters/` *if* anything in
   the CLI called it — as of this writing, `myace pull`
   (`cli/myace_cli/sync.py`) always calls the backend's `/profiles/compile`
   endpoint directly and has no fallback path, so this package is
   maintained but currently unused. See
   [extending.md](extending.md#adding-a-target-adapter).

13. **Import and export must stay symmetric.** `scan_directory()`
    (`backend/app/services/scanner.py`) and `artifacts_to_files()`
    (`backend/app/services/github_export.py`) implement inverse
    transformations of the same directory layout. A collection exported to
    GitHub and re-imported from that repo should scan back to the same
    artifacts (`model_config` artifacts are the one documented exception —
    they don't round-trip into a single file and are skipped on export).

14. **`tags` and `target_compatibility` are stored as JSON-encoded `Text`,
    not native list columns.** Any route returning `Artifact` data must
    decode them first (`_artifact_to_read()` in
    `backend/app/api/collections.py`, or `_db_to_canonical()` in
    `backend/app/services/compiler.py`) — returning a raw DB row 500s the
    moment a row has real data. See
    [debugging.md](debugging.md#response_model-silently-strips-fields-you-didnt-declare).

## Data integrity

15. **All resource primary keys are UUIDs**, never auto-increment integers.
    The singleton `system_settings` row (fixed `id=1`) is the only
    exception. This is a hard rule, not a default; don't add a table that
    deviates from it.

16. **Every schema change ships an Alembic migration with a working
    `downgrade()`.** Never edit a migration that's already been committed —
    write a new one. See `AGENTS.md` rule 2.

17. **No cascade delete on `artifacts.collection_id`.** The foreign key has
    no `ondelete` configured, and collection deletion in the app is a
    *soft* delete (`Collection.is_active = False` — `delete_collection` in
    `backend/app/api/collections.py`), so this is rarely exercised. If you
    ever add a hard-delete path for collections, you must delete or reassign
    their artifacts first, or the `DELETE` will fail on the FK constraint.

18. **Artifacts, profiles, doc_cache entries, collection comments, and
    collection ratings use soft-delete, not hard delete.**
    `session.delete()` is never called on these models — instead,
    `deleted_at` is set to `datetime.now(UTC)`. Every list/get/aggregate
    query filters on `deleted_at == None` to exclude soft-deleted rows.
    This matches the existing pattern for collections (`is_active =
    False`) and API tokens (`is_active = False`). Enforced in
    `backend/app/api/collections.py` (`bulk_delete_artifacts`),
    `backend/app/api/profiles.py` (`delete_profile`),
    `backend/app/api/doc_cache.py` (`delete_cache_entry`),
    `backend/app/api/comments.py` (`delete_comment`), and
    `backend/app/api/ratings.py` (`delete_rating`). `CollectionRating`'s
    unique constraint is on `(collection_id, user_id)` only, not scoped to
    live rows — re-rating after a soft-deleted rating revives the same row
    (clears `deleted_at`, overwrites `stars`) rather than erroring on the
    constraint or leaving an orphaned soft-deleted duplicate.

19. **`Profile.additional_collection_ids` and `disabled_artifact_ids` are
    JSON UUID lists, not real foreign keys.** The database will not stop you
    from storing a reference to a collection that's later deleted or made
    private. `compile_profile()` resolves these at request time; a
    collection it can't resolve is no longer skipped silently — it falls
    back to the profile's reference snapshot when one exists, and emits a
    `pack_unavailable` warning either way (invariant 24). Don't assume
    referential integrity here that the schema doesn't actually provide.

20. **`Collection.artifact_count` is a denormalized cache**, not a computed
    value. Every route that adds or removes artifacts from a collection
    (bulk import, bulk delete, bulk export's target, and the single-artifact
    `POST /{collection_id}/artifacts`) must update it, or it silently drifts
    from the true count.

21. **Sync-status reporting is always self-scoped to `current_user.id`, both
    on write and on read.** `POST /sync/report` upserts on
    `(current_user.id, profile_id, target, machine_label)` — the caller can
    never write a row under another user's id, since `user_id` is never
    accepted from the request body (`SyncReportRequest` has no such field;
    see AGENTS.md rule 13). `GET /sync/status` filters on
    `SyncStatus.user_id == current_user.id` with no admin bypass and no
    "everyone's status" view anywhere in the API — unlike most other
    resources in this app, there is no visibility flag that would make a
    `SyncStatus` row visible to anyone but the user who reported it. This is
    deliberate: a sync report reveals which files a user has hand-edited on
    their own machine, which is exactly the kind of thing this project
    doesn't expose without being asked (see
    [ADR-0009](adr/0009-manifest-based-drift-detection.md)).

22. **`POST /demo/compile` never persists anything, in either direction.**
    Unlike every other route in this API, it has no DB session dependency
    at all — there is no `AsyncSession` in scope for its handler to write
    (or even read) with. This is what makes invariant 1's public-route
    exception for it safe: there's no ownership model to bypass because
    there's no data being touched. Enforced structurally, not just by
    convention, and covered by
    `backend/tests/test_demo.py::test_demo_compile_creates_no_database_rows`,
    which asserts zero `Collection`/`Artifact` rows exist after a compile
    call. See [ADR-0011](adr/0011-public-demo-sandbox.md).

23. **`mfa_forced` gates login, not just UI copy.** When the MFA feature is
    on and `mfa_forced` is set, an account with no enrolled TOTP factor gets
    no session by either password login (`login_with_password()`) or SSO
    (`auth_callback()`) — only a scoped enrolment challenge it must complete
    before entering the app. Enforced in `backend/app/api/auth.py`. The MFA
    login token is single-use, and a TOTP code cannot be replayed inside its
    30-second step.

24. **An unavailable pack compiles from a frozen reference snapshot, and a
    pack that can't be resolved is never skipped silently.** On profile
    create/update, `capture_pack_snapshots()` records the enabled live
    artifact ids (plus a hash and timestamp) for every referenced collection
    the requesting user does **not** own and can still read — owned
    collections are never snapshotted, and an unreadable one is never
    re-read (its existing snapshot is preserved). A profile update
    therefore read-checks only **newly added** collection ids, so a setup
    whose pack went private stays editable. When `compile_profile()` finds a
    referenced collection missing, inactive, or unreadable, it loads those
    artifact ids by `(id, collection_id)` with no live collection-read check
    **only for an allowed viewer** and emits
    `ValidationIssue(code="pack_unavailable")`. An allowed viewer is:
    `requesting_user is None` (internal/test), the profile's owner, or an
    admin. Every other requester — e.g. user B compiling user A's public
    profile — gets `pack_unavailable` and the pack is skipped, never served
    from the frozen set. When the requester cannot read a pack, the warning
    shows only an id prefix, never the pack's display name. With no
    snapshot, the collection is skipped but the warning is still emitted —
    the old silent-skip behaviour is gone. That reload is the one deliberate
    compile-time authorization bypass; it is scoped to ids the profile owner
    could read when the snapshot was captured, and it relies on artifacts
    being soft-deleted at most (invariant 18), never hard-deleted. See
    [ADR-0015](adr/0015-pack-reference-freeze.md).

25. **Install claims are not verification, and use counts are advisory.**
    A `ProfileInstall` row records only that a user *said* they installed a
    profile to a target at a location. The only verified source of "the
    files match the compiled output" remains `SyncStatus`, fed by `myace
    check --report`. Like sync status (invariant 21), install claims are
    self-scoped: `POST`/`GET /profiles/{id}/installs` read and write only the
    caller's own rows, with no admin bypass. `POST /collections/{id}/use`
    increments `download_count` on **every** call by a signed-in non-owner
    and returns the new count; an owner is blocked (400) from inflating
    their own. There is no per-user dedupe, so any non-owner can inflate
    another pack's count — `download_count` is tamperable and must be treated
    as a rough popularity signal, never a verified metric or
    integrity-sensitive ranking input. See
    [ADR-0015](adr/0015-pack-reference-freeze.md).

## A gap that's accepted, not fixed

**A public profile reveals which collections it references, but not their
contents to someone who cannot read them.** `ProfileRead` exposes
`base_collection_id`/`additional_collection_ids` to anyone who can read the
profile, so a public profile leaks collection *ids* (not names, artifacts,
or membership details). Compilation itself is requester-scoped:
`compile_profile()` only pulls live artifacts from collections the
requester can read, and serves frozen content only to the profile owner or
an admin (invariant 24). A public profile therefore cannot be used to
obtain artifacts from a private collection the viewer cannot read.
The accepted simplification is that profile visibility still does not
cascade to collection visibility: you can mark a profile public while
composing it from private collections, and another viewer sees the profile
with those packs skipped and a `pack_unavailable` warning rather than the
profile being rejected. This is consistent with "no granular per-resource
sharing" (see [ADR-0003](adr/0003-ownership-based-authorization.md)). Don't
treat collection privacy as the boundary that makes a public profile safe;
the owner-scoped-compile rule is that boundary.
