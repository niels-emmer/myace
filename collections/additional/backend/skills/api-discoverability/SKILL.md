---
name: API Discoverability for Agents
description: Making self-hosted services agent-discoverable — bake in a machine-readable API description (OpenAPI spec or a minimal API.md) when building, and discover-first (spec paths, repo search) before probing when integrating.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [api, discoverability, agents, openapi]
---
## Purpose

Agents integrate with services by reading a machine-readable API description instead of crawling a web UI or reverse-engineering endpoints by trial and error. This skill makes that the default: bake the description in when you build a service, and look for it before you probe when you integrate with one. It's the discoverability half of the API story — `api-design-checklist` keeps an API internally consistent; this skill makes sure agents can actually find and use it.

## When to use it

- **BUILDING a new self-hosted service** — after scaffolding, before considering it done.
- **INTEGRATING with an existing unfamiliar service** — before crawling the UI or probing endpoints by trial and error.

## Decision tree

New service → bake-in. Existing service → discover-first, then probe-and-write-back only if no description exists.

## Bake-in (new services)

Treat the API description as a required step before "done", not optional polish.

1. Detect the framework from the project manifest (`package.json`, `pyproject.toml`, `go.mod`, ...).
2. Check for cheap OpenAPI support — FastAPI and ASP.NET Core serve `/openapi.json` with zero extra code.
3. If supported, add the generator and serve the spec at a conventional path (`/openapi.json` preferred; `/swagger.json`, `/api-docs` acceptable). Verify with `curl`.
4. Otherwise write a minimal `API.md` at the repo root covering every endpoint: method, path, params, and a working curl example.
5. Verify before done: every route appears in the spec or `API.md`, the curl examples actually work, and the spec path is reachable at the conventional location.

## Discover-first (existing services)

1. Probe conventional spec paths: `/openapi.json`, `/swagger.json`, `/api-docs`, `/swagger-ui/`, `/redoc`, `/api`, `/docs`.
2. Search the repo: `API.md`, a README API section, `docs/`, OpenAPI yaml files, Postman collections, `*.http` files.
3. Use what you find — extract base URL, auth scheme, endpoints, params, request/response shapes. Integrate against it; do not re-derive by probing.
4. Only if neither a spec path nor repo documentation exists, fall back to probe-and-write-back.

## Probe-and-write-back (no description exists)

1. **Ask the user first** — the person who runs the service usually knows the endpoints. Asking is cheaper and safer than probing.
2. Inspect the UI and the network requests it makes (browser devtools network tab, or `curl` the page and follow the XHR/fetch calls).
3. Probe carefully, read-only: GET/HEAD/OPTIONS only unless writes are explicitly authorized; use provided credentials; respect rate limits; stop on harm signals.
4. Build the discovered description into the project — spec generation if the framework supports it, otherwise `API.md`.
5. **Write back** so the next agent doesn't repeat the work — the core loop is discover → document → done.

## Probing safety rules

1. Read-only first — GET/HEAD/OPTIONS before anything else.
2. No writes without explicit authorization — never POST/PUT/DELETE unless the user approves.
3. Use provided credentials; never bypass or escalate auth.
4. Respect rate limits; back off and retry with delay on 429.
5. Stop if responses suggest you're mutating state or triggering side effects.
6. Prefer asking over guessing — the user knows more than the probe will tell you.

## Expected output

A service that ships with a machine-readable API description at a conventional path (or an `API.md`), and an integration that read that description rather than probing endpoints by trial and error. OpenAPI is better than `API.md`; `API.md` is always better than nothing.
