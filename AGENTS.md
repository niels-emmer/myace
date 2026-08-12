# MyACE — AI Agent Maintenance Guidelines

This document defines the rules and conventions for AI coding agents (Claude Code, OpenCode, Codex, etc.) maintaining the MyACE codebase. It is the single source of truth for agent-facing rules and gotchas — `CLAUDE.md` imports this file (via Claude Code's `@AGENTS.md` memory-import syntax) and adds only genuinely Claude-Code-specific notes on top, so don't duplicate content there.

## What this is

MyACE ("My Agentic Coding Environment") makes AI agent configurations (rules, skills, agent definitions, workflows, model configs) portable across frameworks (OpenCode, Claude Code, Cursor, and others). It stores everything as a **Canonical Intermediate Representation (IR)** — Markdown with YAML frontmatter — and translates that IR into target-framework-specific files via adapters. See [docs/architecture.md](docs/architecture.md) for the full picture.

Three components:
- **`backend/`** — FastAPI + SQLModel API (Postgres in prod, SQLite for tests) that stores collections/artifacts/profiles and compiles profiles into target files.
- **`frontend/`** — React + Vite + TailwindCSS SPA (served by nginx in prod, proxies `/api/*` to the backend).
- **`cli/`** — Python Typer CLI (`myace`) that pulls compiled profiles from the server and can scan local config directories to import them.

## Commands

### Backend (from `backend/`)
```bash
pip install -e ".[dev]"          # install with dev deps
pytest                           # run all tests
pytest tests/test_adapters.py    # run one test file
pytest tests/test_adapters.py::test_name -v   # run a single test
ruff check .                     # lint
mypy app                         # type check (strict mode)
alembic revision --autogenerate -m "description"   # new migration
alembic upgrade head              # apply migrations
```
Tests use SQLite (`aiosqlite`) via `tests/conftest.py`, not Postgres — no running DB needed to run the suite. The `db_session` fixture spins up a fresh in-memory SQLite engine per test and overrides the `get_session` FastAPI dependency to point at it (`app.dependency_overrides[get_session]`); any test that exercises an authenticated route should depend on `async_client` (which itself depends on `db_session`), not construct its own client. Requires `greenlet` installed (a runtime dependency of SQLAlchemy's async engine, listed explicitly in `pyproject.toml` since it isn't pulled in automatically by `sqlmodel`/`asyncpg`).

### Frontend (from `frontend/`)
```bash
npm install
npm run dev       # Vite dev server on :5173, proxies /api to :8000
npm run build     # tsc -b && vite build
npm run lint       # eslint .
npm run test       # vitest
```
`npm run dev`'s proxy target (`vite.config.ts`) is `http://localhost:8000`, not the Docker-network hostname `backend` — the frontend's Docker image always serves a static nginx build (see `docker-compose.yml`), so this proxy is only ever exercised by `npm run dev` running on the host, per `docker-compose.dev.yml`'s own comment. Run `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d` first so the backend is reachable on `localhost:8000`, then `npm run dev` separately for HMR.

### CLI (from `cli/`)
```bash
pip install -e ".[dev]"
pytest
myace --help
```

### Full stack (Docker)
```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
docker compose exec backend alembic upgrade head
```
Dev stack: frontend on `:80`, backend on `:8000` directly, home dir mounted at `/host-home` (needed for the scanner to reach host config dirs like `~/.claude`, `~/.config/opencode`). See the compose file table in [README.md](README.md#compose-files) for the dev/prod override layering.

## Repository Architecture Rules

### 1. Strict Typing Standards

**Backend (Python):**
- All function signatures MUST include type annotations.
- Use `SQLModel` models for all database entities.
- Use `Pydantic v2` for all API request/response schemas.
- Never use `Any` or `dict` without a concrete type parameter.
- Use `X | None` (PEP 604), not `Optional[X]` — enforced by ruff's `UP` rules (`backend/pyproject.toml`), which run in CI.

**Frontend (TypeScript):**
- All function parameters and return types MUST be annotated.
- Use `interface` over `type` for object shapes.
- Define shared types in `src/types/` matching backend Canonical IR.

### 2. Database Migration Rules

- Every schema change requires an Alembic migration.
- Migrations must be reversible (`downgrade()` defined).
- Never modify a committed migration — create a new one.
- Name migrations descriptively: `add_profile_visibility_column`.

### 3. Target Adapter Structure

Each adapter in `backend/app/adapters/` MUST implement:

```python
class BaseAdapter(ABC):
    @abstractmethod
    def adapter_name(self) -> str: ...

    @abstractmethod
    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]: ...
```

- `translate()` returns a dict of `{filename: file_content}` for the target framework.
- Adapters are stateless — all state lives in the composition engine.

### 4. API Versioning

- All routes are prefixed with `/api/v1/`.
- Breaking changes require a new version prefix (`/api/v2/`).
- Backward-compatible additions are allowed within a version.

### 5. Canonical IR Schema

The Canonical Intermediate Representation is the single source of truth:

```yaml
type: rule | skill | agent | workflow | model_config
name: str
version: str (semver)
target_compatibility: list[str]
priority: int (0-100)
tags: list[str]
description: str
body: str (markdown)
```

### 6. Testing Requirements

- Backend: pytest with httpx AsyncClient for API tests.
- Frontend: Vitest + React Testing Library for component tests.
- CLI: pytest with Typer CliRunner for integration tests.
- Minimum coverage: 80% for new code.

### 7. Git Workflow

- Branch from `main`: `feat/description`, `fix/description`, `chore/description`.
- Commits follow conventional commits: `feat:`, `fix:`, `chore:`, `docs:`.
- PRs require at least one review before merging to `main`.
- **`main` is protected** — CI must pass, at least one approving review is
  required, and stale reviews are dismissed on new pushes. Never push
  directly to `main`; always work from a feature/fix/chore branch.

### 8. Scanner Module (CLI + Backend)

Two parallel scanner implementations exist — keep them in sync:

- `cli/myace_cli/scanner.py` — used by `myace import` CLI command
- `backend/app/services/scanner.py` — used by `POST /api/v1/collections/scan` endpoint

Both MUST support scanning these directory structures:

| Directory | File Pattern | Artifact Type |
|-----------|-------------|---------------|
| `skills/<name>/` | `SKILL.md` | `skill` |
| `agents/` | `*.md` | `agent` |
| `commands/` | `*.md` | `workflow` |
| root | `AGENTS.md` (## sections) | `rule` |
| root | `opencode.json` (models + MCP) | `model_config` |

The backend scanner includes Docker path resolution (`/host-home/` mount, broken symlink handling).

The backend scanner additionally supports scanning a Git repository (`scan_git_repository()` — shallow clone to a temp dir, then delegates to the same directory-scanning logic). This is **web-only**: the CLI's `myace import` still only accepts `--path`. If you add git-source support to the CLI, keep its artifact discovery in sync with both existing scanners per the table above.

`backend/app/services/github_export.py` is the inverse: converts canonical artifacts back into this same directory layout and pushes them to a GitHub branch + PR via the REST API. Keep `artifacts_to_files()` (export) and the scanner's parsers (import) symmetric — a collection exported to GitHub should scan back to the same artifacts.

### 9. Compose File Strategy

Three compose files with layered overrides:

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Base — single-machine prod on `:80` |
| `docker-compose.dev.yml` | Dev — adds `:8000` for backend, mounts `~/` to `/host-home/`, CORS for Vite |
| `docker-compose.prod.yml` | VPS — removes host ports, attaches external proxy network via `PROXY_NETWORK` |

Usage: `docker compose -f docker-compose.yml -f docker-compose.<layer>.yml up -d`

### 10. Security Rules

- Never log tokens, secrets, or PII.
- All database IDs are UUIDs, not auto-increment integers.
- API keys are hashed with bcrypt before storage.
- OIDC state parameters use cryptographically random nonces.
- OIDC authorization code flow uses PKCE (S256) — `code_verifier` is stored
  in the session, `code_challenge` is sent with the authorize redirect. Never
  skip PKCE when adding a new OIDC provider.
- **`auth_callback()` must explicitly forward the stashed `code_verifier`.**
  Authlib only auto-manages PKCE (generating and replaying the verifier via
  its own session-backed state) when `code_challenge_method` is set on the
  client *at registration time*. This codebase passes `code_challenge`/
  `code_challenge_method` per-request to `authorize_redirect()` instead (so
  the same generic client works for all three providers), which means
  Authlib's internal state never contains a verifier — `auth_callback()`
  must `request.session.pop("code_verifier", None)` and pass it explicitly
  to `client.authorize_access_token(request, code_verifier=code_verifier)`.
  Omitting this doesn't fail locally against mocked tests; it 500s against
  every real provider at the token-exchange step with a PKCE mismatch
  error, since nothing else in the request/response cycle surfaces the
  problem until a provider actually validates a real `code_challenge`
  against a missing `code_verifier`.
- **GitHub is plain OAuth2, not OIDC — it needs an explicit `userinfo_endpoint`
  and provider-specific field mapping.** `get_oauth_client()`
  (`backend/app/core/security.py`) must register GitHub with
  `api_base_url`/`userinfo_endpoint` set to `https://api.github.com/` /
  `https://api.github.com/user` — there's no discovery document for Authlib
  to find `userinfo_endpoint` from, so omitting it makes
  `client.userinfo()` raise `KeyError: 'userinfo_endpoint'`. GitHub's
  `/user` response also doesn't use OIDC claim names (`id` not `sub`,
  `login`/`avatar_url` not `preferred_username`/`picture`), and `email` is
  null unless the user made one public *even with the `user:email` scope
  granted* — the real address lives at `/user/emails`, which
  `auth_callback()` falls back to via `_fetch_github_primary_email()`. Any
  new non-OIDC provider needs this same explicit-endpoint-plus-field-mapping
  treatment, not the generic `sub`/`email`/`name`/`picture` path that works
  for true OIDC providers (Google, generic OIDC).
- Every route (except `/health` and the auth entry points listed in rule 13) requires `Depends(get_current_user)` — never accept a client-supplied `owner_id`/`user_id` as the source of truth for who's making the request. Ownership on create always comes from `current_user.id`.
- The GitHub PR export endpoint (`POST /collections/{id}/export/github`) takes a `github_token` in the request body, uses it for that single request only, and never persists or logs it — same rule as any other token, just worth calling out since it's user-supplied per-request rather than stored server-side.
- **Registration must never authenticate without a password.** The
  `/auth/register` endpoint returns a fake `UserRead` (with a random UUID)
  when the email already exists, to prevent both user enumeration and
  authentication bypass. Never set `request.session["user_id"]` or return
  the real user row in the duplicate-email path.
- **Bound bcrypt verification loops.** When matching a Bearer token against
  stored hashes, cap the candidate list at 10 before iterating — prevents
  DoS via crafted tokens that share a prefix with many active tokens.
- **Use `Literal` types for constrained string fields.** `artifact_type`,
  `source_type`, and `target` use `Literal` to reject invalid values at the
  schema validation layer (422) rather than at the business logic layer
  (400). Add `Literal` to any new field that has a fixed set of allowed
  values.

### 11. Artifact Response Serialization

`Artifact.tags` and `Artifact.target_compatibility` are stored as JSON-encoded `Text` columns, but `ArtifactRead` (and `CanonicalArtifact`) declare them as `list[str]`. Never return a raw SQLModel `Artifact` row from an API route — FastAPI's response validation will 500 (`ResponseValidationError`) on any row with actual tags/compatibility data. Always convert through `_artifact_to_read()` in `backend/app/api/collections.py` (or `_db_to_canonical()` in `backend/app/services/compiler.py` for the compiler path), which `json.loads()` both fields first.

### 12. Frontend React Query Cache Keys

When two components fetch the same resource with different filters (e.g. an unfiltered list vs. a `visibility=public` list), give them distinct query keys — fold the filter into the key, e.g. `['collections', { visibility: 'public' }]`. Reusing a bare `['collections']` key for differently-filtered queries causes cache collisions: whichever query resolves first silently overwrites the cached data for every other component using that key, and the wrong data can appear during client-side (non-reload) navigation.

### 13. Authentication & Authorization

- **Two auth mechanisms, one dependency.** `get_current_user` (`backend/app/core/deps.py`) accepts either a session cookie (`request.session["user_id"]`, web UI) or a Bearer API token (CLI). Public routes are the explicit exception list: `/health`, `/auth/register`, `/auth/login`, `/auth/login/{provider}`, `/auth/callback/{provider}`, `/auth/providers`. Everything else requires it.
- **Authorization is ownership + visibility, not per-route roles.** Use `authorize_access()` (single resource) and `owner_or_public_clause()` (list endpoints) from `backend/app/core/authz.py` — don't hand-roll owner checks. `authorize_access` 404s (not 403s) on denial, matching the rest of the codebase's convention of not revealing a resource's existence to someone who can't see it. `current_user.is_admin` bypasses both.
- **`Artifact` has no `owner_id` of its own.** Authorize against its parent `Collection` — load the collection first, call `authorize_access` on that, then proceed.
- **Bulk/cross-resource operations need a check per resource touched.** `bulk_export_artifacts`'s target collection needs its own write-check independent of the source collection's read-check — don't assume checking one resource covers every resource an endpoint touches.
- **No more placeholder users.** `backend/app/services/placeholder_user.py` is gone. If you're tempted to special-case a nil/empty `owner_id`, that's a sign the route is missing `Depends(get_current_user)`.
- **Admin-on-another-user actions never touch the caller's own row.** `PATCH /auth/users/{id}?is_active=<bool>` and `DELETE /auth/users/{id}` (`backend/app/api/auth.py`) both 400 if `user_id == current_user.id` — self-service account changes go through `/auth/me`/`DELETE /auth/me` instead. This isn't just a UX nicety: it's what guarantees these two routes can never lock out every admin, since the caller (`require_admin` + `get_current_user`'s active-only filter) is always a distinct, active admin — don't add a separate "last admin" counting check on top, it would be dead code.
- **`DELETE /auth/users/{id}` mirrors `DELETE /auth/me`'s cascade exactly** (soft-deactivate owned collections, soft-delete owned profiles, deactivate API tokens — see `_deactivate_owned_resources()`). If you change one, change the other, or extract further shared logic rather than letting them drift.

### 14. Documentation Maintenance

This project maintains documentation for two audiences, and both are kept up to date in the same PR as the code they describe — not as follow-up cleanup:

- **Human documentation**: `README.md` (what MyACE is, how to run it, public-facing) and `docs/` (deep dives — see [`docs/README.md`](docs/README.md) for the full index: architecture, data model, invariants, ADRs, debugging, extending).
- **Agentic documentation**: this file (`AGENTS.md`) and `CLAUDE.md` (terse, enforceable rules and gotchas for AI coding agents working in this repo).

Concretely, before you consider a change done:

- **New route, model field, or config setting** → update the relevant table in `README.md` and, if it changes the data model or an invariant, `docs/data-model.md`/`docs/invariants.md`.
- **New non-obvious pattern, gotcha, or convention** → add a numbered rule here (or to `CLAUDE.md`) *and* a corresponding entry in `docs/debugging.md` if it's the kind of thing someone will hit and need to search for.
- **A decision that's expensive to reverse or could reasonably have gone another way** (a new auth mechanism, a data model shape, a deployment change) → write an ADR in `docs/adr/` — see [`docs/adr/README.md`](docs/adr/README.md) for when and how.
- **A rule or doc becomes stale** (the code changed, the doc didn't) → fix it in the same PR, don't leave it for later. A stale doc is worse than no doc, because it's actively misleading.
- **Removing a feature or file** → grep for it across `README.md`, `AGENTS.md`, `CLAUDE.md`, and `docs/` before considering the removal complete; dangling references to deleted code are a common way this drifts.

If you're an AI agent and you're not sure whether a change is "documentation-worthy," err toward writing the one or two sentences — it's cheap now and expensive to reconstruct later.

### 15. Soft-Delete Rule

- **Never hard-delete user data.** Artifacts, profiles, and doc cache entries
  use soft-delete (`deleted_at = datetime.now(UTC)`) instead of
  `session.delete()`. Collections use `is_active = False`. API tokens use
  `is_active = False`. Every list/get query must filter out soft-deleted
  rows (`deleted_at == None` or `is_active == True`). If you add a new
  resource type, use soft-delete — never hard-delete.

### 16. Community Collections Route Ordering

- **Static `/community` routes must be registered before the dynamic
  `/{collection_id}` route** in `backend/app/api/collections.py`. FastAPI
  matches routes by registration order, and "community" looks like a UUID
  path parameter — if `/{collection_id}` comes first, all `/community/*`
  GET requests fail with a 422 UUID parse error. The fix is registering
  `/community`, `/community/top`, and `/community/categories` above
  `get_collection`.

### 17. Import Updates download_count

- **`POST /{collection_id}/import` must increment `download_count` on the
  source collection.** This is the only place `download_count` is written
  (it's never set by publish — that only sets `published = True`). If you
  add another import-like operation for community collections, update the
  counter there too.

### 18. Publish Is Self-Serve, Not a GitHub PR — and Is Unrelated to Starter Packs

- **`POST /{collection_id}/publish` is a pure DB write, immediate and
  ungated.** It sets `published=True` and `visibility="public"` (and, if
  provided, overwrites `name`/`description` with `publish_name`/
  `publish_description`) on the caller's own `Collection` row. That's the
  entire operation — no GitHub call, no `github_token`, no PR, no admin
  approval step. `GET /collections/community` lists anything with
  `published=True AND is_active=True`; there's nothing else to satisfy.
- **This used to open a GitHub PR against this repo's `collections/`
  folder** (`app/services/publish.py`, removed) with UI copy promising "an
  admin will review and approve." It didn't actually gate anything — the DB
  flag flipped regardless of the PR's fate — so the review step was fake.
  Don't reintroduce a PR-based publish flow; if a real moderation gate is
  wanted, add an explicit `review_status`-style field enforced in
  `list_community_collections()`, not a side-channel GitHub PR.
- **The starter-pack set (rule 25) is a completely separate, one-directional
  thing.** It's a fixed list hand-maintained in this repo's `collections/`
  directory, changed via the normal branch → PR → CI → merge → deploy
  workflow (by a human or an agent working in this repo), and picked up by
  `seed_starter_collections()` on backend boot. Nothing a user publishes
  through the API ever flows into it automatically.

### 19. Admin-Editable Secrets Must Go Through `app/core/crypto.py`

- **Any secret an admin can enter via System Settings (SMTP password, OAuth
  client secrets) must be encrypted before it touches the database** — use
  `encrypt_secret()`/`decrypt_secret()` from `backend/app/core/crypto.py`
  (Fernet, keyed by `settings.settings_encryption_key`). See
  [ADR-0006](docs/adr/0006-encrypted-admin-editable-secrets.md).
- Follow the established shape: the "Update" Pydantic schema takes a
  plaintext, write-only field (e.g. `smtp_password`); the route handler
  encrypts it into the `_encrypted` DB column; the "Read" schema exposes
  only a computed `{field}_set: bool`, never the encrypted value itself.
  `system_settings.py`'s `SystemSettingsRead.from_settings()` is the
  reference implementation.
- `get_effective_*_config()` helpers in
  `backend/app/services/effective_settings.py` are where "DB value
  overrides env var if non-empty, else env var" is resolved — new
  admin-editable config should extend that module rather than re-deriving
  the precedence rule inline at each call site.

### 20. OAuth Clients Are Rebuilt Per-Request From Effective Config, Not Registered Once at Import

- **`security.py` no longer holds a module-level `oauth` singleton.**
  `get_oauth_client(provider, config)` builds (or returns a cached) Authlib
  remote app from the provider's *effective* config (DB override merged
  over env — see rule 19), keyed by a fingerprint of that config. This is
  what lets a credential saved via System Settings take effect on the next
  login/callback request without restarting the backend.
- Authlib's `OAuth.create_client()` permanently caches the first client it
  builds for a given name — calling `oauth.register()` again with new
  credentials does **not** rebuild an already-cached client. `get_oauth_client()`
  works around this by constructing a fresh `OAuth()` registry (cheap) only
  when the fingerprint changes, rather than mutating Authlib's internal
  `_clients` cache directly.
- Every call site (`login()`, `auth_callback()`, `get_providers()` in
  `backend/app/api/auth.py`) must call `get_effective_oauth_config(provider,
  session)` first and pass the result to `get_oauth_client()` — never call
  `get_oauth_client()` with hand-built config, and never reintroduce a
  module-level `oauth.create_client(provider)` call.

### 21. Adapter Enable/Disable — Enforce at the compile_profile() Choke Point

- **Adapters themselves stay static, stateless Python classes** (rule 3) —
  `system_settings.disabled_adapters` (a JSON-encoded `list[str]`, admin-only,
  toggled via `PATCH /admin/adapters/{name}?enabled=<bool>`) is an
  *enforcement* layer on top of the registry, not a change to how adapters
  are registered.
- **The enforcement check lives in `compile_profile()`**
  (`app/services/compiler.py`), immediately before `get_adapter(target)` is
  called, raising `AdapterDisabledError` if `target` is in the disabled
  list. Both `/profiles/compile` and `/profiles/compile/zip` funnel through
  this one function — if you add a third way to compile a profile, route it
  through `compile_profile()` too rather than calling `get_adapter()`
  directly, or it will silently bypass the disabled check.
- The frontend additionally filters disabled adapters out of
  `TargetExporter.tsx`'s target picker — that's a UX nicety, not the
  enforcement boundary. Don't rely on it alone; the backend check is what
  actually matters for a direct API call or a CLI `myace pull`.
- If you add a new adapter, no `disabled_adapters` change is needed — it
  defaults to enabled (absent from the list) automatically.

### 22. Zip Compile Endpoint Filename Sanitization

- `POST /profiles/compile/zip` (`backend/app/api/profiles.py`) builds its
  `Content-Disposition` filename via `github_export.py`'s `slugify()`,
  never the raw `profile.name`/`target`. Profile names are
  attacker-controllable on profiles you don't own (public profiles), so an
  unsanitized filename would be a header-injection vector into another
  user's response. Any new route that echoes a user-supplied string into a
  response header needs the same treatment.

### 23. Frontend Adapter Pickers Must Read `adapter.name`, Not `adapter.targets`

- `GET /adapters`/`GET /adapters/{name}` responses include each adapter's
  `supported_targets()` aliases (e.g. `claude-code`/`claude`) purely as
  metadata. Only the primary `adapter_name()` is ever a valid compile
  `target` or lookup key. UI code building a target picker (e.g.
  `TargetExporter.tsx`) must read `adapter.name`, not flatten
  `adapter.targets` into options.

### 24. Local Companion Server (`myace serve`) Security Model

- `cli/myace_cli/local_server.py` runs a small FastAPI app on
  `127.0.0.1:8765` (lazy-imports `fastapi`/`uvicorn` — only
  `pip install "myace-cli[serve]"` needs them, not the base CLI) so the web
  UI can scan the user's *own* machine without the browser needing
  filesystem access. It reuses `cli/myace_cli/scanner.py`'s
  `scan_directory()` directly — no third parallel scanner implementation.
- Security model — preserve all of it if you touch this file: refuses to
  start without existing `myace login` credentials; binds loopback-only;
  CORS reflects exactly the logged-in server's origin (never `*`);
  `POST /scan` additionally requires a custom `X-MyACE-Companion` header
  (forces a real preflight, blocks blind `no-cors` POSTs) and a
  server-side `Origin` check (not just a CORS response header) so a
  non-browser client can't skip the dance. Also implements Chrome's
  Private Network Access preflight (`Access-Control-Allow-Private-Network`)
  since a page on a public origin fetching a loopback address gets an
  extra preflight beyond normal CORS.
- **Gotcha — never add `from __future__ import annotations` to this
  file.** Its FastAPI app, route handlers, and Pydantic model are all
  defined *inside* `build_app()` so the base CLI install never needs
  fastapi/uvicorn. PEP 563 turns every annotation into a string that
  FastAPI resolves via `typing.get_type_hints()` against the function's
  *module* globals — which don't include names only bound in
  `build_app()`'s local scope, so `Request`/the request model silently
  fail to resolve and every route 422s as if the parameters don't exist.
- The web UI's "Local Machine" import source (`ImportPage.tsx`) talks to
  this server exclusively. The backend's own
  `POST /collections/scan?source_type=local` route is left in place for
  direct-API/dev use but is unreachable from the hosted web UI — on a real
  deployment it would scan the *server's* filesystem, not the visitor's.
  `ImportPage.tsx` polls `GET /health` on this server while "Local
  Machine" is selected and shows a setup panel when it's unreachable.

### 25. Starter Packs Are Seeded, Not Scanned

- `backend/app/services/seed_collections.py` turns
  `collections/{base,additional}/<slug>/` into `Collection`+`Artifact` row
  sets on every backend startup (`seed_starter_collections()`, called from
  `app/main.py`'s lifespan), owned by a dedicated, **passwordless** system
  account (`starter-packs@myace.local` — `password_hash` stays `None`, so
  it can never authenticate via `/auth/login`) that exists purely to
  satisfy `Collection.owner_id`'s `NOT NULL` FK. Every seeded collection
  ships `published=True` + `visibility="public"` + `is_starter_pack=True`.
- Idempotent by `(name, is_starter_pack)` lookup — safe to call
  unconditionally on every restart/replica, unlike `init_db()` (dev-only).
  Seeding failures (e.g. schema not migrated yet on a brand-new
  deployment) are caught and logged, never raised — a seeding problem must
  never block the app from starting; the next restart after migrations
  land picks it back up.
- Deliberately does **not** call the public `scanner.scan_directory()` —
  that function's path resolution confines scans to `settings.scan_root`
  as a security boundary against arbitrary *user-supplied* local-machine
  paths, which doesn't apply to these hardcoded, trusted paths. It reuses
  the scanner's private per-file parsers (`_parse_skill_file`,
  `_parse_agent_file`, `_parse_command_file`, `_parse_agents_md`) directly
  against a local directory walk instead, so the on-disk format stays in
  sync with what the scanner (and therefore the community-import flow)
  already understands.
- To add a starter pack: create the directory under
  `collections/{base,additional}/<slug>/` in the scanner's format, then
  add an entry to `STARTER_COLLECTIONS` in `seed_collections.py` with its
  display `name`/`category`/`description` — no migration needed.

### 26. Session `user_id` Must Be Parsed Back Into a `uuid.UUID` Before Querying

- The session cookie stores `str(user.id)` (session payloads are JSON, no
  native UUID type), so `_user_from_session` (`backend/app/core/deps.py`)
  must do `uuid.UUID(raw_user_id)` before comparing against `User.id`.
  Comparing the raw string directly works against `asyncpg`/Postgres
  (which coerces loosely) but throws
  `AttributeError: 'str' object has no attribute 'hex'` under SQLite's
  `Uuid` bind processor — this only surfaces once a test actually
  exercises a session-cookie-authenticated route against real SQLite (see
  the `db_session` fixture note under Commands, above).

### 27. Production Hardening Checks in `app/main.py`

- `APP_SECRET_KEY` still being the placeholder is a `RuntimeError` in
  production (not just a warning) — see
  [debugging.md](docs/debugging.md#backend-refuses-to-start-runtimeerror-app_secret_key-is-still-the-default).
- `TrustedHostMiddleware` is **always** registered: it defaults to `['*']`
  in development, but raises a `RuntimeError` at startup in production if
  `TRUSTED_HOSTS` is unset. This is what prevents Host-header injection
  behind a reverse proxy — never relax it to a default-allow in
  production.
- `backend/Dockerfile`'s uvicorn `CMD` runs with
  `--proxy-headers --forwarded-allow-ips=*`, which is safe only because
  `docker-compose.prod.yml` exposes no host port (only the reverse-proxy
  container on the same Docker network can reach it) — don't copy that
  flag into a setup where the backend is directly internet-reachable.
- That `X-Forwarded-Proto` trust only helps if it survives the full hop
  chain. In `docker-compose.prod.yml`, requests pass through an external
  reverse proxy *and* the `frontend` nginx container's `/api/` location
  before reaching the backend — `frontend/nginx.conf` must forward the
  header it already received (`map`-based fallback to its own `$scheme`
  only when nothing set it), never unconditionally overwrite it with
  `$scheme`, or every OAuth `redirect_uri` silently becomes `http://` no
  matter what the external proxy saw. See
  [debugging.md](docs/debugging.md#githubgoogleoidc-login-fails-with-redirect-uri-is-not-associated-with-this-application-behind-a-reverse-proxy).

### 28. Frontend Structure Gotchas

- **Two different things are called "export" — don't conflate them.**
  `TargetExporter.tsx` (`/compile`) compiles a **Profile** into a target
  framework's files (copy-paste, zip download, or CLI pull).
  `CollectionDetail.tsx`'s "Export to GitHub" button pushes a
  **Collection**'s canonical artifacts to a real GitHub branch + PR. They
  share no code path.
- `ImportPage.tsx`'s Local Machine / GitHub Repository source toggle
  shares one scan → select → import flow, but Local Machine scans hit the
  `myace serve` companion server (rule 24), not the backend.
- `UserSettings.tsx`'s "CLI Setup" block is generated, not static copy —
  it interpolates `window.location.origin` and the just-created API
  token. Never hardcode a server URL or placeholder token back into it; a
  wrong one silently breaks first-run onboarding.
- `CollectionDetail.tsx`'s confirm-before-destructive-action modal is this
  codebase's only such pattern — copy it (don't invent a new one) for any
  new destructive frontend action.
- When two components fetch the same resource with different filters
  (rule 12), or need distinct list scoping, give them distinct React
  Query keys — `CollectionDetail.tsx` scopes to `['collection', id]` /
  `['artifacts', id, typeFilter]` rather than the shared `['collections']`/
  `['profiles']` keys used elsewhere.
