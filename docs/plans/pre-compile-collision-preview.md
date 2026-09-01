# Plan: Pre-Compile Name-Collision Preview in Profile Composer

## Status

**Not started — planned.** This is a follow-up feature to be executed on its
own feature branch after the current session's work (base/additional
collection `handoff_to` metadata, new Database + QA/Test collections, and
rule-29 collision fixes) merges to `main`.

## Problem

Users composing a profile (one base + several additional collections) often
hit `name_collision` warnings — but only **at compile time**, in the
`/build/compile` page's amber panel (`TargetExporter.tsx`). The warning is
advisory and dismissible (rule 32), so nothing breaks, but the discovery
happens late: the user has already saved the profile, navigated to compile,
and picked a target before learning that two of their collections define an
artifact with the same name and one silently wins.

The shipped starter set is collision-free (verified: software-engineer + all
19 additional collections compiles with zero warnings), so the collisions
users see come from **community collections** and **their own imported
collections**, which can define common-named artifacts (`builder`,
`code-standards`, `security-checklist`, etc.). Those are exactly the cases
where a preview at profile-edit time adds the most value.

## Goal

Show the user, **while they are composing a profile** (in
`ProfileComposer.tsx`'s create form), which artifact names collide across
the selected base + additional collections, which collection wins, and let
them act on it (disable the losing artifact, or drop the collection) before
saving — instead of discovering it at compile time.

## Non-goals

- **No backend changes.** The collision logic already lives in
  `compile_profile()` (`backend/app/services/compiler.py`); the preview
  replicates the same name-dedup rule client-side. No new endpoint, no
  schema change, no migration.
- **No change to compile-time behavior.** The `name_collision` warning stays
  advisory and non-blocking (rule 32). This feature is a *preview* of the
  same information, not a new gate.
- **No change to the dedup semantics.** Later collections still override
  earlier ones by name (rule 29). The preview only *surfaces* this, it
  doesn't change it.
- **No cross-collection `handoff_to` resolution preview.** Dangling-handoff
  warnings are a separate concern (rule 34) and out of scope for this plan.

## Approach

### Client-side collision detection (mirror of rule 29)

Replicate `compile_profile()`'s dedup step in the frontend:

1. For the selected `base_collection_id` + `additional_collection_ids`,
   fetch each collection's artifacts via `collectionsApi.getArtifacts(cid)`
   (already available, returns `Artifact[]` with `name`, `artifact_type`,
   `is_enabled`, `collection_id`).
2. Iterate collections in profile order (base first, then additional in the
   order they appear in `additional_collection_ids`), maintaining a
   `Map<string, Artifact>` keyed by artifact `name`.
3. When an artifact's name is already in the map **and** its
   `collection_id` differs from the existing entry's, record a collision:
   `{ name, losingCollection, winningCollection, artifactType }`.
4. Overwrite the map entry (later wins), exactly like the backend.

This is a pure function — `detectNameCollisions(collections, artifactsByCollection)`
— unit-testable without React.

### Where it renders

In `ProfileComposer.tsx`'s create form, below the collection pickers
(`ProfileForm.tsx`). A compact amber panel (matching `TargetExporter.tsx`'s
warning styling) listing each collision:

> **Name collision:** `builder` is defined in both *Software Engineer* and
> *My Community Pack*; *My Community Pack* wins.

With an action per collision: **"Disable in this profile"** — which adds the
losing artifact's id to `form.disabled_artifact_ids` (the field already
exists on `ProfileCreate` and is respected by `compile_profile()` via
`include_disabled`/`disabled_ids`).

### Data fetching

- The form already has `collections` loaded (for the pickers).
- Add a `useQueries` fan-out for `getArtifacts` over the *selected*
  collections only (base + checked additional), keyed
  `['artifacts', cid]` — consistent with the existing React Query key
  convention (rule 12).
- Recompute the collision list via `useMemo` whenever the selection or the
  artifact data changes. No new query keys beyond the per-collection ones.

### Edge cases

- **No base selected yet** → no preview (nothing to compose).
- **A collection with zero artifacts** → contributes nothing; skip.
- **Disabled artifacts already in `disabled_artifact_ids`** → excluded from
  the dedup map (they won't be compiled, so they can't collide). This keeps
  the preview consistent with what `compile_profile()` actually does.
- **Same-name artifacts within a single collection** (skill vs rule) →
  *not* surfaced here: the backend only warns on cross-collection overrides
  (rule 29's `name_collision` fires on `source_collection_id` mismatch).
  The preview mirrors that exactly — within-collection collisions are a
  separate, silent dedup and out of scope.
- **Collision resolved by disabling** → the panel updates immediately
  (the disabled id is in the map exclusion), so the user sees the warning
  clear as they act.

## Files touched

| File | Change |
|------|--------|
| `frontend/src/lib/collisions.ts` (new) | `detectNameCollisions()` pure function + types |
| `frontend/src/lib/collisions.test.ts` (new) | Unit tests for the dedup logic |
| `frontend/src/pages/ProfileComposer.tsx` | `useQueries` fan-out for selected collections' artifacts; `useMemo` collision list; render panel |
| `frontend/src/components/ProfileForm.tsx` | (optional) render the panel here instead, if it's cleaner to colocate with the pickers |
| `frontend/src/pages/ProfileComposer.test.tsx` (new or existing) | Component test: collisions appear, disable action adds to `disabled_artifact_ids` |

No backend, no docs/AGENTS.md changes (this is a pure UX addition; the
compile-time warning behavior is unchanged).

## Acceptance criteria

1. With a base + an additional collection that share an artifact name, the
   create form shows a collision panel naming both collections and the
   winning one — before the profile is saved.
2. Clicking "Disable in this profile" on a collision adds the losing
   artifact's id to `disabled_artifact_ids` and the collision disappears
   from the panel.
3. With a collision-free selection (e.g. software-engineer + any starter
   additional), no panel renders.
4. The panel matches the compile-time warning's semantics exactly: same
   dedup order (base first, additional in order), same "later wins" rule,
   same cross-collection-only trigger.
5. `detectNameCollisions()` is unit-tested for: no collision, cross-
   collection collision, later-wins ordering, disabled-artifact exclusion,
   and within-collection same-name (not flagged).
6. Frontend suite passes (`npm run test`), lint clean (`npm run lint`).

## Verification

- `cd frontend && npm run test` — new unit + component tests pass.
- `cd frontend && npm run lint` — clean.
- Manual: compose software-engineer + a community collection that defines a
  `builder` artifact; confirm the panel appears in the create form, the
  disable action works, and the saved profile compiles without the
  `name_collision` warning for that artifact.

## Open questions

1. **Panel placement:** in `ProfileForm.tsx` (colocated with the pickers,
   always visible while composing) vs. `ProfileComposer.tsx` (below the
   form). Leaning `ProfileForm.tsx` for colocation, but the form component
   currently has no data-fetching — the fan-out would live in
   `ProfileComposer.tsx` and pass results down. Decide during implementation.
2. **Should the panel also appear on the profile *edit* path?** The current
   create form is the only composition surface; profile editing happens via
   PATCH on the detail page. Out of scope for v1 unless trivial.
3. **Disable vs. drop:** "Disable in this profile" is the surgical action.
   A secondary "remove collection" hint (pointing at the picker) may be
   worth adding if the collision is broad (many artifacts from one
   collection). Defer to implementation judgment.