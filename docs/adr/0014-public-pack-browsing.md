# ADR-0014: Public read-only pack browsing

**Status:** Accepted — **amended by [ADR-0018](0018-public-read-only-mcp-server.md).**
The public-read family this ADR established has since grown from five routes
to seven: `GET /collections/community/{id}/install.md` and
`GET /api/v1/frameworks` joined it. The invariants below (approved-only,
sanitized, read-only, rate-limited) still govern all of them; "five" below is
the count at the time of this decision.

## Context

The storefront is the front door of the v2.0 onboarding revamp: a visitor
should be able to see real starter and community packs before creating an
account (design proposal §6.1, §9 Phase 5). Until now every collection route
required authentication (AGENTS.md rule 13), including the community listing,
so the exact audience the storefront is meant to convert could not see it.

Two facts constrain the shape of the exception:

- `www` community packs are already moderated. `published=True` is only ever
  set by a moderator approving a submission (rule 18 / ADR-0008), so the data
  these routes expose has already passed review.
- `download_count` is advisory and user-incrementable (invariant 25,
  ADR-0015). It is a soft "used N times" signal, never an authoritative
  popularity ranking.

This ADR follows the pattern ADR-0011 established for the public demo route:
a narrow, explicit allowlist that is a reviewed exception to the
authentication invariant, not a change to the authorization model.

## Decision

Allow anonymous `GET` for the storefront's read surface only, all in
`backend/app/api/collections.py`:

- `GET /api/v1/collections/community`
- `GET /api/v1/collections/community/top`
- `GET /api/v1/collections/community/categories`
- `GET /api/v1/collections/community/{collection_id}`
- `GET /api/v1/collections/community/{collection_id}/artifacts`

Every one of them:

- has **no `Depends(get_current_user)`** and **creates no session**;
- is **read-only** — there is no anonymous write path, and the existing
  `/use`, `/publish`, `/unpublish` and `PATCH` routes keep their auth
  dependency unchanged;
- returns only rows satisfying `is_active AND published AND
  moderation_status == "approved"`; the detail and artifacts routes 404 for
  anything else, so an unpublished pack's existence is not revealed;
- serializes through `PublicCollectionRead`, a deliberately smaller schema
  than `CollectionRead`: no `git_url`/`git_branch` (a pack's source repo may
  be private), no `visibility`, and no moderation-workflow fields
  (`moderation_reason`, `moderated_by`, `moderated_at`, `submitted_at`,
  `verified_by`);
- is rate-limited per client IP by a dedicated `storefront_limiter`
  (`settings.storefront_rate_limit`, default `120/minute`).

`GET /api/v1/collections/{id}` and `/api/v1/collections` stay authenticated.
Ratings and comments stay authenticated and still require
`moderation_status == "approved"` (rule 31); the storefront shows the stored
aggregate rating from `CollectionRead` for anonymous visitors instead.

## Alternatives considered

- **Keep everything behind login.** Rejected: it preserves the exact friction
  the storefront exists to remove, and the content being shown (approved
  community packs) is already public by intent.
- **Make the whole collections surface public**, or make
  `GET /collections/{id}` public for public/approved rows. Rejected: it
  widens the exception to routes whose semantics include ownership and
  private/public sharing, and it would be easy to leak a draft through a
  future change to `visibility`. A separate `/community/...` family keeps the
  public contract and the authenticated contract visibly distinct.
- **Trust `published` alone** (as the listing predicate effectively does
  today). Rejected for the detail routes: checking `moderation_status`
  explicitly means a future code path that flips `published` without an
  approval cannot expose unreviewed content.

## Consequences

- Anonymous users can browse every approved pack and its contents. That is
  the intended product behaviour, and it widens the public attack surface by
  five read routes — bounded by the rate limit and the approved-only filter.
- The rate limiter's storage is in-memory and per-process (rule 36), so
  behind N replicas the effective limit is N × the configured value. Accepted
  for now, as with the demo and auth limiters; a shared store is the fix if
  this ever becomes a real load concern.
- `download_count` is visible anonymously, and remains tamperable. Nothing in
  the storefront sorts or labels it as a ranking; it is rendered only as
  "used N times". Do not add a "Most used" sort or a "Top packs" ranking
  that treats it as authoritative (AGENTS.md rule 42, invariant 25).
- A pack that is unpublished while a visitor has the page open starts
  returning 404 on the next fetch. The existing frozen-copy behaviour for
  setups is unaffected (ADR-0015); nothing here tells a non-owner they have
  frozen content.

## Amendment (2026-11-28): `GET /community/topics`

A sixth anonymous read joined the list: `GET /api/v1/collections/community/topics`,
which maps pack id to up to three topics derived from item tags
(`services/pack_topics.py`) so the library can offer topic filters without a
pack-tags column. It stays inside this decision's boundary: no
`Depends(get_current_user)`, no session, read-only, rate-limited by
`storefront_limiter`, and it reads only approved, published, active packs and
their enabled, undeleted items. It must stay registered above
`/community/{collection_id}` (AGENTS.md rule 16). The public pack detail also
gained `relations` (resolved links to other public packs) and
`content_updated_at`; both are filtered to what an anonymous visitor may already
read.
