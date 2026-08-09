# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

MyACE ("My Agentic Coding Environment") makes AI agent configurations (rules, skills, agent definitions, workflows, model configs) portable across frameworks (OpenCode, Claude Code, Cursor). It stores everything as a **Canonical Intermediate Representation (IR)** — Markdown with YAML frontmatter — and translates that IR into target-framework-specific files via adapters.

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

## Architecture

### Canonical IR is the single source of truth
Every artifact — a rule, skill, agent, workflow, or model_config — is Markdown with YAML frontmatter (`type`, `name`, `version`, `target_compatibility`, `priority`, `tags`, `description`), body is the markdown content. The DB (`app/models/artifact.py`) stores this denormalized (JSON-as-text columns for `tags`/`target_compatibility`); `CanonicalArtifact` is the in-memory Pydantic representation used for compilation, decoupled from the SQLModel table.

### Compilation pipeline (`app/services/compiler.py`)
A **Profile** references a base **Collection** plus additional collections and a disabled-artifact list. `compile_profile()`:
1. Resolves all referenced collections.
2. Pulls enabled artifacts from each (skipping anything in `disabled_artifact_ids`).
3. Deduplicates by artifact `name` — later collections in the list override earlier ones.
4. Sorts by `priority` descending.
5. Hands the list to a target adapter's `translate()`.

