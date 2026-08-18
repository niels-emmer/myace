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
Dev stack: frontend on `:80`, backend on `:8000` directly, home dir mounted at `/host-home` (needed for the scanner to reach host config dirs like `~/.claude`, `~/.config/opencode`). See the compose file table in [docs/deployment.md](docs/deployment.md#compose-files) for the dev/prod override layering.

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
    def expected_paths(self) -> list[str]: ...

    @abstractmethod
    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]: ...
```

- `translate()` returns a dict of `{filename: file_content}` for the target framework.
- `expected_paths()` (added Phase 4, rule 35) returns this adapter's conventional local file/directory names, used by the local setup audit — must match what `translate()` actually writes.
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

- **Two auth mechanisms, one dependency.** `get_current_user` (`backend/app/core/deps.py`) accepts either a session cookie (`request.session["user_id"]`, web UI) or a Bearer API token (CLI). Public routes are the explicit exception list: `/health`, `/auth/register`, `/auth/login`, `/auth/login/{provider}`, `/auth/callback/{provider}`, `/auth/providers`, and (Phase 4) `POST /demo/compile` — see rule 36 for why that last one is a deliberate, narrowly-scoped exception rather than a precedent for public routes in general. Everything else requires it.
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

- **The GitHub Wiki is a generated mirror of `docs/`, never a second copy to
  maintain by hand.** `.github/workflows/wiki-sync.yml` runs
  `scripts/sync_wiki.py` on every push to `main` that touches `docs/**`,
  republishing the human-facing subset of `docs/` (architecture, data model,
  invariants, extending, debugging, ADRs, adapter research — see the page
  map in `scripts/sync_wiki.py`) as Wiki pages with rewritten links/images.
  `docs/plans/*.md`, `AGENTS.md`, and `CLAUDE.md` are deliberately excluded
  — they're design records and agent rules, not visitor-facing reference
  docs. **Never edit a Wiki page directly** — it will be silently
  overwritten by the next sync; edit the source file in `docs/` instead and
  let CI republish it, same as every other doc in this rule.
- **A repo's Wiki git backend doesn't exist until a page has been created
  through the web UI at least once**, even with `has_wiki: true` — no
  amount of `git push` (including this sync) can bootstrap it first. See
  [debugging.md](docs/debugging.md#wiki-sync-action-fails-with-repository-wikigit-not-found)
  if the sync Action fails with `repository '....wiki.git' not found`.

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

### 18. Publish Goes Through Moderation, Not a GitHub PR — and Is Unrelated to Starter Packs

- **`POST /{collection_id}/publish` only submits for review — it is not a
  self-serve publish anymore.** It moves `Collection.moderation_status`
  from `draft`/`denied` to `submitted` (409 otherwise) and never touches
  `published`/`visibility`. The *only* code path that sets
  `published=True`/`visibility="public"` is
  `POST /moderation/{collection_id}/approve` (moderator/admin only, via
  `require_moderator_or_admin` — never `authorize_access`, whose
  owner-bypass would let an owner approve their own submission).
  `GET /collections/community` still filters on
  `published=True AND is_active=True`, but that predicate is only ever
  true for `moderation_status="approved"` rows now. See
  [ADR-0008](docs/adr/0008-collection-moderation-state-machine.md) for the
  full state machine and rule 30 below for the role that gates it.
- **This still isn't a GitHub PR.** The old self-serve flow described in a
  previous version of this rule (`app/services/publish.py`, removed) opened
  a GitHub PR against this repo's `collections/` folder with UI copy
  promising "an admin will review and approve" — it didn't actually gate
  anything, the DB flag flipped regardless of the PR's fate, so that
  review step was fake. The moderation queue described above is the real
  version of that promise: an actual DB-state gate, enforced server-side,
  with no GitHub involvement. Don't reintroduce a PR-based publish flow.
- **The starter-pack set (rule 25) is a completely separate, one-directional
  thing.** It's a fixed list hand-maintained in this repo's `collections/`
  directory, changed via the normal branch → PR → CI → merge → deploy
  workflow (by a human or an agent working in this repo), and picked up by
  `seed_starter_collections()` on backend boot — seeded straight to
  `moderation_status="approved"`, never routed through the queue. Nothing
  a user publishes through the API ever flows into it automatically.
- **`approved` can move to `unpublished`, post-hoc, via
  `POST /{collection_id}/unpublish`** — callable by the collection's owner
  *or* a moderator/admin (unlike `publish`/`approve`/`deny`, this one
  deliberately isn't owner-vs-moderator exclusive). Sets
  `published=False`, `visibility="private"`, reuses `moderation_reason`/
  `moderated_at`/`moderated_by`. This doesn't reopen ADR-0008's
  self-approval question — there's still no path back to `approved`
  except a fresh `publish` + moderator approval. See
  [ADR-0013](docs/adr/0013-post-hoc-unpublish.md) and rule 40.

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
- **A content-only edit to an already-shipped starter-pack file (no new
  collection, no new `STARTER_COLLECTIONS` entry) will NOT reach an
  already-seeded deployment on its own.** The `(name, is_starter_pack)`
  idempotency check above is collection-level, and it short-circuits
  before any artifact is looked at — `if existing.scalar_one_or_none() is
  not None: continue` skips the whole collection, including
  re-scanning its files, the moment a same-named starter collection
  already exists. Restarting (or redeploying) an install that already
  seeded `software-engineer` will not pick up a changed
  `orchestrator.md`, an added `handoff_to:` field, or any other
  in-place edit to that collection's source files — only a *new*
  collection (new slug/name) is ever picked up automatically. On an
  existing deployment, an in-place content change needs a manual fix
  (re-run seeding against a DB where that starter collection's rows have
  been deleted first, or hand-edit the affected artifact rows directly)
  — this is a known, unaddressed gap in the seeding mechanism itself, not
  something to work around ad hoc per content change. See
  [debugging.md](docs/debugging.md#my-starter-pack-content-edit-isnt-showing-up-on-an-existing-deployment)
  for the concrete symptom/fix.

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

- **`CollectionDetail.tsx` no longer has an "Export to GitHub" button.** It
  was removed — publishing a collection now goes exclusively through
  "Publish to Community" (rule 18). The backing
  `POST /collections/{id}/export/github` endpoint and
  `backend/app/services/github_export.py` (rules 8, 10) are untouched and
  still reachable by direct API use; nothing in the frontend surfaces them
  anymore. Don't reintroduce the button — if GitHub export needs a UI again,
  get explicit product direction first. `TargetExporter.tsx` (`/build/compile`)
  remains a separate, unrelated concept: it compiles a **Profile** into a
  target framework's files (copy-paste, zip download, or CLI pull).
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

### 29. Starter-Collection Artifact Names Must Be Unique Across Collections, Not Just Within One

- **`compile_profile()` deduplicates artifacts by name alone, across every
  collection in the profile, with later collections silently overriding
  earlier ones** (`backend/app/services/compiler.py`, step 4 of
  `compile_profile()`'s docstring). An agent, skill, or rule that shares
  its name with one in another collection doesn't merge or conflict
  loudly — one copy just vanishes from the compiled output.
- **This is no longer silent in the API response or the UI** — see rule 32.
  A `name_collision` warning is generated automatically on every compile,
  so the `grep` below is a way to *prevent* collisions proactively in
  `collections/` (this repo's own starter packs); it's no longer the only
  way to *detect* one after the fact.
- This matters most for `additional/` collections, since they're
  explicitly designed to layer onto a `base/` collection in the same
  profile. Before adding or renaming an agent/skill/rule in
  `collections/`, check it isn't reusing a name already used by another
  starter collection likely to be composed with it — run:
  ```bash
  grep -rn "^name:" collections/*/*/skills/*/SKILL.md | sort -t: -k3
  ```
  for skills (name comes from the frontmatter `name:` field — see
  `_parse_skill_file` in `backend/app/services/scanner.py`), or compare
  filenames under `agents/` (agent name is the file stem — see
  `_parse_agent_file`) and `##` headings in `AGENTS.md` (rule name is the
  heading text — see `_parse_agents_md`).
- `additional/auditor`'s `security-compliance-auditor` agent and
  `security-audit-checklist` skill are named the way they are
  specifically to avoid colliding with `base/software-engineer`'s
  `security-auditor` agent and `security-checklist` skill when the two
  collections are composed (a very natural pairing — `software-engineer`
  is the most commonly-chosen base). Likewise `additional/editor`'s
  `technical-writer` agent avoids colliding with
  `base/software-engineer`'s `docs-writer`, whose handoff chain and
  `memory-system` skill integration `editor`'s agent doesn't share. Follow
  this pattern — rename the `additional/` side, not the `base/` side,
  since base collections' internal pipelines (e.g. `orchestrator.md`'s
  hardcoded stage routing) are more expensive to keep consistent than an
  additional collection's own naming.

### 30. Moderator Role — Additive, Community-Scoped, Never Merged With `require_admin`

- **`User.role: Literal["user", "moderator", "admin"]` is additive
  alongside `is_admin`, not a replacement.** `is_admin` still gates every
  pre-existing `require_admin`/`authorize_access` bypass unchanged. The
  two are kept in sync one-directionally: `PATCH /auth/users/{id}/role`
  (admin-only) sets `is_admin = (role == "admin")` in the same
  transaction whenever `role` changes. Any other code path that creates or
  mutates a `User` with `is_admin=True` (registration/OIDC bootstrap-admin
  paths in `app/api/auth.py`) must set `role="admin"` alongside it, or
  that admin will fail `require_moderator_or_admin` despite being a real
  admin. See [ADR-0007](docs/adr/0007-additive-user-role-column.md).
- **`require_moderator_or_admin` (`backend/app/core/deps.py`) reads `role`
  only, never `is_admin`.** It gates every route under
  `/api/v1/moderation/*`, plus two Phase-4 additions under other URL
  prefixes that are the same community-content-review capability in
  substance — `GET /admin/freshness-queue` and
  `POST /collections/{id}/verify` (rule 37) — and nothing else. Never
  widen it to accept `is_admin` alone, never merge it with `require_admin`,
  and never use `authorize_access()`'s owner-bypass on a route it gates —
  a collection's own owner must never be able to approve or deny their own
  submission, including an owner who happens to also be a moderator or
  admin viewing the route through a different capability.
- Moderator scope is deliberately narrow: review/approve/deny submissions,
  edit collection metadata (`PATCH /moderation/{id}/meta`), delete
  comments. No user management, system settings, or adapter toggles.
  Widening it is a deliberate, reviewed decision, not a drive-by change.

### 31. Ratings and Comments Gate on `moderation_status`, Soft-Delete, Block Self-Rating

- **Rating and commenting both require `Collection.moderation_status ==
  "approved"`, not `published`/`visibility` alone.** Those two fields are
  only ever set together with `moderation_status="approved"` today (see
  rule 18), but a future change should still check `moderation_status`
  directly rather than assume that invariant holds.
- **Self-rating is blocked**: `PUT /collections/{id}/rating` 400s if
  `current_user.id == collection.owner_id`. There is no equivalent
  self-comment block — an owner can comment on their own collection.
- **`CollectionComment` and `CollectionRating` both use soft-delete
  (`deleted_at`), never `session.delete()`** — this extends rule 15 to
  both new tables. `CollectionRating`'s unique constraint on
  `(collection_id, user_id)` is **not** scoped to live rows, so
  `PUT /collections/{id}/rating` must look up an existing row regardless
  of `deleted_at` and revive it (clear `deleted_at`, overwrite `stars`)
  rather than insert a second row — a naive "only look at live rows, then
  INSERT if none found" upsert will 500 on the constraint the moment a
  user re-rates after deleting their rating. `Collection.avg_rating`/
  `rating_count` recomputation must filter `deleted_at == None`, or a
  withdrawn rating keeps counting toward the average.
- **Comment deletion authorization is comment-author OR collection-owner
  OR moderator/admin** — checked in the route handler
  (`backend/app/api/comments.py::delete_comment`), not a DB constraint.
  The frontend delete icon on a comment mirrors this exact rule so it
  doesn't render and then 403 on click.

### 32. Compile-Time Validation Warnings — Additive, Response-Only, Not Yet Blocking

- **`compile_profile()` (`backend/app/services/compiler.py`) returns a
  `warnings: list[ValidationIssue]` field alongside its pre-existing
  `{profile_id, profile_name, target, artifact_count, files}` shape**
  (`ValidationIssue = {level: "warning", code: str, message: str}`,
  `backend/app/models/profile.py`). This is response-only — nothing is
  persisted, there's no migration, and no new table (see
  [data-model.md](docs/data-model.md)). Both `POST /profiles/compile` and
  `POST /profiles/compile/zip` funnel through this one function (same
  choke point as rule 21's adapter-disabled check), so a new warning rule
  added here reaches both routes automatically.
- **The only rule implemented so far is `name_collision`** — the
  artifact-name-dedup step described in rule 29 now emits a warning
  whenever an override actually crosses a collection boundary, naming
  both collections and which one won. `code` is deliberately a generic
  string (not a closed enum) and the schema is deliberately generic
  (`code`/`message`, not name-collision-specific fields) — a planned
  follow-up (dangling `handoff_to` references once that field exists)
  reuses this exact same plumbing rather than inventing a second warnings
  mechanism.
- **Warnings never block compilation** — `level` is currently always
  `"warning"`, and every consumer treats them as advisory: the CLI's
  `myace pull` prints them (yellow) after the file table but still writes
  the files (outside `--dry-run`, where nothing is written either way),
  with a `--strict` flag to opt into a non-zero exit code rather than
  skipping the write/dry-run itself; the zip route appends a
  `_myace_warnings.txt` file inside the archive (a zip's HTTP response has
  no room for a second JSON payload) only when there's something to
  report; `TargetExporter.tsx` renders a dismissible amber (not red) panel
  above the file output. If a future `"error"` level is ever added, that's
  a deliberate, reviewed widening of the `Literal` — not an implicit one.
- **Don't hand-roll a second ad hoc warnings mechanism for a new
  compile-time check.** Add a new `code` and append to the same
  `warnings` list inside `compile_profile()`'s existing collection loop
  (or a clearly-marked follow-up pass over `all_artifacts` for
  whole-profile checks) instead.

### 33. CLI Sync Manifest Format, and the compile-status Endpoint's Cost Trade-off

- **`myace pull` writes `.myace/<target>.manifest.json`** next to the files
  it just wrote (`cli/myace_cli/sync.py`'s `write_manifest()`), shaped
  `{profile_id, profile_name, target, compiled_hash, pulled_at, files:
  {filename: sha256(content)}}`. `files` records a hash of what actually
  ended up on disk for each path — a file the user declined to overwrite
  keeps its *old* on-disk hash, not the new server content's hash, or the
  very next `check` would wrongly report it as in sync. Filenames rejected
  by `pull`'s path-traversal guard are excluded entirely (never written,
  not real paths). Re-running `pull` overwrites the manifest in place —
  it never appends or merges with a previous run. See
  [ADR-0009](docs/adr/0009-manifest-based-drift-detection.md) for why this
  is a local file rather than new server-side state.
- **`myace check`/`watch` diff two independent things per target**, both
  implemented in `check_target()` (`cli/myace_cli/sync.py`): `locally_modified`
  (recompute each manifest-tracked file's hash from disk right now,
  zero network calls) and `stale` (one `GET
  /profiles/{id}/compile-status?target=X` call, comparing its
  `compiled_hash` against the manifest's stored value). A target is
  `in_sync` only when both are clean and the network call succeeded.
- **`compile-status` is transfer-cheap, not compute-cheap — don't oversell
  it as free in code or docs.** `compute_compile_status()`
  (`backend/app/services/compiler.py`) still resolves every artifact and
  runs the adapter's `translate()` exactly like a full `/compile` call; it
  only skips shipping the resulting file *content* back over the wire.
  `myace watch`'s interval poll therefore still costs the server a full
  compile per tick, per watched target, for every user running `watch`.
  If that becomes a real load concern, the fix is a server-side cache of
  compiled output keyed by a hash of the profile's resolved inputs — not
  implemented yet, deliberately left as documented future work in
  ADR-0009 rather than solved speculatively.
- **`myace watch --auto-pull` must never overwrite a locally-modified
  file, full stop.** The check-then-maybe-pull decision is a pure function,
  `decide_watch_action()` — `locally_modified` always wins over `stale`
  regardless of `--auto-pull`, and is the thing to unit-test directly
  rather than the real `watchfiles` event loop (`run_watch_iteration()`
  is the one-network-call-per-target orchestration around it; both are
  exercised in `cli/tests/test_watch.py` without ever invoking
  `watchfiles.watch()` itself).
- **`myace check --report`/`myace watch --report` are the only things that
  ever write a `SyncStatus` row, and only when that flag is passed.**
  Nothing about `pull`, `check`, or `watch` reports to the server by
  default — see invariant 21 in
  [docs/invariants.md](docs/invariants.md) and rule 13's ownership rule:
  `POST /sync/report` always upserts under `current_user.id`, never a
  client-supplied user id.

### 34. Orchestration UX — `handoff_to` Is Advisory Metadata, Not Enforced Routing

- **`Artifact.handoff_to: list[str] | None` is a nullable JSON-text
  column, agent artifacts only** — same storage/conversion pattern as
  `tags`/`target_compatibility` (rule 11), but `NULL` ("not declared") is
  kept distinct from `[]` ("declared, terminal — never hands off")
  rather than defaulting to `"[]"` like those two fields do, since most
  agent rows never set this at all. See
  [ADR-0010](docs/adr/0010-structured-handoff-field.md) for why this is
  a plain name list on the existing table rather than a join table with
  real foreign keys.
- **References are by agent *name*, not artifact ID, and are never
  enforced at write time.** A `handoff_to` entry can legitimately point
  at an agent that only exists in a different collection than the one
  being scanned/imported/created — resolution only happens at compile
  time, once a specific profile's full, deduplicated artifact set is
  known. `compile_profile()`'s `_check_dangling_handoffs()` pass (added
  *after* the existing per-collection dedup loop, not inside it — see
  rule 32's `name_collision` for the pairwise/streaming check that
  correctly *is* loop-embedded, and why this one can't be) reuses the
  same `warnings: list[ValidationIssue]` plumbing to emit a
  `dangling_handoff` warning for anything that doesn't resolve. Like
  `name_collision`, this never blocks compilation.
- **Both scanners parse an optional `handoff_to:` frontmatter key on
  agent files** (`_parse_agent_file` in both
  `backend/app/services/scanner.py` and `cli/myace_cli/scanner.py`,
  kept in sync per rule 8) — a plain YAML list, not the `mode`/`model` →
  tag-string transformation those two fields get. The prose "##
  Handoff" section in every hand-written starter-pack agent
  (`collections/base/software-engineer/agents/*.md`) stays the
  human-readable version of the same routing fact; frontmatter is the
  machine-readable version. Nothing enforces the two stay consistent —
  keep them that way by hand when editing either.
- **`POST /{collection_id}/artifacts` (`backend/app/api/collections.py`)
  is the only single-artifact-create route** — every other artifact
  creation path (bulk-import, `/scan`-derived import) is bulk. It
  follows the same `authorize_access(write=True)` convention as the
  existing artifact PATCH/bulk-delete routes on this resource, and
  updates `Collection.artifact_count` like every other artifact-mutating
  route must (invariant 20). `ArtifactCreate` (`backend/app/models/
  artifact.py`) is this route's request body and deliberately has no
  `collection_id` field — the path parameter is the single source of
  truth, not a client-supplied body field (same reasoning as rule 13).
- **The Orchestration Gallery (`/build/orchestration`) and pipeline wizard
  (`/build/orchestration/build`, `frontend/src/pages/OrchestratorBuilder.tsx`)
  derive everything client-side from artifacts the API already
  exposes — no dedicated backend endpoint for either beyond the create
  route above.** A "recipe" is any agent with a `mode:primary` tag
  (still encoded as a tag string, e.g. `"mode:primary"` — not a first-
  class field) and a non-empty `handoff_to`. The gallery's diagram does
  a real BFS over each visited agent's own `handoff_to` (so back-edges
  like `verifier -> builder` render); the wizard's preview is a
  synthetic straight-line chain matching the sequence being composed,
  not the real graph — they intentionally show different things. Both
  reuse the shared rendering/layout primitives in
  `frontend/src/components/PipelineFlow.tsx` rather than duplicating
  the `@xyflow/react` setup — extend that file, don't fork it, if a
  third page ever needs to render a pipeline diagram.

### 35. Local Setup Audit — `expected_paths()` Is a Hand-Maintained Contract, Not a Shared Import

- **`BaseAdapter.expected_paths() -> list[str]`** (implemented by all 12
  backend adapters, `backend/app/adapters/*.py`) returns each target
  framework's conventional local file/directory names — directory entries
  end with `/` (e.g. `.claude/agents/`), file entries don't (e.g.
  `CLAUDE.md`). It must match what that adapter's `translate()` actually
  writes; if you change one, check the other. Nothing enforces this at
  runtime — no test cross-checks `expected_paths()` output against
  `translate()` output — so keep them in sync by hand when editing either.
- **The companion server's `POST /audit` route**
  (`cli/myace_cli/local_server.py`, same security model as `/scan` — see
  rule 24, unchanged) uses this to scan every detected target's
  conventional location under a given root, via `cli/myace_cli/audit.py`'s
  `audit_directory()`. It computes cross-target coverage gaps (an artifact
  name present under one target's paths but absent from another's),
  within-target duplicate names, and a documented, deliberately rough
  0-100 score — say so in any UI surfacing it (`SetupAudit.tsx` does),
  not just in code comments.
- **`cli/myace_cli/audit.py`'s `ADAPTER_EXPECTED_PATHS` is a hand-maintained
  mirror of the 12 backend adapters' `expected_paths()` values, not an
  import.** The CLI package doesn't depend on the backend package (same
  reasoning as the two parallel scanner implementations, rule 8) — if you
  add a 13th adapter or change an existing one's `expected_paths()`,
  update this dict too, or the audit will silently miss/misreport that
  target.
- **Two tiers of parsing fidelity inside `audit.py`'s `scan_target()`**,
  and don't blur them: directories named `agents/`/`skills`/`commands/`
  (Claude Code, OpenCode, Codex CLI) are handed to the *real*
  `scan_directory()` parsers (pointed at the parent directory, since
  that's what `scan_directory()` itself expects); every other directory
  convention (Cursor/Windsurf/Amazon Q/Cline/Continue/Copilot's flat
  rules-or-instructions folders) has no per-file parser here and falls
  back to "one artifact per `.md`/`.mdc` file, named by filename stem." If
  you add real per-file parsing for one of those frameworks, keep the
  fallback for whichever frameworks still lack it — don't remove the
  tiering assumption elsewhere in the module.

### 36. Public Demo Compile Endpoint — the Auth-Exception + Rate-Limiter Pattern

- **`POST /demo/compile` (`backend/app/api/demo.py`) is the only
  fully-public *data* route in this backend beyond the auth-entry list in
  rule 13** — see [ADR-0011](docs/adr/0011-public-demo-sandbox.md) for the
  full reasoning. If a future feature seems to need another public route,
  read that ADR first; it's a deliberate, narrowly-scoped exception, not
  a precedent that public routes are now fine in general.
- **The pattern to copy, if you ever add another one:** no
  `Depends(get_current_user)` *and* no DB session dependency at all (so
  there's structurally nothing to persist by accident — see invariant 22
  in `docs/invariants.md`), a capped/validated input size, a fixed small
  scope (3 adapters here, not all 12), and a per-route `slowapi`
  `@limiter.limit(...)` decorator. Don't reach for session-based/anonymous
  auth to gate a route like this — if there's genuinely nothing to own,
  there's nothing an auth check would protect.
- **`slowapi`'s `Limiter` + `RateLimitExceeded` exception handler are
  registered once, globally, on the FastAPI app** (`app/main.py`:
  `app.state.limiter` + `app.add_exception_handler(...)`). This is
  required plumbing for `@limiter.limit(...)` to raise 429s at all — it is
  **not** app-wide rate limiting. Only routes explicitly decorated with
  `@limiter.limit(...)` are throttled; as of this writing that's `POST
  /demo/compile` alone. Don't assume adding this registration protects any
  other route, and don't remove it thinking it's dead weight — every
  route that *does* carry the decorator depends on it.
- **The rate limiter's storage is in-memory and per-process** — in a
  multi-replica deployment the effective limit is `10 × replica_count`,
  not a hard global 10. Acceptable for a demo-abuse deterrent today
  (documented in ADR-0011's consequences); if MyACE grows a documented
  multi-replica production shape, this needs a shared backend (e.g.
  Redis), not a bigger in-memory number.

### 37. Collection Freshness Verification — Manual, Honest, and Not a Live Check

- **`Collection.last_verified_at`/`verified_by`** (nullable `Date`/FK to
  `users.id`) record that a moderator/admin manually looked at a community
  collection recently and confirmed it's still good. This is **not** an
  automated check against live tool documentation — every surface that
  shows it (API docstrings, `FreshnessBadge.tsx`'s tooltip copy) says so
  explicitly. Don't let a future change make this look more automated than
  it is (e.g. auto-setting it from a passing CI run) without a deliberate,
  reviewed decision to change what "verified" means. See
  [ADR-0012](docs/adr/0012-manual-collection-freshness-verification.md)
  for why manual, not automated, was the deliberate choice here.
- **`GET /admin/freshness-queue` and `POST /collections/{id}/verify`
  (`backend/app/api/freshness.py`, `backend/app/api/collections.py`) are
  both gated by `require_moderator_or_admin`, per rule 30's extended
  scope** — not `authorize_access`, and not a self-verification block the
  way moderation approval has a self-approval block (rule 18): verifying
  is additive/non-destructive to the collection in a way approving a
  submission isn't, so there's no equivalent risk in letting a
  moderator/admin who also owns a collection verify it themselves.
- **`freshness.py`'s `stale_collections_query()` is the single source of
  truth for "what counts as stale."** Both the queue route and
  `app/scripts/check_collection_freshness.py` (the weekly digest cron
  script, same "no in-process scheduler" shape as
  `send_download_digests.py` — see `docs/deployment.md`) call this one
  function. If you change the staleness definition, change it there once
  — don't let the route and the script hand-roll two copies of the same
  `WHERE` clause that can drift apart.
- **`settings.collection_freshness_threshold_days` (default 180, ~6
  months) is not exposed via any API endpoint today.** The frontend
  badge's own threshold (`frontend/src/components/FreshnessBadge.tsx`) is
  a hardcoded mirror of that default, not read live from the server — an
  admin-overridden threshold (there's currently no UI to override it
  anyway; it's env/settings-only) won't be reflected in the badge. Known,
  accepted gap for a "rough signal" feature; revisit if the threshold ever
  becomes admin-editable via System Settings.
- **A handful of `# type: ignore` comments in `freshness.py`/
  `check_collection_freshness.py`** cover a genuine mypy/SQLAlchemy stub
  gap specific to comparing a nullable `date`-typed column (`<`, wrapped
  in `or_()`) — mypy resolves `Collection.last_verified_at` as a plain
  `date | None` in that context rather than a SQLAlchemy `ColumnElement`,
  unlike the `datetime`-typed nullable columns elsewhere in this codebase
  (e.g. `Artifact.deleted_at == None`), which don't need one. Each ignore
  is scoped to one line with a comment explaining why; don't blanket-ignore
  the file, and don't be surprised if a `datetime` column doesn't need the
  same treatment.

### 38. Frontend Navigation Is Grouped by Task, With `lib/navigation.ts` as the Single Source of Truth

- **The sidebar (`frontend/src/components/Layout.tsx`) is grouped into
  task-based, collapsible sections, not a flat link list.** Groups:
  Dashboard (single link, not collapsible), **Collections** (My
  Collections, Community), **Build** (Profiles, Orchestration, Compile &
  Export), **My Machine** (Import, Setup Audit, Sync), and **Settings**
  (Account, Moderation†, System†). This exists because the flat 9-item
  list stopped mapping to how people actually think about the app as
  functionality grew (see `docs/plans/` for the platform-enhancements
  history) — grouping by task keeps the nav legible for a first-time
  visitor without hiding anything from a power user.
- **Every group has a "hub" page** — `CollectionsHub.tsx`/`BuildHub.tsx`/
  `MachineHub.tsx`/`SettingsHub.tsx`, all thin wrappers around the shared
  `SectionHub.tsx` component — reachable at `/collections`, `/build`,
  `/machine`, `/settings`. Clicking a group's *label* in the sidebar goes
  to its hub (a card grid explaining what each child page is for);
  clicking a *child* link goes straight to that page. `SettingsHub.tsx` is
  the one hub page that isn't a static import — it calls `useAuth()` and
  passes the live `user` into `getSettingsGroup(user)` itself, since its
  card set is role-gated the same way its sidebar children are.
- **Each group is collapsed by default and expands on click, chevron
  rotated to indicate state.** `Layout.tsx`'s `NavGroupSection` renders
  the group label as a `Link` to its hub and a *separate* chevron button
  next to it that only toggles expansion — clicking the label navigates,
  clicking the chevron does not. Effective open state is
  `openOverrides[group.id] ?? locationPathnameStartsWith(group.hubPath)`:
  with no manual toggle, whichever group contains the active route
  auto-expands (so deep-linking straight into a child page never hides the
  highlighted item) and every other group stays collapsed; a manual click
  overrides that default for that group until clicked again. Expanded
  children render in an indented, left-bordered block
  (`ml-[1.15rem] pl-3 border-l border-border`) below the header — that's
  the "slightly indented" sub-menu look; don't restyle children to look
  like top-level items.
- **`frontend/src/lib/navigation.ts` is the single source of truth for
  group/child labels, icons, descriptions, and paths** — both
  `Layout.tsx`'s sidebar and the four hub pages import the same
  `collectionsGroup`/`buildGroup`/`machineGroup` constants (and
  `getSettingsGroup(user)` for the role-gated one), so the sidebar and its
  hub card never drift out of sync the way the CLI/backend scanner pair
  (rule 8) or `ADAPTER_EXPECTED_PATHS` (rule 35) require manual syncing.
  Add a new page to an existing group by adding one entry to that group's
  `children` array in `navigation.ts` — don't hand-edit `Layout.tsx` or a
  hub page directly.
- **The Settings group's naming is deliberate: the *group* is "Settings",
  the *child* pointing at the personal-account page (`UserSettings.tsx`,
  API tokens/CLI setup/profile) is "Account".** Calling both of them
  "Settings" (the original shape) was confusing once Moderation and System
  joined the same group as siblings — "Settings" now means "this whole
  area," "Account" means "your own settings specifically." Don't rename
  the child back to "Settings" even though its component file is still
  called `UserSettings.tsx`.
- **Every page that moved under a group prefix keeps its old top-level
  path alive as a redirect** in `App.tsx` (`/profiles` → `/build/profiles`,
  `/orchestration` → `/build/orchestration`, `/orchestration/build` →
  `/build/orchestration/build`, `/compile` and `/export` → `/build/compile`,
  `/import` → `/machine/import`, `/setup-audit` → `/machine/audit`,
  `/sync` → `/machine/sync`, `/moderation` → `/settings/moderation`,
  `/admin/system` → `/settings/system`) — same pattern as the pre-existing
  `/export` → `/compile` redirect. `/profiles/:id` needs its own tiny
  `ProfileDetailRedirect` wrapper component (reads `useParams().id` and
  builds the target path) since `<Navigate to="...">` can't itself contain
  a route param placeholder — copy that pattern for any future param-bearing
  redirect. **`/collections` and `/settings` are the two exceptions**:
  `/collections` used to be My Collections directly and `/settings` used
  to be the account page directly, but both are now intentionally
  repurposed as their group's hub landing page (My Collections moved to
  `/collections/mine`, the account page moved to `/settings/account`)
  rather than redirected — that's a deliberate behavior change, not an
  oversight. `RequireModerator`/`RequireAdmin` still gate the real
  `/settings/moderation`/`/settings/system` routes exactly as they gated
  the old `/moderation`/`/admin/system` ones; the legacy paths are plain,
  ungated `Navigate` redirects because the gate at the destination already
  covers them.
- If you add a new top-level page, decide up front whether it belongs
  inside an existing group (add it to that group's `children` in
  `navigation.ts`) or genuinely needs a new group — don't add a new flat,
  ungrouped sidebar item.

### 39. `POST /auth/login` Must Return the Real User, Not a Hand-Built `UserRead`

- **`login_with_password()` (`backend/app/api/auth.py`) returns
  `UserRead.model_validate(user)`, not a manually-constructed
  `UserRead(...)`.** This route has no `response_model` (it also returns
  an `{"mfa_required": ...}` dict when MFA is enabled), so whatever it
  returns must already be shaped as public fields — but hand-listing
  fields is exactly what caused the bug this rule exists to prevent: an
  earlier version built `UserRead(id=..., email=..., ...)` by hand and
  simply forgot `role` (and `notify_on_download`/`notify_on_comment`),
  so every password login reported `role="user"` regardless of the
  account's actual role, even for a real moderator/admin. `is_admin` was
  listed explicitly and so wasn't affected, which is why this went
  unnoticed for admins but silently hid the Settings → Moderation nav
  item (rule 38) for moderators — until the next full page load, when
  `AuthContext`'s mount-time `GET /auth/me` (which correctly serializes
  `current_user` through `response_model=UserRead`) overwrote the stale
  session state. If you add a new field to `UserRead` or `User`, this is
  the one route where nothing forces you to update it — there's no
  `response_model` to catch a drifted-by-hand return value at request
  time the way FastAPI would everywhere else.
- **Never `return user` (the raw ORM row) here either.** `User` is a
  `SQLModel` table model — without a `response_model` to filter the
  output, FastAPI's `jsonable_encoder` would serialize every column,
  including `password_hash`, `totp_secret`, and `reset_token_hash`.
  `UserRead.model_validate(user)` is the one line that's both correct
  (reads every current field off the ORM object, nothing to drift) and
  safe (still only emits `UserRead`'s public fields).

### 40. Moderator Read Access to Collections Is Scoped by Lifecycle State, Not Just Role

- **`_visible_to_moderator()` (`backend/app/api/collections.py`) is what
  lets `GET /collections/{id}` (and the artifacts routes) work for a
  moderator/admin viewing someone else's non-public collection** — plain
  `authorize_access(is_public=collection.visibility=="public")` only ever
  passed for the owner, an admin (via its unconditional bypass), or a
  truly public collection, so a non-admin moderator could see a
  submission's row in `GET /moderation/queue` but got a 404 opening it to
  actually review its contents. The helper adds a read-only bypass for
  `role in ("moderator", "admin")`, but **only once
  `moderation_status != "draft"`** — a collection that's never been
  submitted stays exactly as private as before, matching the scope
  `update_collection_meta` (rule 30) already established. Don't widen this
  to cover writes (artifact edits, collection metadata) — those still go
  through `write=True` `authorize_access` calls untouched, or the
  dedicated moderator-only meta-edit endpoint.
- This is a read bypass on the shared `_get_collection_or_404` call sites
  in `collections.py` specifically, not a change to `authorize_access`
  itself (`app/core/authz.py`) — that helper is shared by profiles/sync/
  auth too, where a blanket moderator bypass would be wrong. If a future
  resource type needs the same "moderator can review, once it's actually
  in the review pipeline" shape, copy the pattern locally rather than
  teaching the shared helper about roles.

### 41. Inline Artifact Editing — Validate-on-Blur, No Backend Changes Needed

- **Editing an artifact's priority/version/target_compatibility/body on
  `CollectionDetail.tsx` (`/collections/{id}`) is entirely a frontend
  feature.** The backend already had everything it needed —
  `PATCH /collections/{id}/artifacts/{artifact_id}` (partial update,
  `exclude_unset=True`) and `POST /collections/{id}/artifacts` (single-
  artifact create, rule 34) were both already implemented and already
  called by the frontend (the enable/disable toggle uses the same PATCH
  route). Before adding a UI that edits or creates *any* resource, check
  whether the write endpoint already exists — it frequently does, since
  most resources on this backend get PATCH/POST routes even before a
  frontend surface calls them.
- **Editing only becomes available once a row is expanded** — the
  collapsed row header's compact `p{priority}`/`v{version}` badges stay
  read-only; the expanded panel's Priority/Version/Target/Body become
  click-to-edit. Each artifact row (`ArtifactRow` in `CollectionDetail.tsx`)
  owns its own `editingField`/draft-value/`fieldError` state — there's no
  shared "which field of which row is being edited" state in the parent,
  since only one field of one row can plausibly be mid-edit at a time and
  co-locating the state avoids threading a row-identifying key through
  every draft-value setter.
- **The edit lifecycle is the same for all four fields**: click → input
  (auto-focused, seeded from the current value) → **Escape** reverts with
  no API call → **blur** with an unchanged value exits with no API call
  (avoids needless PATCH traffic) → blur with a changed, valid value calls
  `collectionsApi.updateArtifact` (via `mutateAsync`, not the shared
  mutation object's `isError`/`isPending` — every row would otherwise
  flicker off each other's in-flight state) and exits edit mode on success
  → a validation or request failure shows a small inline `text-destructive`
  message under the field and **stays in edit mode**, so a failed save
  never silently discards what the user typed. `TargetChecklist.tsx`
  (`frontend/src/components/`, shared between this inline editor and the
  Add-rule form below) is the one field that isn't a plain blur-to-save
  input — it's a checkbox popover with an explicit "Done" button, since
  toggling several checkboxes needs to happen before committing.
- **Validation is client-side only, mirroring the Canonical IR schema
  (rule 5)**: priority is an integer 0–100; version must match
  `^\d+\.\d+\.\d+$` (plain `MAJOR.MINOR.PATCH`, no pre-release/build
  metadata); body must be non-empty after trimming. `target_compatibility`
  has no validation — despite looking like it constrains which adapters an
  artifact applies to, grepping `compiler.py` confirms it's never actually
  read anywhere in compilation; it's descriptive metadata copied straight
  onto `CanonicalArtifact`. The checklist (built from live `GET /adapters`
  names) still beats free text for avoiding typos, but don't assume this
  field gates anything at compile time — it doesn't, today.
- **No client-side ownership check gates any of this** — `CollectionDetail.tsx`
  has never had one (Edit/Delete/Share are unconditionally rendered too);
  authorization is enforced entirely server-side via
  `authorize_access(write=True)`, which 404s for a non-owner (including a
  moderator using rule 40's read-only bypass, which doesn't extend to
  writes). A failed PATCH/POST from a non-owner surfaces through the same
  inline-error path as any other failure — there's nothing MyACE-specific
  to add here, just don't add a `useAuth()`/`owner_id` check that the rest
  of this page doesn't have either.
- **"Add rule" (`frontend/src/pages/NewArtifactRule.tsx`,
  `/collections/{id}/artifacts/new`) only creates `artifact_type: "rule"`**
  — matching the button's literal label lets the form skip both a type
  picker and a `file_path` field. `file_path` is hardcoded to `"AGENTS.md"`,
  matching the convention every scanner-parsed rule already uses
  (`_parse_agents_md_content` in `backend/app/services/scanner.py` — every
  rule from an `AGENTS.md` file shares that same `file_path`, differentiated
  by `name`/`## section`, not by a unique path each). If a future "Add
  skill"/"Add agent" is added, it needs its own `file_path` convention
  (`skills/{slug}/SKILL.md`, `agents/{slug}.md`) since those aren't
  filename-shared the way rules are.
- **No special "re-sort after create" code exists, or is needed** —
  `CollectionDetail.tsx`'s `visibleArtifacts` is a `useMemo` that already
  re-derives and re-sorts from whatever the `['artifacts', id]` query
  currently holds; invalidating that query on create (same as every other
  artifact-mutating action on this page) is sufficient for the new rule to
  appear in the right sorted position once the page navigates back.
