# Plan: Collection Action Buttons (Delete, Share, Upload)

## Feature Summary

Add three action buttons to the collection detail page (next to the existing
"Edit" button):

1. **Delete** — soft-delete the collection with a confirmation modal
2. **Share** — toggle collection visibility between `private` and `public`
3. **Upload to GitHub** — grayed-out placeholder for future GitHub-hosted
   collections

## Acceptance Criteria

- [ ] Delete button visible next to Edit on collection detail page
- [ ] Delete shows a confirmation modal before proceeding
- [ ] Confirming delete calls `DELETE /api/v1/collections/{id}` (soft-delete)
- [ ] After delete, user is navigated back to the collections list
- [ ] Share button visible next to Edit on collection detail page
- [ ] Share opens a modal showing current visibility with toggle to public
- [ ] Toggling visibility calls `PATCH /api/v1/collections/{id}` with
      `visibility` field
- [ ] Backend `CollectionUpdate` schema accepts `visibility` field
- [ ] Upload to GitHub button visible next to Edit
- [ ] Upload button is disabled/grayed-out with "Coming soon" tooltip
- [ ] All buttons respect the editing state (hidden during inline edit)
- [ ] Backend tests pass
- [ ] Frontend tests pass
- [ ] Security audit: no new auth bypass, no hardcoded secrets
- [ ] Documentation: invariants, data model, AGENTS.md updated if needed

## Epics

### Epic 1: Delete Collection Button

**Files to change:**
- `frontend/src/pages/CollectionDetail.tsx` — add delete button + modal
- `frontend/src/pages/CollectionDetail.test.tsx` — new test file

**Backend:** Already exists (`DELETE /api/v1/collections/{id}`). No changes needed.

**Steps:**
1. Add `deleteCollectionMutation` using `collectionsApi.delete`
2. Add `showDeleteCollectionModal` state
3. Add "Delete" button next to "Edit" (red/destructive styling)
4. Add confirmation modal: "Are you sure? This will permanently disable this
   collection and hide it from all views."
5. On confirm: call mutation, on success navigate to `/collections`
6. Write frontend tests

### Epic 2: Share Collection Button

**Files to change:**
- `backend/app/models/collection.py` — add `visibility` to `CollectionUpdate`
- `frontend/src/pages/CollectionDetail.tsx` — add share button + modal
- `frontend/src/types/index.ts` — add `CollectionUpdate` with `visibility`

**Steps:**
1. Add `visibility: str | None = None` to `CollectionUpdate` in backend
2. Add `visibility` to the frontend `CollectionUpdate` type
3. Add `showShareModal` state and share button
4. Add share modal showing current visibility with toggle to public/private
5. On confirm: call `collectionsApi.update` with `{ visibility: 'public' | 'private' }`
6. Write frontend tests

### Epic 3: Upload to GitHub Button (Placeholder)

**Files to change:**
- `frontend/src/pages/CollectionDetail.tsx` — add disabled upload button

**Steps:**
1. Add "Upload to GitHub" button next to Edit
2. Button is `disabled` with `opacity-50 cursor-not-allowed`
3. Title/tooltip: "GitHub-hosted collections — coming soon"
4. No modal or backend changes needed

## Verification

- Run `cd backend && pytest` — all existing tests pass
- Run `cd frontend && npx vitest run` — all existing + new tests pass
- Run `cd frontend && npx tsc --noEmit` — no type errors
- Security audit: no new routes, no new data exposure, no hardcoded secrets
- Documentation: verify invariants.md, data-model.md, AGENTS.md are current
