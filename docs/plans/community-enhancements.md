# Plan: Community Enhancements

**Status: Not started.** This is a live task list for an unattended build. Work
through the epics in order on a single branch, committing after each one
(see [Branch & Workflow](#branch--workflow)). Do not skip the documentation
epic at the end — it is part of "done," not cleanup.

## Overview

Seven related upgrades to the community-collections feature:

1. New `moderator` role (alongside `user`/`admin`), assignable from the admin
   Users table.
2. Community moderation actions (approve/deny submissions, edit meta, delete
   comments) are restricted to the collection owner (scoped to their own
   collection's comments only), moderators, and admins — never to arbitrary
   users.
3. 1–5 star ratings on collections; community listing pages become sortable
   by rating, downloads, or name.
4. Comments on collections, deletable by the collection owner, moderators,
   or admins (and by the comment's own author).
5. Moderators/admins can edit a submitted collection's name, description,
   and category (metadata only — never artifact content).
6. Publishing a collection now goes through a `submitted → approved/denied`
   moderation queue instead of going live immediately; the submitter gets an
   email on the decision (with a reason, if denied) when they have an email
   on file.
7. Users can opt in, per-profile, to email notifications when someone
   downloads or comments on their submission.

## Decisions Locked In

These were confirmed with the requester before writing this plan. An
unattended build should treat them as settled — do not re-litigate, just
implement:

- **Moderator scope is community-only.** Moderators can review/approve/deny
  submissions, edit collection meta, and delete comments. They get **no**
  other admin capability (user management, system settings, adapter
  toggles, etc.). Enforced by a new `require_moderator_or_admin` dependency
  that is distinct from `require_admin` — never widen it to full admin
  parity.
- **Owners never self-approve.** The collection owner can manage their own
  collection's comments (delete) and edit its metadata *before* submission,
  but only a moderator or admin can approve/deny a `submitted` collection.
  This resolves the apparent tension between requirement 2 (owner has
  "moderation" access) and requirement 6 (submissions go through a queue):
  "moderation access" for an owner means comment/pre-submission management,
  not the approve/deny decision itself.
- **Resubmission after denial is allowed.** A denied collection reverts to
  `draft`-like status (visible only to the owner), the owner can edit it,
  and re-submitting sends it back into the queue for a fresh review. The
  prior denial reason is kept as history (not shown to other users).
- **Existing public collections are grandfathered.** The migration that
  introduces `moderation_status` auto-marks every collection that is
  currently `published=True AND visibility="public" AND is_active=True`
  (this includes all starter packs, which are seeded with
  `published=True`) as `approved`. Nothing currently visible in the
  community disappears or needs re-review.
- **Download notifications are a daily digest**, not per-download emails —
  avoids flooding a popular collection owner's inbox. Comment notifications
  are sent immediately per comment (comments are much lower-volume than
  downloads).
- **Category stays free text.** It is not being converted to a `Literal`/enum
  in this plan (seed data already uses ad hoc category strings — see
  `seed_collections.py`). Moderators can edit it to any string. Out of
  scope; do not add an enum unless asked.

## Branch & Workflow

- Branch: `feat/community-enhancements`, created from `main`.
- All eleven epics below are built on this one branch, **one commit per
  epic**, in order (later epics depend on earlier ones — the role model and
  moderation state machine are foundational).
- Follow `AGENTS.md` rule 7: conventional-commit messages (`feat:`, `docs:`,
  etc.), no direct pushes to `main`, PR requires passing CI + one approving
  review before merge.
- Follow `AGENTS.md` rule 2 for every schema change: one reversible Alembic
  migration per epic that touches the DB (don't bundle multiple epics'
  columns into one migration — keeps `downgrade()` meaningful and keeps
  epic commits self-contained).
- Run `ruff check .` + `mypy app` (backend) and `npm run lint` (frontend)
  before each commit; run `pytest` (backend/cli) after each backend epic and
  keep the suite green throughout — don't defer test fixes to the docs
  epic.
- Use the project's existing skills/agents as normal while executing this
  plan: `code-review` (or `/code-review`) after each epic before committing,
  and the `security-review` skill once before opening the PR (this feature
  touches authz on every epic — worth a dedicated pass). Use the `Explore`
  agent for any one-off "where is X" lookups called out below instead of
  grepping manually, per this repo's own agent-usage guidance.

### Preflight checks (do these once, at the start of Epic 1)

A couple of facts this plan relies on were not pinned down to the exact
line during planning — confirm them before writing migrations so you don't
create a duplicate head or guess at an existing route:

- Run `alembic heads` in `backend/` to get the exact current head revision
  ID for `down_revision` in the first new migration (plan research found
  `f6a7b8c9d0e1_add_smtp_and_password_reset.py` as the likely latest, but
  confirm).
- Find the existing owner-facing collection update route (likely
  `PATCH /collections/{id}` in `backend/app/api/collections.py`) and check
  what fields it currently allows the owner to change. Epic 5's new
  moderator-only meta-edit endpoint should mirror its validation, and
  Epic 6's resubmission UI needs to know whether the owner already has a
  "edit name/description/category" form to reuse or needs a small one
  added.

## Architecture Decisions

### Role model: additive `role` column, `is_admin` untouched

Add `User.role: Literal["user", "moderator", "admin"]` (default `"user"`)
as a **new** column rather than replacing `is_admin`. `is_admin` stays
exactly as-is and continues to gate every existing `require_admin` /
`authorize_access` bypass — changing that plumbing across the whole
authz surface is out of scope and risky. The two stay in sync one-directionally:
whenever `role` is set via the new admin endpoint, `is_admin = (role ==
"admin")` is written in the same transaction. `role` is the only field a
new `require_moderator_or_admin` dependency reads. This is ADR-worthy
(changes the shape of the auth/authz data model) — write it up as
**ADR-0007** in the documentation epic.

### Moderation state machine

`Collection.moderation_status: Literal["draft", "submitted", "approved", "denied"]`,
default `"draft"`. State transitions:

```
draft ──submit──> submitted ──approve──> approved
                       │
                       └──deny(reason)──> denied ──edit + resubmit──> submitted
```

- `draft`: not public, not in any queue. Owner can edit freely.
- `submitted`: owner-editing locked (no meta edits while under review —
  simplest way to avoid a moderator reviewing content that changes under
  them); visible in the moderation queue to moderators/admins only.
- `approved`: `published=True`, `visibility="public"`, visible in the
  community. This is the *only* path that flips `published`/`visibility` —
  the old self-serve behavior described in `AGENTS.md` rule 18 no longer
  applies and that rule must be rewritten in the docs epic, not left stale.
- `denied`: not public; `moderation_reason` holds the reviewer's note,
  visible only to the owner; owner can edit and resubmit (→ back to
  `submitted`).

This is also ADR-worthy (changes the collection publishing lifecycle,
expensive to reverse once collections exist in these states) — write up as
**ADR-0008**.

### Ratings are denormalized onto `Collection`

Store `Collection.avg_rating: float` (default `0.0`) and
`Collection.rating_count: int` (default `0`), recomputed transactionally on
every rating write/delete, same pattern as the existing `download_count`
counter. This keeps sorting-by-rating on listing pages a plain indexed
`ORDER BY` instead of a join+aggregate on every page load. The
per-user `CollectionRating` rows remain the source of truth; the two
denormalized columns are a cache of their aggregate.

### Download digest is a cron-invoked script, not an in-process scheduler

The backend has no task scheduler today (no APScheduler/Celery). Rather
than add one for a single daily job, add
`backend/app/scripts/send_download_digests.py`, runnable as
`python -m app.scripts.send_download_digests`, intended to be invoked once
a day by the host's crontab (VPS deployment) — document this in
`docs/deployment.md` next to the existing compose-file instructions. To
compute "downloads since last digest" without a new events-log table, add
`Collection.last_digest_download_count: int` (default `0`) and
`Collection.last_digest_sent_at: datetime | None`; the script diffs
`download_count - last_digest_download_count` per collection, emails if
positive and the owner opted in, then updates the two columns.

## Epics

### Epic 1: Backend — Role model

**Files:**
- `backend/app/models/user.py` — add `role` field + `UserRead`/`UserUpdate` exposure (read-only on `UserUpdate`; role changes go through the dedicated admin endpoint, not self-service)
- `backend/app/core/deps.py` — add `require_moderator_or_admin`
- `backend/app/api/auth.py` — add `PATCH /auth/users/{user_id}/role` (admin-only)
- `backend/alembic/versions/` — new migration

**Tasks:**
1. Run the preflight `alembic heads` check; add `role: str` column
   (`sa.String`, `server_default='user'`, not nullable) to `users` in a new
   migration; data-migration step backfills `role='admin' WHERE
   is_admin = true`; `downgrade()` drops the column.
2. `User.role: Literal["user", "moderator", "admin"] = "user"` on the
   SQLModel; add to `UserRead`.
3. `require_moderator_or_admin(current_user: User = Depends(get_current_user)) -> User` in `deps.py`, raising 403 if `current_user.role not in ("moderator", "admin")`.
4. `PATCH /auth/users/{user_id}/role` — `Depends(require_admin)`, body
   `{role: Literal["user","moderator","admin"]}`, mirrors the existing
   `set_user_active` self-modification guard (`auth.py` — 400 if
   `user_id == current_user.id`) for the same admin-lockout-avoidance
   reason documented there. Sets `role` and syncs `is_admin = (role ==
   "admin")` in one commit.
5. Tests: role change happy path, self-modification blocked, non-admin
   gets 403, `require_moderator_or_admin` unit-style coverage via a
   trivial protected test route or an existing moderator-gated route once
   Epic 3 lands (fine to add this test in Epic 3 instead if it's more
   natural there).

**Commit:** `feat: add moderator role and admin role-management endpoint`

### Epic 2: Frontend — Role management UI

**Files:**
- `frontend/src/pages/SystemSettings.tsx` — Users table
- `frontend/src/lib/api.ts` — `adminApi.setUserRole`
- `frontend/src/types/index.ts` — add `role` to the `User` type

**Tasks:**
1. Add `role: 'user' | 'moderator' | 'admin'` to the frontend `User` type.
2. `adminApi.setUserRole(id, role)` calling the new `PATCH` route.
3. In the Users table, replace/augment the `is_admin` badge with a role
   `<select>` (user/moderator/admin), wired to a `setUserRoleMutation`
   sibling to the existing `setUserActiveMutation`. Disable it for the
   row matching the logged-in admin (same `isSelf` guard already used for
   the active-toggle button).
4. Manual verification: log in as admin, promote a test user to
   moderator, confirm the badge/select updates and a re-fetch shows the
   new role; demote back to user.

**Commit:** `feat: add role selector to admin Users table`

### Epic 3: Backend — Moderation state machine

**Files:**
- `backend/app/models/collection.py` — new fields
- `backend/app/api/collections.py` — rework `POST /{id}/publish`
- `backend/app/api/moderation.py` — new router (queue, approve, deny)
- `backend/app/main.py` — register new router
- `backend/app/services/email.py` — `build_moderation_approved_email`, `build_moderation_denied_email`
- `backend/alembic/versions/` — new migration (with grandfather backfill)

**Tasks:**
1. Migration: add `moderation_status` (`server_default='draft'`),
   `moderation_reason: str | None`, `submitted_at: datetime | None`,
   `moderated_at: datetime | None`, `moderated_by: uuid | None` (FK
   `users.id`, nullable) to `collections`. Data step:
   `UPDATE collections SET moderation_status='approved' WHERE published = true AND visibility = 'public' AND is_active = true`
   (covers starter packs too, since they're seeded with
   `published=True`/`visibility='public'`). `downgrade()` drops all five
   columns.
2. `Collection.moderation_status: Literal["draft","submitted","approved","denied"] = "draft"` + the other four fields on the SQLModel; extend `CollectionRead`.
3. Rework `POST /collections/{id}/publish`: now means "submit for
   review." Requires `moderation_status in ("draft", "denied")` (409 or
   400 otherwise — e.g. already submitted/approved). Sets
   `moderation_status="submitted"`, `submitted_at=now()`. Does **not**
   touch `published`/`visibility` anymore — remove that logic from this
   endpoint entirely. Still accepts the existing
   `{category, publish_name, publish_description}` body for a last edit
   at submission time (unchanged from today).
4. New `backend/app/api/moderation.py`, mounted at `/api/v1/moderation`,
   every route behind `Depends(require_moderator_or_admin)`:
   - `GET /moderation/queue` — collections with `moderation_status="submitted"`, newest-submitted-first by default (sorting itself is Epic 9's `sort` param, but stub the query so Epic 9 only needs to add the param).
   - `POST /moderation/{collection_id}/approve` — sets `moderation_status="approved"`, `published=True`, `visibility="public"`, `moderated_by=current_user.id`, `moderated_at=now()`. If `collection.owner.email`, send `build_moderation_approved_email`.
   - `POST /moderation/{collection_id}/deny` — body `{reason: str}` (required, non-empty). Sets `moderation_status="denied"`, `moderation_reason=reason`, `moderated_by`, `moderated_at`. Leaves `published=False`. If `collection.owner.email`, send `build_moderation_denied_email(reason)`.
   - Both approve/deny 404 if the collection isn't currently `submitted` (can't approve a draft, can't double-approve).
5. Email send failures must not fail the approve/deny request — wrap in
   try/except, log, still commit the DB state change (matches the
   existing pattern where `EmailSendError` is caught around the
   password-reset email call in `auth.py`).
6. Tests: submit → queue visibility (mod/admin see it, plain user via
   direct `GET /moderation/queue` gets 403), approve flips
   published/visibility, deny sets reason and leaves it private, owner
   cannot approve their own collection (403 for an owner who is not
   also mod/admin), re-submit-after-denial transitions correctly,
   double-approve returns 404/409, email failure doesn't roll back the
   state change (mock `send_email` to raise).

**Commit:** `feat: replace self-serve publish with moderation queue`

### Epic 4: Frontend — Moderation queue page

**Files:**
- `frontend/src/pages/ModerationQueue.tsx` — new page
- `frontend/src/lib/api.ts` — `moderationApi.getQueue/approve/deny`
- `frontend/src/components/Layout.tsx`, `frontend/src/App.tsx` — nav item + route, gated on `role in ('moderator','admin')`
- `frontend/src/pages/CollectionDetail.tsx` — update "Publish" button copy/state to reflect "submitted, pending review" instead of immediately-public; show the denial reason (if any) to the owner with an "edit & resubmit" affordance

**Tasks:**
1. New page listing submitted collections (name, owner, submitted_at,
   category), each with Approve and Deny actions; Deny opens a small
   modal requiring a non-empty reason.
2. Nav: add "Moderation" item visible only when `user.role` is
   `moderator` or `admin` (same conditional-rendering pattern already
   used for the admin-only "System" nav item).
3. `CollectionDetail.tsx`: Publish button becomes "Submit for review"
   when `moderation_status` is `draft`/`denied`, shows a "Pending
   review" badge when `submitted`, shows the denial reason + an
   "Edit and resubmit" path when `denied` (reuses whatever edit form
   Epic 5/6 or the existing owner-edit form provides).
4. Manual verification: as a moderator, approve one test submission and
   deny another with a reason; log in as the submitting owner and
   confirm the denial reason is visible and resubmission works.

**Commit:** `feat: add moderation queue page`

### Epic 5: Backend — Moderator meta-edit

**Files:**
- `backend/app/api/moderation.py` — extend
- `backend/app/models/collection.py` — `CollectionMetaUpdate` schema if not already covered by an existing update schema

**Tasks:**
1. `PATCH /moderation/{collection_id}/meta` — `Depends(require_moderator_or_admin)`, body allows partial `{name?, description?, category?}` only (explicitly not `git_url`/`git_branch`/artifact content — this only edits the three metadata fields named in the requirement). Works on any collection regardless of `moderation_status` (a moderator should be able to fix a typo on an already-approved collection too, not just during review).
2. Tests: mod/admin can edit meta on someone else's collection; plain
   user and the collection's own owner (who is neither mod nor admin)
   get 403 on this specific endpoint (owner still edits via their own
   existing route, unaffected); partial update only touches provided
   fields.

**Commit:** `feat: allow moderators to edit community collection metadata`

### Epic 6: Frontend — Meta-edit UI

**Files:**
- `frontend/src/pages/CommunityCollectionDetail.tsx` — edit form, visible only to mod/admin viewers
- `frontend/src/pages/ModerationQueue.tsx` — optional inline edit-before-approve
- `frontend/src/lib/api.ts` — `moderationApi.updateMeta`

**Tasks:**
1. On the community collection detail page, show an "Edit metadata"
   affordance (name/description/category form) only when
   `user.role in ('moderator','admin')`.
2. Manual verification: as moderator, edit a public collection's
   category from its community detail page and confirm it persists and
   sorts/filters correctly afterward.

**Commit:** `feat: add moderator metadata edit UI`

### Epic 7: Backend — Ratings & comments

**Files:**
- `backend/app/models/collection_rating.py`, `backend/app/models/collection_comment.py` — new models
- `backend/app/models/__init__.py` — export
- `backend/app/api/collections.py` (or a new `ratings.py`/`comments.py`) — endpoints
- `backend/app/services/email.py` — `build_comment_notification_email`
- `backend/alembic/versions/` — new migration

**Tasks:**
1. Migration: `collection_ratings` table (`id` uuid pk, `collection_id`
   FK, `user_id` FK, `stars` int with a `CHECK (stars BETWEEN 1 AND 5)`
   constraint, `created_at`, `updated_at`, **unique constraint on
   `(collection_id, user_id)`**); `collection_comments` table (`id` uuid
   pk, `collection_id` FK, `user_id` FK, `body` text capped at 2000
   chars — enforce at the Pydantic schema layer, not just DB — `created_at`,
   `deleted_at` nullable for soft-delete per rule 15); add
   `Collection.avg_rating: float = 0.0` and
   `Collection.rating_count: int = 0` in the same migration.
2. `PUT /collections/{id}/rating` — auth required; 400 if
   `current_user.id == collection.owner_id` (no self-rating); 404 unless
   `collection.moderation_status == "approved"` (can't rate what isn't
   public); upserts the caller's `CollectionRating` row and recomputes
   `avg_rating`/`rating_count` on `Collection` transactionally.
   `DELETE /collections/{id}/rating` removes the caller's rating and
   recomputes. `GET /collections/{id}/rating` returns the aggregate plus
   the caller's own rating if authenticated.
3. `POST /collections/{id}/comments` — auth required, same
   `moderation_status == "approved"` gate, body `{body: str}` (1–2000
   chars). On success, if `collection.owner.notify_on_comment` (Epic 10)
   and `collection.owner.email`, send
   `build_comment_notification_email` immediately (same
   try/except-and-log pattern as Epic 3's approve/deny emails — a failed
   notification must never fail the comment creation).
   `GET /collections/{id}/comments` — list non-deleted comments,
   newest-first, public (no auth required, matches public collection
   visibility).
   `DELETE /collections/{id}/comments/{comment_id}` — allowed for: the
   comment's own author, the collection owner, or
   `current_user.role in ("moderator","admin")`. Soft-delete
   (`deleted_at = now()`), never hard-delete (rule 15).
4. Tests: rating upsert changes existing rating rather than duplicating;
   self-rating blocked; rating a non-approved collection 404s;
   avg/count recompute correctly across multiple raters and after a
   delete; comment creation triggers the email only when the preference
   is on and email is present (mock `send_email`, assert
   called/not-called); comment deletion allowed for author/owner/mod/admin
   and denied for an unrelated user; deleted comments excluded from the
   list endpoint.

**Commit:** `feat: add collection ratings and comments`

### Epic 8: Frontend — Ratings & comments UI

**Files:**
- `frontend/src/pages/CommunityCollectionDetail.tsx` — star widget + comment thread
- `frontend/src/lib/api.ts` — rating/comment API methods
- `frontend/src/types/index.ts` — types

**Tasks:**
1. 1–5 star input (click to set/change your rating) plus the
   collection's `avg_rating`/`rating_count` displayed read-only nearby.
2. Comment list + a simple textarea + submit button below it; each
   comment shows a delete icon only when the viewer is authorized
   (author, owner, or mod/admin — mirror the backend rule so the button
   doesn't appear and then 403).
3. Manual verification: rate a collection as a non-owner user, confirm
   the aggregate updates; leave a comment as one user, delete it as a
   different (owner) user; confirm the delete icon is hidden for an
   unrelated third user.

**Commit:** `feat: add ratings and comments UI`

### Epic 9: Sorting (backend + frontend)

**Files:**
- `backend/app/api/collections.py` — `sort` param on `GET /collections/community` (and `/community/top` if it still makes sense alongside a generic sort)
- `backend/app/api/moderation.py` — `sort` param on the queue
- `frontend/src/pages/CommunityCollections.tsx` — sort dropdown
- `frontend/src/pages/ModerationQueue.tsx` — sort dropdown

**Tasks:**
1. `sort: Literal["rating", "downloads", "alpha"] = "downloads"` query
   param on the community listing endpoint(s); maps to
   `ORDER BY avg_rating DESC`, `ORDER BY download_count DESC`, or
   `ORDER BY name ASC` respectively. Same param on the moderation queue
   (default there can stay `submitted_at` ascending — oldest-first is
   the sane default for a review queue — but still accept the same
   three values as an override).
2. Frontend: a `<select>` for sort order on both pages, value in the
   React Query key (per `AGENTS.md` rule 12 — `['collections', {
   visibility: 'public', sort }]`, not a bare `['collections']`) so
   switching sort doesn't collide with cached unsorted data.
3. Tests (backend): each sort value returns rows in the expected order
   against a small fixture set.

**Commit:** `feat: add sorting by rating, downloads, and name`

### Epic 10: Notification preferences + download digest

**Files:**
- `backend/app/models/user.py` — `notify_on_download`, `notify_on_comment`
- `backend/app/models/collection.py` — `last_digest_download_count`, `last_digest_sent_at`
- `backend/app/api/auth.py` — extend `PATCH /auth/me` / `UserUpdate`
- `backend/app/scripts/send_download_digests.py` — new script
- `backend/app/services/email.py` — `build_download_digest_email`
- `frontend/src/pages/UserSettings.tsx` — two toggles
- `docs/deployment.md` — cron setup instructions
- `backend/alembic/versions/` — new migration

**Tasks:**
1. Migration: `users.notify_on_download` / `users.notify_on_comment`
   (`bool`, `server_default=false`); `collections.last_digest_download_count`
   (`int`, `server_default='0'`); `collections.last_digest_sent_at`
   (`datetime`, nullable).
2. `UserUpdate` gains `notify_on_download: bool | None`,
   `notify_on_comment: bool | None`; `PATCH /auth/me` applies them
   (self-service, no admin needed — these are the user's own
   preferences).
3. `send_download_digests.py`: iterate collections where
   `download_count > last_digest_download_count` and
   `owner.notify_on_download` and `owner.email`; send
   `build_download_digest_email(collection.name, delta)`; update both
   digest-tracking columns per collection regardless of whether the
   email actually sent (so a bad email address doesn't cause the delta
   to balloon forever — log the failure and still advance the
   watermark). Load `SmtpConfig` via the same
   `get_effective_smtp_config()`-style helper the existing email call
   sites use; skip entirely (log a notice, exit 0) if SMTP isn't
   configured/enabled.
4. `docs/deployment.md`: document the crontab entry, e.g.
   `0 6 * * * cd /path/to/myace && docker compose exec -T backend python -m app.scripts.send_download_digests`,
   next to the existing compose-file instructions.
5. `UserSettings.tsx`: two checkboxes in the profile section wired to
   the existing profile-update mutation.
6. Tests: digest script sends only when delta > 0 and preference is
   on; watermark advances even on send failure; no email sent when
   SMTP is disabled.

**Commit:** `feat: add notification preferences and download digest`

### Epic 11: Documentation & release

**Files:**
- `docs/adr/0007-additive-user-role-column.md` — new
- `docs/adr/0008-collection-moderation-state-machine.md` — new
- `docs/data-model.md` — `users` table (role, notify_* fields), `collections` table (moderation_* + rating/digest fields), new `collection_ratings`/`collection_comments` tables, rewrite the existing "Community collections" section's self-serve-publish description
- `docs/invariants.md` — new invariants under `## Authorization`: owners never self-approve; moderator scope is community-only; comments/ratings only on approved collections
- `AGENTS.md` — rewrite rule 18 (publish is no longer an immediate self-serve DB write — replace with the new submit/approve/deny description); add a new numbered rule for the moderator role + `require_moderator_or_admin` pattern; add a rule for the ratings/comments soft-delete + self-rating guard if not already implied by rule 15
- `CLAUDE.md` — only touch if something Claude-Code-specific changed (unlikely; skip unless needed)
- `README.md` — update the community-collections description (star ratings, comments, moderation) if it currently describes the old self-serve flow
- `docs/debugging.md` — add an entry if any epic surfaced a non-obvious gotcha worth searching for later (e.g. the alembic head confirmed in preflight, or an email-failure-must-not-roll-back-state pattern)
- `backend/pyproject.toml`, `cli/pyproject.toml`, `frontend/package.json`, `frontend/package-lock.json` — version bump (this repo has no `CHANGELOG.md`; version-bump commits are the existing precedent — follow it, don't invent a changelog file)

**Tasks:**
1. Write ADR-0007 and ADR-0008 per `docs/adr/template.md`, following the
   Architecture Decisions section above.
2. Update every doc file listed above. Grep for stale references before
   considering this done, per `AGENTS.md` rule 14's removal-checklist
   habit — specifically grep for `"Publish to Community"` and
   `POST /{collection_id}/publish` and self-serve publish language, since
   Epic 3 changes its behavior.
3. Bump the version (minor bump — this is new functionality, not a
   patch) in all four version-bearing files, matching the pattern in
   commit `b6a5308`.
4. Full-suite check: `pytest` (backend, cli), `npm run test` and
   `npm run lint` (frontend), `mypy app` (backend) — all green.
5. Run the `security-review` skill against the full branch diff once
   (not per-epic) — this feature adds several new authz surfaces
   (`require_moderator_or_admin`, self-approval prevention, comment
   deletion ownership) worth one dedicated pass before the PR.

**Commit:** `docs: document community moderation, ratings, and comments; bump version`

## Verification Strategy

### Per-epic testing
- Backend epics (1, 3, 5, 7, 9, 10): pytest via httpx `AsyncClient` against
  the in-memory SQLite fixture, covering the happy path, the specific
  authz denial the epic introduces, and any state-machine edge case
  (double-approve, self-rate, self-approve, resubmit-after-deny).
- Frontend epics (2, 4, 6, 8, 9, 10): manual verification via the
  `frontend-dev` preview server + backend on `:8000` (per `CLAUDE.md`) —
  no frontend test infra exists for these pages beyond what's already in
  the two `.test.tsx` files noted in research; add to those only if a
  genuinely reusable component emerges (e.g. a star-rating widget), don't
  invent broad new frontend test coverage as a side effect of this plan.

### Security-sensitive spots to double-check explicitly
- `require_moderator_or_admin` is never accidentally satisfied by
  `is_admin` alone without `role` being set (i.e. an existing admin whose
  `role` wasn't backfilled to `"admin"` by the Epic 1 migration must still
  pass — confirm the backfill `UPDATE ... WHERE is_admin = true` actually
  ran against every existing admin row in a test).
- Approve/deny/meta-edit routes use `require_moderator_or_admin`, **not**
  `authorize_access` — the latter's owner-bypass would let an owner
  approve their own collection, which is the exact thing Epic 3 must
  prevent.
- Comment/rating endpoints correctly gate on `moderation_status ==
  "approved"`, not on `published`/`visibility` alone (a `denied`
  collection could theoretically have stale `published=True` only if a
  bug elsewhere set it — moderation_status is the single source of truth
  post-Epic-3).

### Documentation
Covered by Epic 11 — treat it as a hard requirement, not an optional
wrap-up, per `AGENTS.md` rule 14 ("both are kept up to date in the same
PR... not as follow-up cleanup").

## Dependencies to Add

None. `aiosmtplib` (email), `alembic`, and the existing SQLModel/FastAPI
stack cover everything in this plan — no new third-party packages.

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Grandfather migration misses some currently-public collections (e.g. `is_active=False` public ones) | Backfill predicate exactly matches the existing community-listing query's filter (`published AND visibility='public' AND is_active`) — verify against `list_community_collections()`'s actual `WHERE` clause before finalizing the migration, don't hand-derive it |
| Owner locked out of editing while `submitted` (no meta edits mid-review) | Deliberate, documented in the state machine — a moderator can still fix typos via the mod-only meta-edit endpoint (Epic 5) even while `submitted` |
| Email send failures block approve/deny/comment actions | Every email send site wrapped in try/except + log, never raises past the DB commit (Epics 3, 7, 10) |
| Digest script double-counts or under-counts downloads across concurrent runs | Watermark (`last_digest_download_count`) update happens in the same transaction as the read-and-diff, and the script is intended to run once daily via cron, not concurrently — document "don't run this on multiple hosts" in `docs/deployment.md` |
| Role backfill migration runs against a large `users` table in production | Single indexed `UPDATE ... WHERE is_admin = true` — admin rows are a tiny fraction of any realistic user table, no batching needed |
| Moderator role scope creeps into full admin over time (future PRs bypassing `require_moderator_or_admin`) | Called out explicitly in Decisions Locked In and Architecture Decisions — any future PR widening moderator scope should be treated as a deliberate, reviewed decision, not a drive-by change |
