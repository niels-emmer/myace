# MyACE — AI Agent Maintenance Guidelines

This document defines the rules and conventions for AI coding agents (Claude Code, OpenCode, Codex, etc.) maintaining the MyACE codebase.

## Repository Architecture Rules

### 1. Strict Typing Standards

**Backend (Python):**
- All function signatures MUST include type annotations.
- Use `SQLModel` models for all database entities.
- Use `Pydantic v2` for all API request/response schemas.
- Never use `Any` or `dict` without a concrete type parameter.
- Use `Optional[X]` instead of `X | None` for SQLModel fields.

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
- The bulk import endpoint auto-creates users when the nil UUID is passed as `owner_id`.
