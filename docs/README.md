# MyACE Documentation

This is the deep-dive documentation for MyACE — written for both humans and
AI coding agents working on the codebase. It complements, rather than
repeats, two other documents you should already know about:

| Document | Audience | Purpose |
|---|---|---|
| [`README.md`](../README.md) | Humans, first visit | What MyACE is, screenshots, how to install/run it |
| [`AGENTS.md`](../AGENTS.md) / `CLAUDE.md` | AI coding agents | Terse, enforceable rules and known gotchas — read before editing code |
| **`docs/`** (this documentation) | Humans and agents, deep dives | *Why* the system is built this way, not just *what* the rules are |

If `AGENTS.md` is the "don't do this" list, `docs/` is the "here's the whole
picture" reference. When a rule in `AGENTS.md` references a concept in more
depth, it links here.

## Contents

- **[`API.md`](../API.md)** — the HTTP API: base URL, auth (session cookie
  + Bearer token), route groups, and working curl examples. The canonical
  machine-readable spec is served at `/openapi.json`; this file is the
  orientation layer on top of it.
- **[architecture.md](architecture.md)** — the three components, how they
  talk to each other, the compilation pipeline, and the authentication
  model. Start here.
- **[data-model.md](data-model.md)** — every table, its columns, and how
  they relate. What's a foreign key vs. a JSON-as-text column and why.
- **[invariants.md](invariants.md)** — the rules the system must never
  violate (ownership, visibility, IR shape) and where they're enforced in
  code. Read this before touching authorization or the canonical IR schema.
- **[extending.md](extending.md)** — task-oriented guides for common
  extensions: adding a target adapter, adding an artifact type, adding an
  auth provider, adding an API route.
- **[deployment.md](deployment.md)** — forking and hardening a fresh
  install, and running it in production (single machine, or behind a
  reverse proxy — including an nginx-proxy-manager walkthrough).
- **[cli.md](cli.md)** — installing `myace` (binary or pip), the full
  command reference, and the `import`/`serve`/`check`/`watch` workflows.
- **[mcp.md](mcp.md)** — the read-only MCP server: connecting an agent, the
  five tools and four resources, limits, and troubleshooting.
- **[onboarding-wizard.md](onboarding-wizard.md)** — the five-step first-run
  wizard, resume/skip semantics, add-on pairing, install methods, and why an
  install claim is not verification.
- **[ci-drift-check.md](ci-drift-check.md)** — the distributable
  `myace-check` GitHub Action other repos use to fail CI on sync drift
  against a MyACE server.
- **[backups.md](backups.md)** — database backup retention defaults,
  offsite copy guidance, and the restore procedure.
- **[debugging.md](debugging.md)** — known gotchas with concrete symptoms,
  root causes, and fixes. If something is behaving strangely, check here
  before spending an hour on it.
- **[adr/](adr/)** — Architecture Decision Records. Short documents that
  capture *why* a non-obvious decision was made, so nobody re-litigates it
  (or repeats a mistake) six months later.
- **[adapters-research.md](adapters-research.md)** — every target adapter
  MyACE ships, its confirmed file format and doc citation, plus a Future
  Plans section for unbuilt candidates (Zed AI, CodeGPT) and known gaps in
  shipped adapters, open to contribution.
- **[plans/](plans/)** — design records for multi-phase work. Most relevant
  now: [`plans/v2.0-onboarding-revamp.md`](plans/v2.0-onboarding-revamp.md)
  (pack/setup/install vocabulary, navigation, Home, packs library, ⌘K, and
  how the work was versioned and shipped as 2.0.0).
  [`plans/agent-install-url.md`](plans/agent-install-url.md) is a scoped but
  **unbuilt** design: a public URL an agent can fetch to install a pack,
  including the payload format and why it is not possible with today's
  setup-scoped, authenticated compile routes.

## Keeping this up to date

Documentation here is expected to change in the same PR as the code it
describes — see the rule in [`AGENTS.md`](../AGENTS.md#14-documentation-maintenance).
A change that isn't reflected in `docs/`, `README.md`, or `AGENTS.md` (as
appropriate) isn't done yet.
