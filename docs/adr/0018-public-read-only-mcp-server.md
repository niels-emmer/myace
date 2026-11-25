# ADR-0018: A public, read-only MCP server for packs

**Status:** Accepted

## Context

MyACE already serves public, approved packs anonymously: three storefront reads
(`GET /collections/community`, `/community/{id}`, `/community/{id}/artifacts`)
behind one visibility predicate, per ADR-0014. That made the *catalogue*
readable by anyone with `curl`, but not *usable* by a coding agent: an agent had
no vocabulary for "find a pack, read an item, compile it for my framework".

Two gaps stood in the way.

1. **Nothing could compile a pack.** Every compile path —
   `/profiles/compile`, `/profiles/compile/zip`, `myace pull` — starts from a
   saved `Profile` row and requires a session or Bearer token.
   `compile_profile()` resolves collections through
   `profile.base_collection_id`, so a pack on its own had no way to become
   files.
2. **No agent-facing surface.** `docs/plans/agent-install-url.md` designed a
   Markdown install URL for agents that can `WebFetch`; MCP is the typed
   equivalent, and that plan already scoped an MCP server as its Phase 3.

The Model Context Protocol is now what agent frameworks speak to call tools, so
an MCP endpoint is the difference between "a pack you can download" and "a pack
your agent can browse, evaluate and install on request".

## Decision

Ship a **separate, stateless, anonymous, read-only MCP container** served at
`/mcp` on the site's existing hostname, exposing five tools (`search_packs`,
`get_pack`, `get_item`, `list_targets`, `download_pack`) and four resource
templates over public, approved packs — plus the one backend seam it needs: a
pack-scoped compile (`compile_pack()` over the shared `_compile_collections()`)
surfaced as `GET /collections/community/{id}/install.md`.

It has **no write capability of any kind**: no install tool, no database, no
credentials, no import/use counter. The frontend proxies `/mcp` to it; it is
opt-in via the `mcp` compose profile.

## Alternatives considered

- **Mount the MCP app inside the existing FastAPI process.** ~10 lines, but it
  puts an unauthenticated, long-lived streaming endpoint in the same process
  that serves login, MFA, admin settings and moderation, and it makes MCP
  protocol churn force a rebuild of the image that serves auth. A separate
  container costs one internal HTTP hop and buys a real blast-radius boundary.
- **stdio transport** (`uvx myace-mcp`). Works in more clients today, but it
  re-introduces a local install step and hides the content inside the user's own
  machine — the opposite of the accessibility goal. Streamable HTTP only;
  a stdio shim proxying to it is a later client-side convenience.
- **Compile inside the MCP container.** Would duplicate `compile_profile()`'s
  dedup, snapshot and warning logic plus 12 adapters, and guarantee drift. The
  container calls the backend instead.
- **Keep `install.md` as the only surface.** It stays (the MCP even returns its
  URL), but a document is not a tool: it cannot be discovered, listed or
  validated by the agent runtime.
- **An `install_pack` tool.** Rejected deliberately. Installing is a local
  write; a public anonymous endpoint must not be able to trigger one, and the
  design goal was that a human applies what an agent fetched. The read-only
  boundary *is* the human gate.
- **Base64 zip in a tool result.** A pack is hundreds of KB of Markdown; base64
  in a tool result puts all of it into the agent's context as opaque text. The
  tool returns a file map; the zip is a `application/zip` resource.
- **Authenticated MCP with API tokens.** Nothing in scope is non-public, so a
  credential would add a revocation/logging story and protect nothing. Own-draft
  access is a later, separate decision.

## Consequences

**Easier:** any MCP-capable agent can discover, inspect, cite and install a pack
with no account, CLI or server-side configuration. Pack quality review becomes
a first-class use: point an agent at a pack and ask whether it still makes
sense.

**Harder / given up:**

- **ADR-0014's public-read family grows** from five routes to seven
  (`GET /frameworks`, `GET /collections/community/{id}/install.md`). The
  invariant that keeps it safe is structural, not procedural: nothing in that
  family writes.
- **A second deployment artifact** (the `mcp` profile) and a second set of
  pinned dependencies. Isolated on purpose so a protocol bump never touches the
  auth-serving image.
- **No popularity signal.** `download_count` deliberately does not move on any
  read (invariant 25), so MCP installs are invisible in the counter.
- **Anonymous, unaccountable load.** Limits are per-IP and in-memory
  (`storefront_rate_limit`, per-process), so the real ceiling is per-replica.
  The MCP adds no limiter of its own — every tool call goes through a backend
  route that already has one — but it **forwards the inbound caller's IP** as
  `X-Forwarded-For` on those calls. Without that, all MCP traffic would arrive
  from the container's single address and share one bucket, letting one busy
  agent throttle every other client. The forwarding is trustworthy because of
  the hop chain (`--forwarded-allow-ips` private ranges on both servers), not
  because the header is unspoofable in general.
- **No CORS.** A browser-based MCP client would need it; this is not enabled.
  Server-to-server and desktop agents are the target, and a wildcard CORS header
  must never be added as a shortcut.
- **Prompt injection is inherent.** Pack bodies are publisher-authored
  instructions — that is what a pack is. Mitigation is presentation, not
  enforcement: bodies are returned inside `PACK CONTENT` markers, tool
  descriptions say they are data rather than server instructions, and the human
  decides.
