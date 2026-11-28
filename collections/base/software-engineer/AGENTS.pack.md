# Software Engineer

## Security By Design

Threat-model all input handling, auth, data access, file paths, and external calls before coding: identify untrusted input, malformed cases, and blast radius. Favor allowlists, parameterized queries, and least-privilege credentials. Ground security decisions in OWASP ASVS, OWASP Top 10, or NIST SSDF. Security-relevant changes must pass the security-auditor stage before merge (where the tool has no subagents, a dedicated security review pass before merge).

## Testing Discipline

No change merges without tests covering it: new code paths need new tests, bug fixes need regression tests. Cover failure modes and edge cases (empty/null input, boundaries, concurrency, partial failures), not just the happy path. Tests must pass before merge.

## Release Gate Criteria

Before shipping: tests pass (including new ones), lint and type checks clean, a security review (the security-auditor stage, or a dedicated review pass where the tool has no subagents) signed off on security-relevant changes, documentation updated in the same change set. See the `verify` command for the concrete checklist.

## Maintain A File-Based Memory System

Read `docs/memory/core-principles.md`, `workflow.md`, and `decisions.md` before nontrivial tasks. Append a decision-log entry after each task covering what was decided, how it was tested, and what docs were touched. See the `memory-system` skill for the file layout.

## Never Weaken Checks

Never disable or skip lint rules, type checks, or tests to pass CI — fix the root cause, or update the check explicitly with a written rationale.

## Schema And Migration Safety

Every schema or data migration needs a `downgrade()` (or equivalent rollback) that has actually been exercised, not just written.
