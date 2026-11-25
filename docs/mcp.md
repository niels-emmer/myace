# The MyACE MCP server

MyACE exposes its **public packs** to any MCP-capable coding agent. An agent
can browse the library, read an item's full text, and compile a pack into files
for a chosen framework — with no account, no CLI and no server-side setup.

It is **read-only by construction**. There is no tool that can create, change,
publish or install anything, and the container holds no database credentials.
Installing the files is something the agent proposes and the human approves.

- **Endpoint:** `https://<your-myace-host>/mcp` (Streamable HTTP)
- **Contents:** active, published, moderation-approved packs only — exactly
  what an anonymous visitor sees on `/packs`
- **Not included:** setups, private or draft packs, ratings, comments, writes
- **Implementation:** [`mcp/`](../mcp) — one container, no database
- **Decision record:** [ADR-0018](adr/0018-public-read-only-mcp-server.md)

## Connecting a client

The transport is Streamable HTTP, so the connection is a URL. Clients differ
only in where the config lives.

**Claude Code** — one command:

```bash
claude mcp add --transport http myace https://myace.example.com/mcp
```

Add `--scope user` to make it available in every project (the default is
project-local). To commit it with a repo instead, put `.mcp.json` at the
project root — Claude Code picks it up automatically, and everyone who checks
out the repo gets the server with no setup:

```json
{
  "mcpServers": {
    "myace": { "type": "http", "url": "https://myace.example.com/mcp" }
  }
}
```

**Cursor and other clients** read an equivalent `mcpServers` block in their own
config file. Copy the `url` form above; `type` is Claude Code's key, so drop it
if a client rejects it.

**Desktop clients** (including Claude Desktop) add remote servers through their
own UI — Settings → Connectors → *Add custom connector* — rather than the
`mcpServers` block, which historically accepted only local (stdio) servers.

Stateless and JSON-responding: no session id, no sticky routing, nothing to
warm up.

## Tools

| Tool | Arguments | Returns |
|---|---|---|
| `search_packs` | `query?`, `category?`, `pack_type?` (`base`\|`additional`), `sort?` (`downloads`\|`rating`\|`alpha`), `limit?` (1–100), `offset?` | `{total, offset, limit, packs: [...]}` — metadata only |
| `get_pack` | `pack_id` | `{pack, items, item_count, hint}` — metadata plus the item index, no bodies |
| `get_item` | `pack_id`, `item_name` | `{pack_id, item, body}` — one item's full text |
| `list_targets` | — | `{targets: ["claude-code", "cursor", …]}` — live and enabled only |
| `download_pack` | `pack_id`, `target`, `with_packs?` | `{files, compiled_hash, warnings, install_url, zip_url, …}` |

Three deliberate shapes:

- **`get_pack` omits bodies.** A 17-item pack would flood the agent's context;
  the agent fetches only the items it needs.
- **`download_pack` returns a file map, not a zip.** The agent writes files
  directly — no unzip, no binary handling, no base64 in context. The zip is a
  resource (below) for clients that want an artifact.
- **`download_pack` never writes.** It returns files plus an instruction to
  show the list and confirm with the user before overwriting anything.

`download_count` on a pack is displayed but never bumped by any of this:
counters only move through the explicit `POST /collections/{id}/use`.

## Resources

| URI | Content |
|---|---|
| `myace://packs` | The catalogue (first page, 50 packs) |
| `myace://packs/{pack_id}` | One pack: metadata plus item index |
| `myace://packs/{pack_id}/items/{item_name}` | One item's body as Markdown |
| `myace://packs/{pack_id}/files/{target}` | The compiled pack as `application/zip` |

## Worked examples

**"Find me a pack for code review."** `search_packs(query="review")` → names,
ratings, item counts. The agent asks which one to open.

**"What's in this pack?"** `get_pack(id)` → the item index; `get_item(id,
"orchestrator")` → that agent's full definition. This is also the review path:
an agent can critique a pack it can actually read.

**"Install it for Cursor."** `list_targets()` → confirm `cursor` exists →
`download_pack(id, "cursor")` → the agent lists the files, asks, then writes.

**"I want the archive."**
`myace://packs/{id}/files/claude-code`, or the plain URL that
`download_pack` returns as `zip_url`, which works with `curl`.

## Operational notes

The server is **opt-in**. It runs only when the stack is started with the `mcp`
compose profile:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile mcp up -d
```

Without it, `https://<host>/mcp` returns 502 and the rest of the site is
unaffected — the frontend's `location /mcp` proxies to a container that is not
there. For the same reason the signed-out landing page probes
`GET /mcp/health` (an exact-match nginx location that maps to this container's
own `/health`) and only advertises the endpoint when it answers, so a stack
without the profile never shows a dead URL. That probe is silent by design:
its access line is off, and it is proxied through a loopback-only helper server
whose error log is discarded, because nginx attributes the expected resolver
failure of a variable `proxy_pass` to the server rather than the location.
An MCP-less deployment therefore collects nothing per visitor.

Two settings matter in production:

- `MCP_ALLOWED_HOSTS` must include the public hostname (e.g.
  `myace.macjuu.com`), or the container's DNS-rebinding protection answers
  **421** to every request. It fails closed on purpose.
- `MCP_SITE_URL` (usually `${FRONTEND_BASE_URL}`) does two jobs: it makes the
  human-openable `url`/`zip_url`/`install_url` fields point at the public site
  rather than an internal Docker hostname, **and** it supplies the `Host`
  header for backend calls. The backend runs `TrustedHostMiddleware` with
  `TRUSTED_HOSTS` set to your public domain, so a call whose `Host` is
  `backend:8000` is rejected with `400 Invalid host header` — every tool would
  fail. Leave it unset and the container logs a startup warning.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `421 Misdirected Request` | `Host` not in `MCP_ALLOWED_HOSTS` |
| `502` on `/mcp` | The `mcp` compose profile is not running |
| Tool returns "No such pack" | Not published, not approved, or inactive — check `/packs/:id` as a signed-out visitor |
| `list_targets` lacks a framework | An administrator disabled that adapter |
| Download is 400 "disabled by an administrator" | Same thing, from the compile route |
| Download returns the target list instead of files | The `target` is unrecognised (typo, stale link, or an alias like `claude`); use an id from `list_targets` |
| `"Rate limited by MyACE"` | More than 120 requests in a minute from one caller IP. The backend's storefront limit is per client IP, and the MCP forwards the caller's address, so one busy agent does not consume anyone else's budget — but a single agent looping will hit its own ceiling. Retry after a minute. |
| `400 Invalid host header` | `MCP_SITE_URL` is unset, so backend calls present the internal `backend:8000` host and `TRUSTED_HOSTS` rejects them. Set `MCP_SITE_URL` (usually `${FRONTEND_BASE_URL}`) and restart the container. |
| Very large pack | `format=md`/`json` capped at 2 MiB; fetch the zip resource |

## For maintainers

`mcp/server.py` is the whole surface — five tools, four resources, one health
route. It must stay a **thin wrapper**: no compiler logic, no database, no
writes. A tool that needs data the backend does not expose needs a backend
route first.

```bash
cd mcp
pip install -r requirements.txt -r requirements-dev.txt
pytest          # stubbed backend; no Docker, no network, no database
```
