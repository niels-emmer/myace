# ADR-0015: Referenced packs freeze to a snapshot when unavailable

**Status:** Proposed

## Context

A profile ("setup") references collections ("packs") by id; it does not copy
their contents. `Profile.base_collection_id` is a real foreign key, while
`additional_collection_ids` is a JSON list the database never enforces. That
reference model is what lets a setup track a pack as the pack improves, and
it is what makes "one setup, several packs" cheap.

It also has a failure mode. Before this decision, `compile_profile()`
resolved each referenced collection and **silently skipped** any it could not
find, that was soft-deleted, or that the requesting user could not read. So
when a pack owner unpublished a pack — `POST /collections/{id}/unpublish`
sets `visibility="private"` and `published=False` (ADR-0013) — every setup
that referenced it simply lost those artifacts, with no error and no
warning. That is exactly the silent-loss class of bug that the compile-time
warnings mechanism (ADR-0009's sibling work, AGENTS.md rule 32) and the
name-collision warning exist to prevent.

The v2.0 onboarding/usage revamp makes reference the primary path ("Use this
pack" adds it to a setup), so this has to be fixed before that path becomes
the default.

## Decision

### Reference, not fork

Packs remain referenced, not copied. Using a pack does **not** duplicate its
artifacts into the user's account, does not fork it, and never writes to
another user's data. A fork ("Customize a copy") remains an explicit,
separate user action. The only new persistent state is a small snapshot on
the *referencing* profile.

### Freeze mechanism

`Profile.pack_snapshots` is a JSON-encoded `Text` column (default `"{}"`),
shaped:

```json
{
  "<collection_id>": {
    "artifact_ids": ["<uuid>", "..."],
    "hash": "<sha256 of the sorted ids>",
    "captured_at": "<iso8601>"
  }
}
```

- Captured/refreshed on **profile create and update**, by
  `capture_pack_snapshots()`.
- Only for referenced collections the requesting user does **not** own.
  An owned collection is always readable by its owner, so freezing it would
  add only a stale second copy.
- The captured set is the enabled, live artifact ids — i.e. the set a
  non-owner compile would resolve at that moment.
- `hash` is sha256 over the sorted ids joined by newlines; `captured_at`
  records when the freeze was taken so a UI can say "frozen copy from …".

`compile_profile()` resolves each referenced collection as before. If it is
missing, inactive, or (when `requesting_user` is given) unreadable, the
compiler instead loads the artifacts named by the snapshot and emits a
`ValidationIssue(code="pack_unavailable")`. With no snapshot it still skips
the collection, but now also emits `pack_unavailable`. Nothing is silent
anymore.

### Authorization-bypass scope

Loading frozen artifacts **does not** re-check collection read access — that
is the point, and it is the one deliberate compile-time auth bypass. It is
kept safe by four constraints:

1. **The client never supplies the snapshot.** `ProfileCreate` has no
   `pack_snapshots` field; the value is written only server-side during
   create/update. A user cannot point a snapshot at an artifact id they could
   not read.
2. **Ids were captured only while the profile owner could read the pack.**
   `create_profile`/`update_profile` validate every referenced collection
   with `authorize_access` (owner, public, or admin) before capturing.
3. **The reload is pinned to the same collection.** Artifacts are fetched
   with `Artifact.id.in_(ids) AND Artifact.collection_id == cid`, so a
   snapshot can never pull an artifact out of a different collection.
4. **It returns only the artifact's compiled content** — no collection
   metadata, ratings, comments, or other rows.

Artifacts are soft-deleted at most (AGENTS.md rule 15), never hard-deleted,
so a frozen id keeps resolving after the pack is gone. A later soft-delete
of an individual artifact does **not** remove it from the frozen set; that
is the intended meaning of "frozen". The profile's own
`disabled_artifact_ids` toggles still apply.

## Alternatives considered

- **Auto-fork on unpublish** — rejected. It writes new rows into the user's
  account without asking, silently changes ownership semantics, and grows
  storage on every unpublish. Users who want a copy have an explicit action.
- **A `profile_pack_refs` join table instead of a JSON column** — rejected
  for now. The snapshot is always read and written as a whole and never
  queried element-wise, matching the existing JSON-in-`Text` convention
  (`additional_collection_ids`, `disabled_artifact_ids`, ADR-0010). If a
  future feature needs "which setups reference pack X", that is the point to
  normalize.
- **Grant public read to unpublished packs so references keep resolving** —
  rejected. It defeats unpublish/deny and widens the public-read surface for
  a problem that only affects existing references.
- **Keep the silent skip** — rejected. It is the bug being fixed.

## Failure modes and limits

- **Stale frozen copy.** If a pack changes after capture, the setup keeps
  the captured set until the profile is updated (which refreshes the
  snapshot) or the user forks. This is deliberate: the freeze is a copy at
  reference time, not a live mirror. `captured_at` is recorded so the UI can
  be honest, and the warning tells the user a frozen copy is in use.
- **Empty snapshot.** A pack with no enabled artifacts at capture time
  freezes to an empty list; the pack still contributes nothing, but the
  warning still fires so it isn't mistaken for "working".
- **Corrupt JSON.** `_parse_pack_snapshots()` treats an unparseable value as
  "no snapshots" rather than failing compilation.
- **Concurrent create/update.** Two simultaneous writes can race on the
  snapshot; last write wins, and the worst case is a stale-but-valid set —
  the same outcome as an unrefreshed snapshot.
- **Unknown adapter names in `target_frameworks`** are dropped silently on
  write (never 422), so an admin disabling or removing an adapter cannot
  brick an existing setup.

## Consequences

- Unpublishing or soft-deleting a referenced pack no longer silently guts a
  setup: it compiles from the frozen set and reports `pack_unavailable`.
- Setups gain a small amount of storage (ids, a hash, a timestamp) but no
  copied artifact bodies.
- `ProfileCreate`/`ProfileRead` gain `target_frameworks`, and
  `Collection` gains `license`; `POST /collections/{id}/use` records
  references (as `download_count`) and `profile_installs` records install
  *claims*. None of those are verification — `SyncStatus` remains the only
  verified source (see `docs/invariants.md` 24–25).

## Related

- [ADR-0003](0003-ownership-based-authorization.md) — ownership + visibility
  authorization, which this ADR locally bypasses for frozen ids.
- [ADR-0008](0008-collection-moderation-state-machine.md),
  [ADR-0013](0013-post-hoc-unpublish.md) — the unpublish flow this protects
  against.
- [ADR-0009](0009-manifest-based-drift-detection.md) — the other
  "claim vs. verification" distinction in this codebase.
