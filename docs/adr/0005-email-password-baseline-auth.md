# ADR-0005: Email+password as the baseline auth method, SSO optional

**Status:** Accepted

## Context

The backend already had real OIDC/GitHub/Google OAuth2 scaffolding
(`backend/app/core/security.py`) before any of it was actually enforced —
client registration existed, but no route validated a session or token
against a request, and the frontend's "Authentication Providers" buttons in
Settings weren't wired to any click handler. All three providers are
unconfigured (empty client ID/secret) by default. A pure "OIDC/SSO only"
design would mean a fresh deployment has **no way to ever log in** until an
operator sets up an external identity provider first — a hard requirement
before the app is usable at all.

## Decision

Add real email+password authentication (bcrypt-hashed, same pattern as the
existing API token hashing) as the always-available baseline. OIDC/GitHub/
Google remain available as optional additional sign-in methods, registered
exactly as before — only if their config is present — with no change to
that scaffolding's behavior.

## Alternatives considered

- **OIDC/SSO only** — rejected as the sole mechanism because it makes a
  fresh, unconfigured deployment unusable out of the box, which fails the
  basic bar of "clone it, run it, use it." Worth revisiting *as an
  additional restriction* (e.g. an env var that disables password auth
  once SSO is confirmed working) for deployments that want to mandate SSO —
  not implemented here.
- **A one-time bootstrap CLI command that seeds a single admin account** —
  rejected as extra surface (a new CLI command, a new code path only used
  once) for a problem email+password registration already solves more
  generally, including for any *additional* users after the first.

## Consequences

- First-ever registered user becomes admin automatically (there's no other
  way to get an admin on a totally fresh database); `ADMIN_EMAILS`
  (comma-separated config) promotes specific emails on register or OIDC
  login afterward, for adding more admins without direct database access.
- `User.password_hash` is nullable — an OIDC/GitHub/Google-only account
  never sets one, and login-by-password correctly rejects such an account
  rather than crashing on a null comparison
  (`backend/app/api/auth.py`'s `login_with_password`).
- This is a schema change (new column, `password_hash`), so it shipped with
  an Alembic migration (`a1c2d3e4f5a6_add_password_hash.py`) rather than
  being bolted on informally.
- Registration is currently open to anyone who can reach `/auth/register` —
  there's no invite-only mode or email verification step. Fine for a
  small, trusted-user deployment; would need revisiting before opening
  registration to the general public.

## Update — `ADMIN_BOOTSTRAP_ENABLED`

The risk noted above (open registration + automatic first-user-admin) is
partially addressed: `_is_bootstrap_admin` (`backend/app/api/auth.py`) now
checks `settings.admin_bootstrap_enabled` (default `true`) before the
`count == 0` check. Operators are expected to set it to `false` in `.env`
immediately after creating their own admin account on a public deployment
— see [deployment.md](../deployment.md#fork-it-and-make-it-yours)'s "Fork
it and make it yours" checklist. This narrows the
exposure window but doesn't close it outright (still a check-then-act race
during that window); invite-only registration or email verification would
be the fuller fix, not implemented here.
