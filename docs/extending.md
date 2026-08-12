# Extending MyACE

Task-oriented guides for common changes. Each one assumes you've read
[architecture.md](architecture.md) and, if you're touching auth, the
[Authorization invariants](invariants.md#authorization).

## Adding a target adapter

To support a new framework (say, "Continue.dev" — see `ADAPTERS_RESEARCH.md`
for other unbuilt candidates; don't reuse one of the 7 already shipped in
`backend/app/adapters/__init__.py`):

1. **Backend**: create `backend/app/adapters/continue_dev.py` implementing
   `BaseAdapter` (see `backend/app/adapters/base.py` for the interface):
   ```python
   class ContinueDevAdapter(BaseAdapter):
       def adapter_name(self) -> str: return "continue-dev"
       def supported_targets(self) -> list[str]: return ["continue-dev"]
       def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
           ...  # canonical artifacts in, {filename: content} out
   ```
   Register it in `backend/app/adapters/__init__.py`'s adapter list.
2. **Compile endpoint**: add the adapter's primary name to the `target`
   `Literal` in `ProfileCompileRequest` (`backend/app/models/profile.py`).
   This is easy to forget and fails silently in a confusing way: the adapter
   works fine in isolation, but `POST /profiles/compile` 422s on it forever
   because Pydantic rejects the request before it ever reaches
   `get_adapter()` — this exact bug shipped for four adapters (`codex-cli`,
   `copilot-cli`, `cline`, `windsurf`) until it was caught and fixed.
3. **CLI fallback**: mirror the same adapter in
   `cli/myace_cli/adapters/continue_dev.py` — the CLI keeps its own copies so
   `myace pull` can render locally if the server is unreachable. Keep the
   two in sync; there's no automated check for this today. (In practice the
   CLI currently only mirrors the original three — `claude_code`, `opencode`,
   `cursor` — so this step is aspirational for the other four until someone
   backports them.)
4. **Test**: add a `TestContinueDevAdapter` class to
   `backend/tests/test_adapters.py` following the existing pattern (see
   `TestClaudeCodeAdapter`, `TestCodexCliAdapter`, `TestWindsurfAdapter`,
   etc.) — at minimum, one test per artifact type your adapter handles
   specially.
5. **Docs**: add a row to the target adapters table in `README.md`, and to
   the adapter list in `architecture.md` and `CLAUDE.md`.

Adapters must stay stateless and pure — see
[invariants.md #9](invariants.md#canonical-ir). Don't reach into the
database or filesystem from inside `translate()`.

## Adding a new artifact type

The five artifact types (`rule`, `skill`, `agent`, `workflow`,
`model_config`) are a closed set referenced in a lot of places. Adding a
sixth means touching all of:

1. `backend/app/models/artifact.py` — nothing to change in the model itself
   (`artifact_type` is a plain string), but update the docstring/comment.
2. Every adapter's `translate()` — decide how the new type renders for each
   target framework, including "doesn't apply here, skip it."
3. `backend/app/services/scanner.py` **and**
   `cli/myace_cli/scanner.py` — how does this type get *discovered* from a
   directory scan? Update both (see the scanner-duality rule in
   `AGENTS.md`).
4. `backend/app/services/github_export.py`'s `artifacts_to_files()` — the
   inverse of step 3. Keep it symmetric (invariant #10).
5. `frontend/src/types/index.ts`'s `ArtifactType` union, and anywhere the
   frontend special-cases type (e.g. `CollectionDetail.tsx`'s
   `ARTIFACT_TYPES` filter list and `typeColors` map).

## Adding an SSO provider

OIDC (generic), GitHub, and Google are already wired via Authlib
(`backend/app/core/security.py`). Credentials for all three can be set
either via `.env` or, since the OAuth provider admin UI shipped, via System
Settings → Authentication Providers — click a provider row to expand it,
which shows the exact callback URL to register with the provider and fields
for Client ID/Secret (and Issuer URL/Scopes for OIDC). A "Test Connection"
button checks reachability/format (not a full login — that needs a real
browser redirect, hence the "Sign in with X" callout in its result message).
See [ADR-0006](adr/0006-encrypted-admin-editable-secrets.md) for how the
secret is stored.

To add a fourth provider that also speaks OAuth2/OIDC:

1. Add `<provider>_client_id`/`<provider>_client_secret` (and any
   provider-specific URLs) to `backend/app/core/config.py`, and matching
   `{provider}_client_id`/`{provider}_client_secret_encrypted` columns to
   `SystemSettings` (+ a migration) if it should also be admin-editable.
2. Extend `get_effective_oauth_config()`
   (`backend/app/services/effective_settings.py`) with the new provider's
   branch, and add it to `get_oauth_client()`'s registration branches in
   `security.py`, following the GitHub/Google examples.
3. Add `"<provider>"` to the allowed-providers checks in
   `backend/app/api/auth.py`'s `login()`/`auth_callback()` routes and to
   `OAUTH_PROVIDERS` in `backend/app/api/admin.py`.
4. Add it to `GET /auth/providers`'s response and to the frontend's
   `AuthProviders` type (`frontend/src/types/index.ts`), `Login.tsx`'s
   button list, and `PROVIDER_INFO` in `SystemSettings.tsx` (setup steps +
   console/docs links for the credentials accordion).

No database migration needed for `users` — `User.oidc_provider` is a plain
string, not an enum.

## Configuring SMTP for password reset

Password-reset emails (`POST /auth/forgot-password`) are sent via SMTP,
configured either through `.env` (`SMTP_HOST`/`SMTP_PORT`/`SMTP_USERNAME`/
`SMTP_PASSWORD`/`SMTP_FROM_EMAIL`/`SMTP_FROM_NAME`/`SMTP_USE_TLS` — see
`.env.example`) or through System Settings → Email (SMTP), which an admin
can use instead of editing `.env` and restarting. A value saved via System
Settings overrides the matching env var at runtime
(`backend/app/services/effective_settings.py`); the master `smtp_enabled`
toggle there has no env-var equivalent — it defaults off, so email sending
stays inert until an admin explicitly turns it on.

Requires `SETTINGS_ENCRYPTION_KEY` (`.env.example`) to be set before the
SMTP password can be saved via the UI — see
[ADR-0006](adr/0006-encrypted-admin-editable-secrets.md). Use the "Send Test
Email" button on the System Settings page to validate a configuration (host/
port/credentials as currently typed, not necessarily saved yet) before
relying on it — it sends a real email to the requesting admin's own address.

## Configuring SMTP for password reset

Password-reset emails (`POST /auth/forgot-password`) are sent via SMTP,
configured either through `.env` (`SMTP_HOST`/`SMTP_PORT`/`SMTP_USERNAME`/
`SMTP_PASSWORD`/`SMTP_FROM_EMAIL`/`SMTP_FROM_NAME`/`SMTP_USE_TLS` — see
`.env.example`) or through System Settings → Email (SMTP), which an admin
can use instead of editing `.env` and restarting. A value saved via System
Settings overrides the matching env var at runtime
(`backend/app/services/effective_settings.py`); the master `smtp_enabled`
toggle there has no env-var equivalent — it defaults off, so email sending
stays inert until an admin explicitly turns it on.

Requires `SETTINGS_ENCRYPTION_KEY` (`.env.example`) to be set before the
SMTP password can be saved via the UI — see
[ADR-0006](adr/0006-encrypted-admin-editable-secrets.md). Use the "Send Test
Email" button on the System Settings page to validate a configuration (host/
port/credentials as currently typed, not necessarily saved yet) before
relying on it — it sends a real email to the requesting admin's own address.

