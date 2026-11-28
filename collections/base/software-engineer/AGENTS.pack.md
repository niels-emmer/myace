# Software Engineer

## Security By Design

<!-- myace: priority=90 tags=security -->

Threat-model all input handling, auth, data access, file paths, and external calls before coding: identify untrusted input, malformed cases, and blast radius. Favor allowlists, parameterized queries, and least-privilege credentials. Ground security decisions in OWASP ASVS, OWASP Top 10, or NIST SSDF. Security-relevant changes must pass the security-auditor stage before merge (where the tool has no subagents, a dedicated security review pass before merge).

## Release Gate Criteria

<!-- myace: priority=70 tags=quality -->

Before shipping: tests pass (including new ones), lint and type checks clean, a security review (the security-auditor stage, or a dedicated review pass where the tool has no subagents) signed off on security-relevant changes, documentation updated in the same change set. See the `verify` command for the concrete checklist.

## Never Weaken Checks

<!-- myace: priority=70 tags=quality -->

Never disable or skip lint rules, type checks, or tests to pass CI — fix the root cause, or update the check explicitly with a written rationale.

## Schema And Migration Safety

<!-- myace: priority=70 tags=safety -->

Every schema or data migration needs a `downgrade()` (or equivalent rollback) that has actually been exercised, not just written.

## Dependency Hygiene

<!-- myace: priority=90 tags=security,supply-chain -->

Adding a dependency is a decision, not a convenience: check it is maintained, its licence fits, and it isn't replaceable by a few lines of your own. Pin versions (commit the lockfile; no `latest` or unpinned installs in CI or Dockerfiles), read what an upgrade changes, and never install from an unverified source or run a downloaded script you haven't read. Run the ecosystem's vulnerability audit before release and treat a known-exploitable finding as blocking.

## Observability Baseline

<!-- myace: tags=operations -->

Make behaviour visible from the first version: log at boundaries (requests, jobs, external calls) with a correlation id and never log secrets or personal data; expose the few numbers that say whether it is healthy (rate, errors, latency); and make errors carry enough context to act on without reproducing them. Add instrumentation in the same change as the feature, not after the first incident.
