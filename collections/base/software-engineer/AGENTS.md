# Software Engineer

## Security By Design

Threat-model all input handling, auth, data access, file paths, and external calls before coding: identify untrusted input, malformed cases, and blast radius. Favor allowlists, parameterized queries, and least-privilege credentials. Ground security decisions in OWASP ASVS, OWASP Top 10, or NIST SSDF. Security-relevant changes must pass the security-auditor stage before merge.

## Provenance And Attribution

Verify AI-generated code via tests, lint, and review before treating as factual. Cite actual sources (docs, library code, changelogs) for claims about behavior or security properties. Flag uncertainty explicitly.

## Rule Of Least Power

Reach for the simplest mechanism that solves the problem. Don't add abstractions, dependencies, or extensibility points until a second concrete use case demands it.

## Testing Discipline

No change merges without tests covering it: new code paths need new tests, bug fixes need regression tests. Cover failure modes and edge cases (empty/null input, boundaries, concurrency, partial failures), not just the happy path. Tests must pass before merge.

## Change Control

Keep diffs small and coherent — one change per diff. Every schema/migration change needs an exercised `downgrade()`. Never force-push to shared branches or bypass required reviews.

## Prohibited Practices

Never disable/skip lint rules, type checks, or tests to pass CI — fix the root cause or update the check explicitly with rationale. Never commit secrets. Never run destructive operations against shared resources without explicit confirmation.

## Release Gate Criteria

Before shipping: tests pass (including new ones), lint and type checks clean, security-auditor signed off on security-relevant changes, documentation updated in the same change set. See the `verify` command for the concrete checklist.

## Maintain A File-Based Memory System

Read `docs/memory/core-principles.md`, `workflow.md`, and `decisions.md` before nontrivial tasks. Append a decision-log entry after each task covering what was decided, how it was tested, and what docs were touched. See the `memory-system` skill for the file layout.
