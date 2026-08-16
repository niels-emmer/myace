# ADR-0012: Manual freshness verification, not automated content checking

**Status:** Accepted

## Context

Community collections (`docs/data-model.md`'s "Community collections"
section, [ADR-0008](0008-collection-moderation-state-machine.md)) go
through moderation once, at submission time. Nothing re-checks a
collection after it's approved — a rule that was accurate against Claude
Code's frontmatter schema in January can be quietly wrong by August if the
target framework's real config format changed underneath it, and nothing
in the system would surface that. A visitor browsing the community store
has no way to tell "reviewed once, two years ago, never revisited" apart
from "reviewed last week."

An automated freshness check — re-fetching each target framework's docs
and diffing a collection's artifacts against them — isn't something this
system can honestly claim to do today. `doc_verifier`/`DocCacheEntry`
(see `docs/data-model.md`) already fetch and cache framework documentation
for adapter compatibility purposes, but nothing consumes that cache to
validate arbitrary collection *content* against it (the adapters'
translation logic is hardcoded, a documented gap — see
`backend/app/adapters/__init__.py`'s module docstring). Building that
real automated check is a substantially larger project than a freshness
signal warrants right now.

## Decision

Add a manual, moderator-attested freshness signal instead of an automated
one: `Collection.last_verified_at` (nullable `Date`) and `verified_by`
(nullable FK to `users.id`), set by a moderator/admin via
`POST /collections/{id}/verify`, and surfaced everywhere as exactly what
it is — "a human confirmed this recently," never "automatically checked
against live tool docs." The frontend badge (`FreshnessBadge.tsx`) and
every backend docstring touching this feature repeat that framing
deliberately, so the feature can't accidentally imply more rigor than it
delivers.

`GET /admin/freshness-queue` surfaces approved collections whose
verification is missing or older than
`settings.collection_freshness_threshold_days` (default ~6 months), and a
weekly cron script (`app/scripts/check_collection_freshness.py`) emails
moderators/admins a digest when that queue is non-empty, so staleness
doesn't require someone to remember to go check — see
[data-model.md](../data-model.md#freshness-verification) for the full
field/route/script inventory and [AGENTS.md rule 37](../../AGENTS.md) for
the implementation conventions.

Both the queue route and verify action are gated by
`require_moderator_or_admin` (the same dependency the moderation queue
uses, per [ADR-0007](0007-additive-user-role-column.md)) rather than
`authorize_access`'s ownership model — reviewing community content for
freshness is a moderation capability, not something tied to who owns the
collection.

## Alternatives considered

- **Automated staleness detection** (diff a collection's artifacts against
  live-fetched target-framework docs) — rejected for now as building the
  wrong thing first. The adapters' translation logic doesn't currently
  consume `DocCacheEntry` at all (a pre-existing, separately-tracked gap),
  so a real automated check would mean building that consumption path
  *and* a content-diff heuristic before this feature could exist honestly.
  A manual signal ships today and is honest about its limits; a fake
  "automated" badge that's actually just a timestamp would be worse than
  no badge.
- **No self-verification block** (a moderator/admin who also owns a
  collection can verify it themselves) — considered and accepted as
  correct, not an oversight. Moderation *approval* has a hard
  self-approval block ([ADR-0008](0008-collection-moderation-state-machine.md))
  because approving is the one action that flips a collection from
  private-review to publicly-live — a real trust boundary. Verifying an
  *already-approved* collection is additive and reversible (another
  moderator can re-verify or the queue will just re-flag it next cycle);
  there's no equivalent one-way trust boundary being crossed, so adding a
  self-verification block would be extra complexity solving a risk that
  doesn't exist here.
- **Expose the threshold via an API endpoint / make it admin-editable
  from System Settings** — rejected as scope creep for this pass.
  `settings.collection_freshness_threshold_days` is env/settings-file
  only; the frontend badge hardcodes a matching default rather than
  fetching it live (a known, documented gap — AGENTS.md rule 37). Worth
  revisiting if the threshold ever needs to vary per deployment without a
  restart, but not required for the feature to be useful today.

## Consequences

- "Verified" is a claim about a point in time, not a live guarantee — a
  collection can go stale again the moment a target framework's real
  config format changes, and nothing will notice until the next
  moderator pass or the weekly digest's threshold catches up to it. This
  is the honest trade-off of a manual signal, not a bug.
- The freshness queue and digest script share one query
  (`stale_collections_query()` in `app/api/freshness.py`) specifically so
  "what counts as stale" can't drift between the two call sites — see
  AGENTS.md rule 37.
- If MyACE ever builds the automated content-diff check described above,
  `last_verified_at`/`verified_by` don't need to be removed — an
  automated check would most naturally add a third, distinct signal
  ("last automatically checked") alongside this manual one, not replace
  it; a human confirming a collection is still good is a different claim
  than a script confirming a target framework's docs haven't changed.
