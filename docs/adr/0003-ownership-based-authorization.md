# ADR-0003: Ownership + visibility authorization, not RBAC/teams

**Status:** Accepted

## Context

Before real authentication existed, every route trusted a client-supplied
`owner_id` with no verification, and almost no route filtered by it anyway —
of every route touching a specific collection or profile, only three
actually checked ownership. Any caller could read, edit, or delete any other
user's data by UUID. This needed a real fix, but the deployment target is a
small, self-hosted, single-organization instance (a handful of known users,
not a multi-tenant SaaS) — not a system that needs teams, shared workspaces,
or per-resource ACLs.

## Decision

Two roles only: **user** (owns their own collections/profiles/tokens, has
read-only access to anything another user marked public) and **admin**
(bypasses ownership entirely, for oversight). No teams, no organizations, no
granular per-resource sharing beyond the existing public/private binary that
already existed on `Collection.visibility`/`Profile.is_public`. The first
person to ever register becomes admin automatically; `ADMIN_EMAILS` promotes
others afterward.

## Alternatives considered

- **Full RBAC with per-resource permissions** — rejected as disproportionate
  to the actual deployment shape. It would mean new tables, a permissions
  model, and UI for managing grants, for a use case that doesn't need
  collaboration finer-grained than "mine" / "everyone can see this."
- **Teams/organizations grouping users** — rejected for the same reason;
  explicitly out of scope per the decision that prompted this work.
- **Enforce visibility with a database-level policy (Postgres RLS)** —
  considered and rejected for now: the application-layer check
  (`authorize_access()`/`owner_or_public_clause()`) is sufficient given
  there's exactly one, trusted, first-party client of the database (the
  backend itself). RLS would add real value if a second, less-trusted
  service ever queried the same database directly.

## Consequences

- Authorization logic is small and centralized: two functions
  (`backend/app/core/authz.py`), used consistently across every route — see
  [invariants.md](../invariants.md#authorization).
- Denied access always returns 404, not 403, everywhere, by construction —
  a resource's existence is never revealed to someone who can't access it.
- **The gap this doesn't cover**: a public profile can reference a private
  collection, and compiling that profile exposes the private collection's
  artifacts to anyone who can see the public profile —
  `compile_profile()` doesn't re-check per-collection visibility. This is
  an accepted trade-off of "no granular sharing," documented explicitly in
  [invariants.md](../invariants.md#a-gap-thats-accepted-not-fixed) rather
  than silently left as a surprise.
- Adding real team/shared-workspace support later means introducing a new
  primitive (not stretching `is_admin`/ownership to fake it) — this ADR is
  the marker for "we knew this was out of scope, here's why."
