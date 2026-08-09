# MyACE Documentation

This directory is the deep-dive documentation for MyACE — written for both
humans and AI coding agents working on the codebase. It complements, rather
than repeats, two other documents you should already know about:

| Document | Audience | Purpose |
|---|---|---|
| [`README.md`](../README.md) | Humans, first visit | What MyACE is, screenshots, how to install/run it |
| [`AGENTS.md`](../AGENTS.md) / `CLAUDE.md` | AI coding agents | Terse, enforceable rules and known gotchas — read before editing code |
| **`docs/`** (this directory) | Humans and agents, deep dives | *Why* the system is built this way, not just *what* the rules are |

If `AGENTS.md` is the "don't do this" list, `docs/` is the "here's the whole
picture" reference. When a rule in `AGENTS.md` references a concept in more
depth, it links here.

## Contents

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
- **[debugging.md](debugging.md)** — known gotchas with concrete symptoms,
  root causes, and fixes. If something is behaving strangely, check here
  before spending an hour on it.
- **[adr/](adr/)** — Architecture Decision Records. Short documents that
  capture *why* a non-obvious decision was made, so nobody re-litigates it
  (or repeats a mistake) six months later.

## Keeping this up to date

Documentation here is expected to change in the same PR as the code it
describes — see the rule in [`AGENTS.md`](../AGENTS.md#14-documentation-maintenance).
A change that isn't reflected in `docs/`, `README.md`, or `AGENTS.md` (as
appropriate) isn't done yet.
