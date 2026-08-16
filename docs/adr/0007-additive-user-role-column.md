# ADR-0007: Additive `role` column alongside `is_admin`

**Status:** Accepted

## Context

The community-moderation feature (approve/deny submissions, edit
collection metadata, delete comments) needs a third privilege tier between
a plain user and a full admin: a moderator who can review community
submissions but has none of an admin's other capabilities (user
management, system settings, adapter toggles). The existing authz surface
is entirely built around `User.is_admin: bool` — `require_admin`,
`authorize_access`'s admin bypass, and every admin-only route already
depend on it.

## Decision

Add `User.role: Literal["user", "moderator", "admin"]` (default `"user"`)
as a **new** column. `is_admin` is untouched and continues to gate every
existing `require_admin`/`authorize_access` bypass exactly as before. The
two are kept in sync one-directionally: the new admin-only
`PATCH /auth/users/{id}/role` endpoint sets `is_admin = (role == "admin")`
in the same transaction whenever `role` changes. A new
`require_moderator_or_admin` dependency reads `role` only — never
`is_admin` — so moderator scope can never accidentally widen by having
some code path check `is_admin` as a shortcut.

## Alternatives considered

- **Replace `is_admin` with `role` everywhere** — rejected. `is_admin` is
  referenced across the whole existing authz surface (`require_admin`,
  `authorize_access`'s bypass, admin-lockout guards in `auth.py`). Migrating
  every call site to compare `role == "admin"` instead is a much larger,
  riskier change for a feature that only needs one new tier, and it was
  out of scope for this plan.
- **A separate `is_moderator: bool` column, parallel to `is_admin`** —
  rejected: doesn't generalize if a fourth tier is ever needed, and two
  independent booleans invite an invalid state (`is_admin=True,
  is_moderator=True` meaning what, exactly?) that a single `role` enum
  can't represent.
- **A many-to-many roles/permissions table** — rejected as disproportionate;
  this app has no team/org model (see ADR-0003) and a single-role-per-user
  enum is sufficient for the one new tier this feature needs.

## Consequences

- Two sources of truth for "is this user an admin" (`is_admin` and
  `role == "admin"`) must be kept in sync by convention, enforced only at
  the one call site that changes `role`
  (`app/api/auth.py::set_user_role`). Any future code path that sets
  `role` directly (a script, a fixture, a different endpoint) without also
  syncing `is_admin` — or vice versa — silently desyncs the two. The Epic 1
  migration's backfill (`role='admin' WHERE is_admin=true`) and the
  registration/OIDC bootstrap-admin paths were updated to set both
  together for the same reason.
- `require_moderator_or_admin` is a second, parallel authorization
  dependency alongside `require_admin` — a future change that needs "admin
  OR moderator" semantics elsewhere in the codebase should reuse this
  dependency rather than inventing a third variant.
- Moderator scope is deliberately narrow (community moderation only) per
  the plan's locked-in decision — widening it to any other admin
  capability should be treated as a new, reviewed decision, not a
  drive-by change to `require_moderator_or_admin`.
- This adds a third tier to ADR-0003's "two roles only, no RBAC" decision.
  It's a minimal, purpose-specific extension (one new tier, one new
  dependency, no permissions table) rather than a reversal of that
  decision — ADR-0003's reasoning against full RBAC/teams still holds for
  this deployment shape.
