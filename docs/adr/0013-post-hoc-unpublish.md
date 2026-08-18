# ADR-0013: Post-hoc unpublish for approved collections

**Status:** Accepted

## Context

ADR-0008 established pre-publication review: a collection only becomes
public once a moderator/admin approves it, and it explicitly rejected
"post-hoc-only moderation" as a *replacement* for that review step. But
that decision left no way to reverse an approval after the fact — once a
collection was `approved`, nothing (not the owner, not a moderator, not an
admin) could take it back out of the community store. In practice content
can go stale, a license issue can surface after approval, or an owner may
simply change their mind, and none of those are things pre-publication
review catches.

## Decision

Add `Collection.moderation_status = "unpublished"` and
`POST /collections/{id}/unpublish`, callable by the collection's owner or
by a moderator/admin, only from `approved`. It sets `published=False`,
`visibility="private"`, and reuses `moderation_reason`/`moderated_at`/
`moderated_by` (same fields `approve`/`deny` already write). This is
additive to ADR-0008's state machine, not a replacement for it — pre-
publication review is unchanged; this is a *separate*, post-hoc action.
Getting back into the community store still requires a fresh `publish` +
moderator approval, same as a `denied` collection; there is no self-serve
republish path, which is what keeps this consistent with ADR-0008's
"owner never single-handedly makes content public" invariant.

A moderator/admin unpublishing someone else's collection can attach an
optional reason, emailed to the owner (mirrors the existing deny-reason
email). An owner unpublishing their own collection doesn't need to give
themselves a reason.

Making this endpoint usable by a non-admin moderator also required
loosening collection-detail *read* access
(`_visible_to_moderator()` in `app/api/collections.py`): moderators could
already see queue rows via `GET /moderation/queue`, but `GET
/collections/{id}` still 404'd for them unless the collection happened to
be public — meaning a moderator without `is_admin` could review a
submission's metadata in the queue table but never open it to actually see
its contents. This bypass only applies once a collection has entered the
moderation lifecycle (`moderation_status != "draft"`); a never-submitted
draft stays private to its owner even from a moderator, matching the
existing scope of the meta-edit endpoint (rule 30).

## Alternatives considered

- **Reuse `denied` for this state instead of a new `unpublished` value** —
  rejected: `denied` specifically means "a moderator rejected this
  submission before it ever went live," which is a different fact than
  "this was live and got pulled." Collapsing them loses that distinction
  in the collection's history and in the reason field's meaning.
- **New `unpublished_at`/`unpublished_by` columns instead of reusing
  `moderated_at`/`moderated_by`** — rejected as unnecessary schema growth;
  those columns already mean "when/who last changed the moderation state,"
  and `deny` already reuses them for a conceptually similar transition.
- **Immediate self-serve unpublish only, no moderator path** — rejected;
  a moderator/admin needs to be able to act on reported or stale content
  without waiting on the owner, same reasoning that justifies the
  moderator meta-edit endpoint existing alongside the owner's own PATCH.

## Consequences

- A collection's full history is now: `draft` → `submitted` →
  `approved`/`denied`, and `approved` can additionally move to
  `unpublished`, which itself can only get back to `approved` by going
  through `submitted` again. No state has a direct self-serve path back to
  `approved`.
- Ratings/comments already gate on `moderation_status == "approved"`
  (rule 31) and the community listing already filters on
  `published == True` — both correctly exclude `unpublished` collections
  with no additional code change.
- The collection-detail read bypass is scoped to moderator/admin roles and
  to collections that have been submitted at least once; it does not
  extend to artifact writes or collection metadata writes, which remain
  owner/admin-only (or moderator-only via the existing meta-edit
  endpoint).
