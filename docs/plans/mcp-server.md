# Public MCP server — implementation record

Status: **Implemented** (this branch). Rationale: [ADR-0018](../adr/0018-public-read-only-mcp-server.md).
Usage: [docs/mcp.md](../mcp.md). Related prior design:
[agent-install-url.md](agent-install-url.md), whose Phase 3 this is.

## Goal

Let any MCP-capable coding agent browse public packs, read their items, and
fetch a pack compiled for a chosen framework — anonymously, read-only, packs
only. The human gate is structural: the server cannot write, so installing is
something an agent proposes and a human approves.

## Accepted decisions

| Decision | Choice |
|---|---|
| Where it runs | A separate small container (`mcp/`), not mounted in the FastAPI app |
| Compilation | The existing compiler, via a new `compile_pack()` seam — never duplicated |
| Transport | Streamable HTTP only, at `/mcp`, same hostname as the site |
| Session model | Stateless, JSON responses (no session store, no SSE chunking) |
| Auth | None. Public, approved packs only |
| Tools | `search_packs`, `get_pack`, `get_item`, `list_targets`, `download_pack` |
| Delivery | File map in the tool result; zip as an `application/zip` resource; both URLs also returned |
| Write path | None — no `install_pack`, no import, no counters |
| Rollout | Opt-in compose profile `mcp`; homeserver deployment enables it explicitly |

## What shipped

**Backend**

- `compiler.py`: shared `_compile_collections()`; `compile_profile()` is now a
  thin wrapper; `compile_pack()` passes `can_use_frozen=False` and
  `requesting_user=None` (safe only because the route proves visibility first).
- `GET /api/v1/collections/community/{id}/install.md` — `target` (plain `str`),
  `format=md|json|zip`, repeatable `with=`. Four `target` outcomes: omitted →
  guidance document; unrecognised → guidance + note; registered-but-disabled →
  400; otherwise compiled. ETag/304, 300s cache, `X-Robots-Tag: noindex`,
  2 MiB cap → 413. Never increments `download_count`.
- `GET /api/v1/frameworks` — primary adapter names minus admin-disabled ones.
- `GET /collections/community` gained an optional `q` (name/description,
  case-insensitive) so `search_packs` can search server-side.
- `pack_install_max_bytes`; `get_disabled_adapter_names()` moved into
  `services/effective_settings.py` so the adapter routes and both new reads
  share one source.

**MCP container**

- `mcp/server.py`, `mcp/backend.py`, Dockerfile, pinned `requirements.txt`,
  22 tests against a stubbed backend (no Docker, no network, no database).
- DNS-rebinding protection **on**, allow-listed from `MCP_ALLOWED_HOSTS` —
  the SDK's localhost default would 421 every public request.

**Wiring**

- `frontend/nginx.conf`: `location /mcp` (needs no nginx-proxy-manager change,
  since that host forwards every path to the frontend).
- `docker-compose.yml`: `mcp` service under `profiles: ["mcp"]`.
- CI: `MCP (pytest)` job plus an image build step.

## Deviations from the reviewed draft

Four, all deliberate:

1. **`FastMCP` → `MCPServer`.** `mcp` 2.x renamed it
   (`mcp.server.mcpserver.MCPServer`); pinning `<2` to keep the old name would
   trade a real dependency for a stale one.
2. **No MCP-side rate limiter or response cap.** Every tool call hits a backend
   route that already has `storefront_rate_limit` and the 2 MiB cap. A second
   knob with no distinct effect is configuration debt, not safety.
3. **The zip resource is `…/files/{target}`, not `…/files/{target}.zip`.**
   A literal suffix after a URI-template variable is unnecessary risk in the
   template matcher; the MIME type already says it is a zip.
4. **`stateless_http=True` + `json_response=True`.** No session store and no
   SSE framing to get wrong behind nginx, and every tool is request/response.

## Follow-ups (not in this change)

- stdio shim for clients without remote MCP support.
- `myace install <url>` CLI path (agent-install-url Phase 2.5).
- Optional Bearer auth for a user's own non-public packs — a separate decision.
- Pack-scoped `compile-status` so an agent-written manifest can report `stale`.
