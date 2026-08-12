# MyACE — AI Agent Maintenance Guidelines

This document defines the rules and conventions for AI coding agents (Claude Code, OpenCode, Codex, etc.) maintaining the MyACE codebase.

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

### 18. Publish Uses Existing GitHub Export

- **`POST /{collection_id}/publish` reuses `artifacts_to_files()` and
  `export_collection_to_github()` from `github_export.py`.** It prefixes
  every file path with `collections/{type}/{slug}/` and adds a `README.md`.
  The target repo is configured via `settings.community_repo` (default
  `nemmer/MyACE`). The user's `github_token` is passed through, used once,
  and never persisted — same contract as the existing GitHub export endpoint.
