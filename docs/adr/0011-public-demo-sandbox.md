# ADR-0011: A stateless, rate-limited public demo endpoint

**Status:** Accepted

## Context

MyACE's value is hard to see without trying it, and trying it has
historically required registering an account first — even just to see what
a compiled `CLAUDE.md`/`AGENTS.md`/`.cursor/rules/*.mdc` output looks like.
That's real friction for a first-time visitor deciding whether to sign up
at all, and it's the opposite of what a landing page is supposed to do.

Every route in this backend requires authentication today (AGENTS.md rule
13, invariant 1 in `docs/invariants.md`) — with good reason: ownership and
ownership-derived data are the whole authorization model (ADR-0003), and an
unauthenticated route is, by construction, a route with no ownership to
check. Adding *any* public route is therefore not a routine addition; it's
a deliberate carve-out of the one invariant every other route in this
codebase can lean on.

## Decision

Add exactly one public, unauthenticated route: `POST /api/v1/demo/compile`
(`backend/app/api/demo.py`), scoped as narrowly as the feature allows:

- **No `Depends(get_current_user)`, no DB session dependency at all.** The
  route can't read or write anything in the database even by accident —
  there's no `AsyncSession` in scope to do it with. Caller-supplied
  markdown is parsed into ephemeral `CanonicalArtifact` objects that exist
  only for the duration of the request.
- **Rule-type artifacts only**, parsed by the same `##`-section splitter
  the scanner already uses for `AGENTS.md` (`_parse_agents_md_content()`,
  factored out of the existing `_parse_agents_md()` for this purpose). No
  skills, agents, model-configs, git URLs, or file uploads — the smallest
  input surface that still demonstrates the real compilation pipeline.
- **Capped at 20KB of input.**
- **Compiled through 3 adapters, not all 11** (`claude-code`, `cursor`,
  `opencode`) — enough to show the "one input, many outputs" story without
  the response ballooning or every adapter's edge cases becoming part of
  this route's abuse surface.
- **Rate-limited to 10 requests/minute/IP** via `slowapi` (new dependency,
  MIT-licensed), applied with `@limiter.limit(...)` on this one route only.
  The `Limiter` instance and its `RateLimitExceeded` exception handler are
  registered once on the FastAPI app (`app/main.py`) — that registration is
  required plumbing for the decorator to raise 429s at all, not a global
  rate-limiting policy; no other route carries the decorator, so no other
  route is throttled by it.

## Alternatives considered

- **Require a lightweight/anonymous session for the demo** (e.g. an
  ephemeral guest account, or a signed anonymous token) — rejected as
  solving a problem that doesn't exist here. The whole point is zero
  friction before signup; inventing a session concept just to gate a
  stateless preview would add complexity (a new auth mode alongside
  session-cookie/Bearer-token) without adding any real protection, since
  nothing is being protected — there's no data to own.
- **Reuse the full `/profiles/compile` pipeline behind a fake/system
  profile** — rejected. That pipeline resolves real `Collection`/`Artifact`
  rows from the database per profile; forcing a stateless, visitor-supplied
  compile through it would mean either persisting throwaway rows per demo
  request (a footgun for accidental data growth and the kind of
  "nothing is persisted" claim this ADR wants to make truthfully) or
  forking the pipeline's behavior based on caller identity, which is worse
  than a small, separate, deliberately narrower endpoint.
- **No rate limit, rely on infrastructure (reverse proxy / CDN) instead** —
  rejected as not self-hostable-friendly. MyACE ships to be forked and
  self-hosted on a single VPS behind a plain reverse proxy (`docs/
  deployment.md`), not necessarily behind a CDN with its own rate limiting.
  An unauthenticated, unlimited compile endpoint on a small VPS is a
  trivial CPU-exhaustion vector (11 adapters' worth of `translate()` calls,
  even scoped to 3, run per request); the limit needs to be true regardless
  of what's in front of the box.
- **Rate-limit by something other than IP** (e.g. a per-session cookie) —
  rejected; the whole point is no session exists yet. IP is the only
  identity available pre-auth, with the usual caveat that it's imperfect
  behind NAT/shared IPs — acceptable for a demo-abuse deterrent, not
  claimed as a security boundary against a determined distributed attacker.

## Consequences

- This is now the one documented exception to "every route requires
  `Depends(get_current_user)`" beyond the pre-existing auth-entry list —
  AGENTS.md rule 13 and `docs/invariants.md` invariant 1 both name it
  explicitly, and rule 36 documents the pattern (no persistence, fixed
  small scope, per-route rate limit) for any future public route rather
  than leaving this as a one-off precedent to rediscover from a diff.
- `docs/invariants.md` gains a new invariant: the demo endpoint never
  persists anything, ever — enforced structurally (no session dependency
  exists to persist with), not just by convention, and covered by a test
  that asserts zero DB rows exist after a compile call.
- `slowapi`'s in-memory rate-limit storage is per-process. In a
  multi-replica deployment, a client could get up to `10 × replica_count`
  requests/minute rather than a hard global 10 — acceptable for a
  demo-abuse deterrent on what's still a single-VPS-oriented deployment
  story (`docs/deployment.md`), but if MyACE ever grows a documented
  multi-replica production shape, the limiter would need a shared backend
  (Redis) to hold across replicas.
- Every other route's authorization posture is unchanged. This ADR
  authorizes exactly one new public route, not a general loosening —
  widening the exception list again is a decision as deliberate as this
  one, not an implicit side effect of adding a route that happens to be
  convenient to leave unauthenticated.
