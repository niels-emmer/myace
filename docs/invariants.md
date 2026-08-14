# Invariants

These are the rules MyACE's code is expected to enforce everywhere, all the
time. If you're changing anything related to auth, ownership, or the
canonical IR, check this list before and after your change. Each invariant
names where it's enforced so you can verify it hasn't regressed.

## Authorization

1. **Every API route requires an authenticated user**, except the explicit
   public list: `/health`, `/auth/register`, `/auth/login`,
   `/auth/login/{provider}`, `/auth/callback/{provider}`, `/auth/providers`.
   Enforced by `Depends(get_current_user)` — `backend/app/core/deps.py`.
   *If you add a route and forget this dependency, it's open to anyone.*

2. **A regular user can read and write their own resources**, read (never
   write) resources another user marked public, and cannot see or touch
   anything else. Enforced by `authorize_access()` (single resource) and
   `owner_or_public_clause()` (list endpoints) — `backend/app/core/authz.py`.
   *Don't hand-roll an owner check inline; use these two functions so the
   rule stays in one place.*

3. **`current_user.is_admin` bypasses ownership and visibility entirely.**
   Both functions in rule 2 check this first. There is no partial-admin or
   per-resource role — it's a single global flag.

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

## Canonical IR

8. **The Canonical IR schema (`type`, `name`, `version`,
   `target_compatibility`, `priority`, `tags`, `description`, `body`) is the
   single source of truth.** Every adapter's `translate()` reads only from
   `CanonicalArtifact` — never from a framework-specific shape. If a target
   framework needs a field the IR doesn't have, that's a schema change (with
   a migration), not a special case in one adapter.

9. **Adapters are stateless and pure.** `translate(artifacts) -> {filename:
   content}` must not touch the database, the filesystem outside its return
   value, or any other adapter. This is what would make `cli/myace_cli/adapters/`
   a safe local-rendering copy of `backend/app/adapters/` *if* anything in
   the CLI called it — as of this writing, `myace pull`
   (`cli/myace_cli/sync.py`) always calls the backend's `/profiles/compile`
   endpoint directly and has no fallback path, so this package is
   maintained but currently unused. See
   [extending.md](extending.md#adding-a-target-adapter).

10. **Import and export must stay symmetric.** `scan_directory()`
    (`backend/app/services/scanner.py`) and `artifacts_to_files()`
    (`backend/app/services/github_export.py`) implement inverse
    transformations of the same directory layout. A collection exported to
    GitHub and re-imported from that repo should scan back to the same
    artifacts (`model_config` artifacts are the one documented exception —
    they don't round-trip into a single file and are skipped on export).

11. **`tags` and `target_compatibility` are stored as JSON-encoded `Text`,
    not native list columns.** Any route returning `Artifact` data must
    decode them first (`_artifact_to_read()` in
    `backend/app/api/collections.py`, or `_db_to_canonical()` in
    `backend/app/services/compiler.py`) — returning a raw DB row 500s the
    moment a row has real data. See
    [debugging.md](debugging.md#response_model-silently-strips-fields-you-didnt-declare).

## Data integrity

12. **All primary keys are UUIDs**, never auto-increment integers — across
    every table, no exceptions. This is a hard rule, not a default; don't
    add a table that deviates from it.

13. **Every schema change ships an Alembic migration with a working
    `downgrade()`.** Never edit a migration that's already been committed —
    write a new one. See `AGENTS.md` rule 2.

14. **No cascade delete on `artifacts.collection_id`.** The foreign key has
    no `ondelete` configured, and collection deletion in the app is a
    *soft* delete (`Collection.is_active = False` — `delete_collection` in
    `backend/app/api/collections.py`), so this is rarely exercised. If you
    ever add a hard-delete path for collections, you must delete or reassign
    their artifacts first, or the `DELETE` will fail on the FK constraint.

15. **Artifacts, profiles, and doc_cache entries use soft-delete, not hard
    delete.** `session.delete()` is never called on these models — instead,
    `deleted_at` is set to `datetime.now(UTC)`. Every list/get query filters
    on `deleted_at == None` to exclude soft-deleted rows. This matches the
    existing pattern for collections (`is_active = False`) and API tokens
    (`is_active = False`). Enforced in `backend/app/api/collections.py`
    (`bulk_delete_artifacts`), `backend/app/api/profiles.py`
    (`delete_profile`), and `backend/app/api/doc_cache.py`
    (`delete_cache_entry`).

16. **`Profile.additional_collection_ids` and `disabled_artifact_ids` are
    JSON UUID lists, not real foreign keys.** The database will not stop you
    from storing a reference to a collection that's later deleted or made
    private. `compile_profile()` resolves these at request time and
    silently skips anything it can't find — it does not error. Don't assume
    referential integrity here that the schema doesn't actually provide.

17. **`Collection.artifact_count` is a denormalized cache**, not a computed
    value. Every route that adds or removes artifacts from a collection
    (bulk import, bulk delete, bulk export's target) must update it, or it
    silently drifts from the true count.

## A gap that's accepted, not fixed

**Profile visibility doesn't cascade to its collections.** A profile marked
`is_public=True` can reference a collection that's private to its owner (or
becomes private later). `compile_profile()` does not re-check the
visibility of the collections it pulls from — the profile's own
owner/public flag is the only gate checked before compilation. Concretely:
if you can see a public profile, you can compile it and see the (otherwise
private) artifacts it references. This is a deliberate simplification
consistent with "no granular per-resource sharing" (see
[ADR-0003](adr/0003-ownership-based-authorization.md)), not an oversight —
but it's worth knowing before you rely on collection privacy as a hard
boundary.
