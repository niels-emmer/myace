# ADR-0008: Collection moderation state machine replaces self-serve publish

**Status:** Accepted

## Context

`POST /collections/{id}/publish` (see the removed `app/services/publish.py`
history and AGENTS.md rule 18) was a pure, immediate self-serve DB write:
it set `published=True` and `visibility="public"` on the caller's own row,
with no review step. That matched the product's original scope, but the
community-enhancements plan requires that submissions go through human
moderation before becoming public — an owner should not be able to make
arbitrary, unreviewed content visible to every MyACE user without a
moderator ever looking at it.

This changes the meaning of `published`/`visibility` on a `Collection`:
they can no longer be set by the same action that submits content, or the
review step is meaningless.

## Decision

Add `Collection.moderation_status: Literal["draft", "submitted",
"approved", "denied"]` (default `"draft"`) as the single source of truth
for the review lifecycle, plus `moderation_reason`, `submitted_at`,
`moderated_at`, `moderated_by`. State transitions:

```
draft --submit--> submitted --approve--> approved
                      |
                      +--deny(reason)--> denied --edit + resubmit--> submitted
```

`POST /collections/{id}/publish` now only means "submit for review" — it
moves `draft`/`denied` to `submitted` and never touches
`published`/`visibility`. The new `/api/v1/moderation` router's
`approve`/`deny` actions (gated by `require_moderator_or_admin` from
ADR-0007, not `authorize_access`'s owner-bypass) are the *only* code path
that flips `published=True`/`visibility="public"` — on approval. A denied
collection keeps `published=False`; the owner can edit it and resubmit,
which sends it back to `submitted` for a fresh review. The prior denial
reason is kept on the row as history but is not surfaced to anyone but the
owner and moderators/admins, since `authorize_access`'s visibility check
(`is_public=collection.visibility=="public"`) already keeps a
non-`approved` collection's detail page invisible to everyone else.

Every collection that was already `published=True AND is_active=True` at
migration time (matching `list_community_collections()`'s actual filter
exactly, not a hand-derived guess — verified against the live query
before finalizing the migration) is grandfathered to `moderation_status =
"approved"` in the same migration, including all starter packs. Nothing
already visible in the community disappears or needs re-review.

## Alternatives considered

- **Keep `published`/`visibility` as the review signal, add a separate
  `pending_review: bool`** — rejected: this keeps two overlapping signals
  for "is this public" (`published` and NOT `pending_review`) instead of
  one, and doesn't cleanly represent "denied, can be resubmitted" as a
  distinct state from "never submitted."
- **A generic `status` free-text field instead of an enum** — rejected;
  the whole point of a state machine is a closed set of valid transitions,
  which a `Literal` enum enforces at the schema-validation layer (422 on
  an invalid value) the same way this codebase already does for
  `collection_type`/`visibility` on `Collection`.
- **Immediate publish stays, moderation is advisory (moderators can
  unpublish after the fact)** — rejected as the opposite of what was
  asked: the requirement is pre-publication review, not post-hoc
  moderation. Post-hoc-only moderation would let unreviewed content go
  live before any human looks at it, which is the exact gap this ADR
  closes.

## Consequences

- The self-serve, code-review-free publish flow described in the old
  AGENTS.md rule 18 no longer exists — that rule was rewritten in the
  documentation epic rather than left stale. `collections/`-directory
  starter packs (rule 25) remain a completely separate, one-directional
  concept unaffected by this change: they're grandfathered to `approved`
  once, at migration/seed time, never routed through the queue.
- An owner can no longer make a collection public without a moderator or
  admin's explicit approval — including the owner if they are *also* a
  moderator/admin: `require_moderator_or_admin` has no ownership-based
  bypass, so self-approval is impossible by construction, not just by
  convention.
- A collection stuck at `submitted` (no moderator has reviewed it yet)
  blocks the owner from editing name/description/category through their
  own route while under review — deliberate, so a moderator isn't
  reviewing content that changes underneath them. The moderator-only
  meta-edit endpoint (a separate, smaller change on top of this state
  machine) exists specifically so a moderator can still fix a typo
  without needing the owner to withdraw and resubmit.
- Comments and ratings gate on `moderation_status == "approved"`
  specifically, not on `published`/`visibility` alone — those two fields
  are only ever set together with `moderation_status="approved"` post this
  change, but `moderation_status` is the authoritative signal a future
  change should check, not a derived boolean that could theoretically
  drift from it.