`POST /api/v1/profiles/compile` returns the `{filename: content}` map as JSON (what the CLI's `pull` consumes). `POST /api/v1/profiles/compile/zip` (`app/api/profiles.py`) wraps the same `compile_profile()` call and streams the result back as a zip for browser-only download — no CLI required. Its `Content-Disposition` filename is built via `github_export.py`'s `slugify()`, not the raw `profile.name`/`target` — profile names are attacker-controllable on profiles you don't own (public profiles), so an unsanitized filename would be a header-injection vector into another user's response.

### Adapters translate IR → framework files
`app/adapters/` (backend) and `cli/myace_cli/adapters/` (CLI) each implement `BaseAdapter`:
```python
class BaseAdapter(ABC):
    def adapter_name(self) -> str: ...
    def supported_targets(self) -> list[str]: ...
    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]: ...  # {filename: content}
```
Adapters are stateless. Three exist: `claude_code` (→ `CLAUDE.md`, `.claude/agents/*.md`, `.claude/workflows/*.md`), `opencode` (→ `.opencode/skills/*.json`, `.opencode/agents/*.json`, `AGENTS.md`), `cursor` (→ `.cursorrules`, `.cursor/rules/*.mdc`, `.cursor/workflows/*.mdc`). The CLI keeps its own adapter copies as a fallback for offline/no-server use.

### Scanner duality — keep in sync
`cli/myace_cli/scanner.py` and `backend/app/services/scanner.py` are parallel implementations of the same directory-scanning logic (used by `myace import` and `POST /api/v1/collections/scan` respectively). Both must recognize the same layout: `skills/<name>/SKILL.md`, `agents/*.md`, `commands/*.md`, `AGENTS.md` (`##` sections → rules), `opencode.json` (models + MCP servers → model_configs). When changing scanning behavior, update both.

The backend scanner additionally handles Docker path resolution (`_resolve_path` in `backend/app/services/scanner.py`) — rewriting `/root`, `/home`, `/Users` prefixes to the `/host-home` mount, and resolving broken symlinks through that mount, since the backend runs in a container but scans paths on the host.

**The web UI no longer calls the backend's local-scan path.** `POST /collections/scan` with `source_type=local` runs against whatever machine *the backend container* is on — on a real multi-tenant deployment that's the VPS, never a remote visitor's laptop, and the `/host-home` mount it needs only exists in `docker-compose.dev.yml` anyway. `ImportPage.tsx`'s "Local Machine" source now goes exclusively through the `myace serve` companion server (see below) instead; the backend route itself is left in place (harmless, dev/API-only) rather than deleted, since removing `source_type=local` from `ScanRequest` would be an unrelated breaking API change and some direct-API dev workflows may still use it against `/host-home`.

### Local companion server (`cli/myace_cli/local_server.py`)
`myace serve` runs a small FastAPI app on `127.0.0.1:8765` (lazy-imports `fastapi`/`uvicorn` — only `pip install "myace-cli[serve]"` needs them, not the base CLI) so the web UI can scan the user's *own* machine without the browser needing filesystem access. It reuses `cli/myace_cli/scanner.py`'s `scan_directory()` directly — no third parallel scanner implementation. Security model: refuses to start without existing `myace login` credentials; binds loopback-only; CORS reflects exactly the logged-in server's origin (never `*`); `POST /scan` additionally requires a custom `X-MyACE-Companion` header (forces a real preflight, blocks blind `no-cors` POSTs) and a server-side `Origin` check (not just a CORS response header) so a non-browser client can't skip the dance. Also implements Chrome's Private Network Access preflight (`Access-Control-Allow-Private-Network`) since a page on a public origin fetching a loopback address gets an extra preflight beyond normal CORS. `ImportPage.tsx` polls `GET /health` while "Local Machine" is selected (`refetchInterval`, so starting `myace serve` mid-session is picked up live) and shows a dynamic setup panel (`window.location.origin` + a link to Settings) when it's not reachable — see `LocalCompanionSetup` in `ImportPage.tsx`.

**Gotcha — don't add `from __future__ import annotations` to `local_server.py`.** Its FastAPI app, route handlers, and Pydantic model are all defined *inside* `build_app()` so the base CLI install never needs fastapi/uvicorn. PEP 563 (`from __future__ import annotations`) turns every annotation into a string that FastAPI resolves via `typing.get_type_hints()` against the function's module globals — which doesn't include names only bound in `build_app()`'s local scope, so `Request`/the request model silently fail to resolve and every route 422s as if the parameters don't exist. Keep annotations eagerly evaluated (i.e., no future-annotations import) in this file.

**Backend-only: Git source scanning.** `scan_git_repository()` in the same file shallow-clones a repo (via `GitPython`, depth=1) into a temp dir, then hands off to the same `scan_directory()` — so it recognizes the identical layout. `POST /api/v1/collections/scan` picks between local/git via `source_type` in `ScanRequest`. This is web-UI-only for now — the CLI's `import` command still only supports `--path`, not a git URL. Only public repos work without extra setup; private repos need a token embedded in the URL (`https://<token>@github.com/...`).

### GitHub PR export (`app/services/github_export.py`)
The inverse direction: `POST /api/v1/collections/{id}/export/github` takes a collection's *enabled* artifacts, converts them back into the scanner's source file-tree layout via `artifacts_to_files()` (mirrors the read-side convention so the exported repo is re-importable — `model_config` artifacts aren't single-file round-trippable and are skipped), then talks to the GitHub REST API directly (via `httpx`, no local git clone/push) to: get the base branch SHA → build blobs → one tree → one commit → create the branch ref → open a PR. The token is per-request only, never persisted or logged (see AGENTS.md security rules).

### API surface
All routes are prefixed `/api/v1/` (breaking changes get a new version prefix, additive changes stay in-version). Route modules live in `app/api/` and are registered in `app/main.py`. Every route except `/health` and the handful of auth entry points (`/auth/register`, `/auth/login`, `/auth/login/{provider}`, `/auth/callback/{provider}`, `/auth/providers`) requires `Depends(get_current_user)`.

### Authentication & Authorization
Two auth mechanisms feed one dependency, `get_current_user` (`app/core/deps.py`): a **session cookie** (`request.session["user_id"]`, set by `SessionMiddleware` in `main.py` after `/auth/login` or an OIDC/GitHub/Google callback — this is what the web UI uses) or a **Bearer API token** (`Authorization: Bearer <key>`, matched by `ApiToken.token_prefix` then bcrypt-verified — this is what the CLI uses). Both resolve to the same `User` row; routes don't need to know which path was used.

**Gotcha — session `user_id` must be parsed back into a `uuid.UUID` before querying.** The session cookie stores `str(user.id)` (session payloads are JSON, no native UUID type), so `_user_from_session` must do `uuid.UUID(raw_user_id)` before comparing against `User.id`. Comparing the raw string directly works against `asyncpg`/Postgres (which coerces loosely) but throws `AttributeError: 'str' object has no attribute 'hex'` under SQLite's `Uuid` bind processor — this only surfaced once the test suite actually exercised session-cookie-authenticated routes against real SQLite (see the `db_session` fixture note above).

Authorization is ownership-based, not role-based-per-resource: every `Collection`/`Profile` has an `owner_id`, plus a `visibility`/`is_public` flag. `app/core/authz.py` has the two primitives every protected route uses — `authorize_access(owner_id=..., current_user=..., is_public=..., write=...)` for single-resource routes (404s, not 403s, if denied — doesn't reveal that the resource exists) and `owner_or_public_clause(...)` for list endpoints (returns a WHERE clause, or `None` for admins — no filter). `User.is_admin` bypasses every check. `Artifact` has no `owner_id` of its own — routes load the parent `Collection` first and authorize against that.

First-ever registered user becomes admin automatically; `ADMIN_EMAILS` (config, comma-separated) promotes specific emails on register/OIDC-login going forward. There is no more "unauthenticated placeholder user" concept — `app/services/placeholder_user.py` (which used to resolve the nil UUID to one shared `local@myace.local` account) was removed once real auth landed; every create route derives ownership from `current_user.id`.

**Gotcha — decode JSON-as-text columns before returning `ArtifactRead`.** `Artifact.tags`/`target_compatibility` are stored as JSON-encoded `Text` columns, but `ArtifactRead` declares them as `list[str]`. Returning a raw SQLModel `Artifact` row as a FastAPI response silently 500s (`ResponseValidationError`) as soon as a row has actual data. `app/api/collections.py` has a `_artifact_to_read()` helper that does the `json.loads()` — always route artifact reads through it (or through `compiler.py`'s `_db_to_canonical`, which does the same) rather than returning DB rows directly.

Artifact-level bulk operations (`bulk-delete`, `bulk-export`) live alongside the single-artifact CRUD routes in `app/api/collections.py`. `bulk-export` copies rows (new IDs, original collection untouched) into an existing or freshly-created collection; it does not move/delete from the source.

**Gotcha — `response_model` silently strips keys not on the schema.** `create_token` used to return `{**db_token.model_dump(), "token": api_key}` under `response_model=ApiTokenRead`, which has no `token` field — FastAPI serializes the response through the schema, so the raw API key was dropped from every response before it ever reached a client (the one-time "copy your token now" flow was broken from the app's inception). Fixed by adding `ApiTokenCreateResponse(ApiTokenRead)` with the extra field and using that as the route's `response_model`. If a route needs to return more than its "read" schema, give it its own response model — don't rely on an untyped dict matching a narrower `response_model` at runtime.

### Frontend
React Router SPA (`src/App.tsx`) with pages under `src/pages/` (Login, Dashboard, CollectionsManager, CollectionDetail, ImportPage, ProfileComposer, `TargetExporter` mounted at `/compile`, Settings) and a single `Layout` shell. (`/export` 301-redirects to `/compile` for old links; the component file is still named `TargetExporter.tsx`.) `src/lib/api.ts` is the API client (every call sets `credentials: 'same-origin'` so the session cookie flows — any hand-rolled `fetch()` outside `api.ts` must set this too, see `ImportPage.tsx`'s scan/import calls); `src/types/index.ts` mirrors the backend's Canonical IR shape. `src/contexts/ThemeContext.tsx` handles light/dark/system theme; `src/contexts/AuthContext.tsx` (same provider/hook shape) holds `user`/`isLoading` and the `login`/`register`/`logout`/`loginWithProvider` actions, calling `GET /auth/me` on mount to rehydrate an existing session.

`/login` is the only public route — everything else is wrapped in a `RequireAuth` component (`App.tsx`) that redirects to `/login` while `isLoading`/unauthenticated. `Login.tsx` itself redirects *away* from `/login` via a `useEffect` the moment `user` becomes non-null (covers both a fresh login and an already-valid session) — OIDC/GitHub/Google buttons only render if `GET /auth/providers` reports that provider configured. `Layout.tsx`'s sidebar footer shows the real signed-in user (name + Admin/User role badge) and a logout button, replacing what used to be a hardcoded "API Connected" indicator.

**Two different things are called "export" — don't conflate them.** `TargetExporter.tsx` (`/compile`) compiles a **Profile** into a target framework's files (opencode/claude-code/cursor), for copy-paste, a zip download (`POST /profiles/compile/zip`, browser-only — no CLI needed), or CLI pull. `CollectionDetail.tsx`'s "Export to GitHub" button pushes a **Collection**'s canonical artifacts to a real GitHub branch + PR. They share no code path.

**`ImportPage.tsx`** has a Local Machine / GitHub Repository source toggle sharing one scan → select → import flow. Git scans hit `POST /collections/scan`; Local Machine scans go to the `myace serve` companion server on `127.0.0.1:8765` instead (see "Local companion server" above) — both feed the same artifact-selection UI and both imports land via the same `POST /collections/import` over the session cookie. `CollectionsManager.tsx`'s "Import Collection" button is just a `Link` to this page now — there used to be a separate quick-create form here that only wrote `{name, git_url}` to the DB without ever fetching anything, silently producing permanently-empty collections. Don't reintroduce a second "create collection" entry point without wiring it through the real scan/import flow.

**`Settings.tsx`**'s "CLI Setup" block is generated, not static copy — `installCommand`/`loginCommand`/`pullCommand` interpolate `window.location.origin` and the just-created token (`newToken`) the same way `TargetExporter.tsx` builds its `myace pull` string. Don't hardcode a server URL or placeholder token back into this block; a wrong one (e.g. `pip install myace-cli`, which was never published to PyPI) silently breaks first-run onboarding.

**`CollectionDetail.tsx`** is the richest page: inline collection editing (name/description/type, toggled via an Edit/Save/Cancel header state) plus per-artifact-row selection with a "With selected..." menu for bulk export (to an existing or new collection, via a modal with existing/new mode toggle) and bulk delete (behind a confirmation modal — this codebase has no other confirm-before-destructive-action pattern, so it's the template to copy), plus the header-level "Export to GitHub" button described above. It scopes its React Query keys to `['collection', id]` / `['artifacts', id, typeFilter]`, unlike the shared `['collections']`/`['profiles']` keys used elsewhere.

**Gotcha — React Query key collisions.** Multiple pages query the same resource with *different filters* (e.g. `Dashboard.tsx` fetches `collections?visibility=public` while `CollectionsManager.tsx` fetches the unfiltered list). If two differently-filtered queries share a cache key, whichever resolves first silently poisons the other view during SPA navigation (no full reload). Always fold the filter into the query key, e.g. `['collections', { visibility: 'public' }]`.

## Conventions (from AGENTS.md)

- **Typing is strict everywhere.** Backend: full type annotations, `SQLModel` for DB entities, Pydantic v2 for API schemas, no bare `Any`/`dict`, `X | None` (not `Optional[X]`) — enforced by ruff's `UP` rules. Frontend: annotate all params/returns, prefer `interface` over `type` for object shapes.
- **Migrations**: every schema change needs an Alembic migration with a working `downgrade()`. Never edit a committed migration — add a new one. Name descriptively (`add_profile_visibility_column`).
- **All DB IDs are UUIDs**, never auto-increment integers.
- Branch naming: `feat/`, `fix/`, `chore/` + description. Conventional commits (`feat:`, `fix:`, `chore:`, `docs:`).
- Never log tokens, secrets, or PII.
- **Keep both human docs (`README.md`, `docs/`) and agentic docs (this file, `AGENTS.md`) up to date in the same PR as the code they describe** — see `AGENTS.md` rule 14. A change isn't done until its documentation reflects it.