## Adding an API route

Every new route that touches user data must answer three questions before
it's done:

1. **Does it need `Depends(get_current_user)`?** Almost always yes — see
   [invariants.md #1](invariants.md#authorization). The only routes that
   skip it are the explicit public list in that same invariant.
2. **What's the access rule?** Pick one and implement it with the shared
   helpers (`backend/app/core/authz.py`), don't hand-roll a check:
   - Owner-or-admin, read: `authorize_access(owner_id=..., current_user=...,
     is_public=...)`
   - Owner-or-admin, write: same, with `write=True`
   - List endpoint: `owner_or_public_clause(...)` folded into the query
3. **Does it touch more than one resource?** If it reads from one resource
   and writes to another (like `bulk_export_artifacts`'s source/target
   collections), each one needs its own check —
   [invariants.md #6](invariants.md#authorization).

Add a row to the API table in `README.md`, and if the route is
security-relevant, a scenario to the verification list this project has
used historically (ask in your PR if you're not sure where that lives for
your change — see [`CONTRIBUTING.md`](../CONTRIBUTING.md)).

## Adding a bulk/cross-resource operation

Same as above, but explicitly: write a mental (or literal, in tests) table
of every resource the operation touches and what access level each needs.
`bulk_export_artifacts` is the reference example — its source collection
needs read access, its target collection (if it already exists) needs an
independent write check, and a brand-new target collection needs no check
(ownership is just assigned to `current_user.id`). Don't assume checking
the "primary" resource in the URL path covers every resource the handler
actually reads or writes.

## Improving type coverage

`mypy --strict` currently runs in CI as advisory only (it doesn't block
merges) — see [debugging.md](debugging.md#a-sqlalchemy-wherecolumn--true-clause-looks-wrong-to-a-linter).
Most of the backlog is missing return-type annotations on FastAPI route
handlers (mechanical, safe to add incrementally) plus a handful of genuine
SQLModel/SQLAlchemy-vs-mypy limitations around class-level column access
(`Column.in_()`, generic `Result` inference) that need either targeted
`# type: ignore[...]` comments with a reason, or a proper SQLAlchemy mypy
plugin setup — don't "fix" these by changing working query code (see the
same debugging entry). This is a good, low-risk first contribution: pick a
handful of functions, add return types, confirm `mypy app` complains less,
open a PR.

## Working on the frontend

- New pages go in `frontend/src/pages/`, added to both the route list in
  `App.tsx` and the sidebar in `Layout.tsx` if they need direct navigation.
- New API calls go in `frontend/src/lib/api.ts`, typed against
  `frontend/src/types/index.ts` — never call `fetch()` directly outside this
  file (see the credentials gotcha in
  [debugging.md](debugging.md#session-cookie-isnt-sent--user-gets-logged-out-unexpectedly)).
- If two components fetch the same resource with different filters, give
  them distinct React Query keys —
  [debugging.md](debugging.md#react-query-shows-stalewrong-data-after-client-side-navigation).
- `Layout.tsx`'s sidebar is a `lg:`-breakpoint responsive drawer: static
  and always visible at `lg` (1024px) and up, an off-canvas `fixed` panel
  below it (toggled by a `Menu`-icon button in a mobile-only top bar,
  closed by tapping the backdrop, its own `X` button, or navigating). New
  pages don't need to do anything special for this — content just renders
  in `<main>` below/beside it — but if a page adds its own wide content
  (a table, a multi-column form), wrap it so it doesn't cause horizontal
  scroll at 375px — an `overflow-x-auto` wrapper (see `SystemSettings.tsx`'s
  tables) or a `grid-cols-1 sm:grid-cols-2` pattern are the two used
  elsewhere in this codebase.
