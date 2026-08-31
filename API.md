# MyACE API

The MyACE backend is a FastAPI service. It serves a machine-readable
**OpenAPI 3.1 spec at `/openapi.json`** — that is the canonical,
always-current description of every endpoint, parameter, and schema, and it
is generated from the running code (FastAPI does this for free; the spec is
served even in production, where the Swagger UI is disabled).

This document is the orientation layer on top of that spec: base URL,
authentication, conventions, and working examples. If this file and the spec
disagree, trust the spec. If you change the API, verify against the spec and
update this file in the same change.

## Base URL

| Environment | Base URL |
|---|---|
| Local dev — backend directly | `http://localhost:8000` |
| Local dev — via nginx | `http://localhost:80` |
| Hosted instance | `https://myace.macjuu.com` |

All routes are prefixed `/api/v1/` (the one exception is `GET /health`).
Breaking changes move to `/api/v2/`; backward-compatible additions stay
within v1.

## Spec endpoints

| Path | Availability | What it is |
|---|---|---|
| `/openapi.json` | Always | The full OpenAPI spec — source of truth for endpoints and schemas |
| `/docs` (Swagger UI) | Dev only (`DEBUG=true`) | Interactive API explorer |
| `/redoc` | Dev only (`DEBUG=true`) | ReDoc rendering |

## Authentication

Two mechanisms feed one `get_current_user` dependency. Every route except
`/health`, the auth entry points (`/api/v1/auth/register`, `/login`,
`/login/{provider}`, `/callback/{provider}`, `/providers`), and
`POST /api/v1/demo/compile` requires one of them:

1. **Session cookie** (`myace_session`) — set by `POST /api/v1/auth/login`
   (or the OIDC/GitHub/Google callback). Used by the web UI.
2. **Bearer API token** — `Authorization: Bearer <token>` header. Used by
   the CLI (`myace login --server <url> --token <token>`).

The OpenAPI spec does not declare these as security schemes (auth is enforced
via a custom dependency, not an `HTTPBearer` security scheme), so this section
is the authoritative auth reference — an agent reading only `/openapi.json`
will not see how to authenticate.

## Route groups

| Prefix | Covers |
|---|---|
| `GET /health` | Liveness check |
| `/api/v1/auth` | Register, login (password + OIDC/GitHub/Google), MFA/TOTP, password reset, API tokens, user management (admin) |
| `/api/v1/collections` | Collections CRUD, artifacts, scan/import, community listing, publish/unpublish, ratings, comments, GitHub export, freshness verify |
| `/api/v1/moderation` | Moderation queue, approve/deny, meta-edit (moderator/admin only) |
| `/api/v1/profiles` | Profiles CRUD, compile, compile/zip, compile-status |
| `/api/v1/adapters` | Adapter registry listing |
| `/api/v1/admin` | System settings, adapter enable/disable, freshness queue |
| `/api/v1/doc-cache` | Documentation cache entries |
| `/api/v1/sync` | Sync status reporting (CLI `--report`) |
| `/api/v1/demo` | Public demo compile (no auth, rate-limited) |

## Examples

All examples assume the dev backend at `http://localhost:8000`.

### Health

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### Register

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "hunter2", "display_name": "You"}'
```

### Login (sets the session cookie)

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "hunter2"}' \
  -c cookies.txt
```

### Create an API token (session-authenticated; the raw token is shown once)

```bash
curl -X POST http://localhost:8000/api/v1/auth/tokens \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"name": "my-cli"}'
# {..., "token": "myace_..."}   <- save this; it is never returned again
```

### List your collections (Bearer auth)

```bash
curl http://localhost:8000/api/v1/collections \
  -H "Authorization: Bearer $MYACE_TOKEN"
```

### Compile a profile to a target framework

```bash
curl -X POST http://localhost:8000/api/v1/profiles/compile \
  -H "Authorization: Bearer $MYACE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"profile_id": "<uuid>", "target": "opencode"}'
# {profile_id, profile_name, target, artifact_count,
#  files: {filename: content}, warnings, compiled_hash}
```

Valid `target` values (from the spec's `Literal`): `claude-code`,
`opencode`, `cursor`, `codex-cli`, `copilot-cli`, `cline`, `windsurf`,
`aider`, `continue`, `goose`, `amazon-q`, `pi-dev`.

### Public demo compile (no auth, rate-limited)

```bash
curl -X POST http://localhost:8000/api/v1/demo/compile \
  -H "Content-Type: application/json" \
  -d '{"markdown": "## my-rule\n\nBody text"}'
# {artifact_count, targets: {framework: {filename: content}}}
```

## Notes

- **Rate limiting**: only `POST /api/v1/demo/compile` is rate-limited
  (per-IP, in-memory, per-process).
- **Body size cap**: `POST /api/v1/demo/compile` is capped at 20 KB.
- **Errors**: non-2xx responses use the shape `{"detail": ...}`.
- **IDs**: all resource IDs are UUIDs.
- **Soft-delete**: DELETE endpoints soft-delete; deleted rows are filtered
  out of list/get responses.