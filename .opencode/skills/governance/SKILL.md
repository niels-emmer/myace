---
name: governance
description: MyACE project-specific governance rules. Data classification, ADR process, documentation maintenance, dependency compliance, and audit trail. Load at session start for any work on this project.
license: MIT
compatibility: opencode
---

## MyACE-specific governance

This skill extends the global governance rules with MyACE project-specific conventions.

### Data classification

Same classification table as the global governance skill (PUBLIC / INTERNAL / CONFIDENTIAL / REGULATED). When in doubt, treat as CONFIDENTIAL.

### ADR process (Architecture Decision Records)

MyACE uses ADRs to capture non-obvious, expensive-to-reverse decisions. See `docs/adr/README.md` for the full guide.

**When to write an ADR:**
- Picking an auth strategy, data model shape, deployment topology
- Anything where a reasonable engineer could have gone a different direction
- A decision that's expensive to reverse

**When NOT to write an ADR:**
- Routine features, bug fixes, or anything where the code itself is the whole explanation

**Format:**
1. Copy `docs/adr/template.md`
2. Number sequentially (next is `0006`)
3. Keep it short — one screen
4. Never renumber or delete a past ADR
5. If superseded, mark old status as `Superseded by ADR-00XX`

**ADR structure:**
```markdown
# ADR-00XX: Title

**Status:** Proposed | Accepted | Superseded by ADR-00XX

## Context
What problem forced this decision? What constraints were in play?

## Decision
What did we decide to do, stated as a clear, single sentence.

## Alternatives considered
What else was on the table, and why it was rejected.

## Consequences
What this makes easier, what it makes harder, and what it gives up.
```

### Documentation maintenance

MyACE maintains documentation for two audiences, both updated in the same PR as the code:

| Document | Audience | Purpose |
|---|---|---|
| `README.md` | Humans, first visit | What MyACE is, how to run it |
| `AGENTS.md` / `CLAUDE.md` | AI coding agents | Terse, enforceable rules and gotchas |
| `docs/` | Humans and agents, deep dives | Architecture, data model, invariants, ADRs, debugging, extending |

**Before considering a change done:**
- **New route, model field, or config setting** → update `README.md` and `docs/data-model.md`/`docs/invariants.md`
- **New non-obvious pattern, gotcha, or convention** → add a numbered rule to `AGENTS.md` and an entry in `docs/debugging.md`
- **Expensive-to-reverse decision** → write an ADR in `docs/adr/`
- **Stale doc** → fix it in the same PR, don't leave it for later
- **Removing a feature or file** → grep across `README.md`, `AGENTS.md`, `CLAUDE.md`, and `docs/` for dangling references

### Dependency compliance

Before adding a dependency:
1. Check if the standard library handles it first
2. Verify OSI-approved license (MIT, Apache 2.0, BSD, LGPL — not AGPL or unlicensed)
3. Verify actively maintained, no critical CVEs
4. Pin to a specific version
5. Use a trusted registry (PyPI, npm)
6. Document the decision explicitly

### Audit trail

For AI-driven changes to this project:
- Record what changed, why, and whether it was AI-authored or human-authored
- Use `/decision-log` for architecture decisions
- Prefix enterprise-affecting AI-authored commits with `[ai]` in the body
- Auth, payments, cryptography, data access, or production infrastructure changes require human review before merge

### Environment isolation

- Never mix personal and enterprise credentials, tokens, or accounts in the same session
- Flag any detected cross-contamination immediately
- The `.env` file is gitignored — never commit it
- API keys, OIDC secrets, and database passwords live in `.env`, never in code
