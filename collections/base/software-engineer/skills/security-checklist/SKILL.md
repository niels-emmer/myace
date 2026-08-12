---
name: Security Checklist
description: A structured PASS / FAIL / N/A checklist covering common risk categories for reviewing a diff before merge.
version: "1.0.0"
priority: 55
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [security, review, checklist]
---
## Purpose

A security review without a structure tends to catch whatever the reviewer happens to think of that day and miss whatever they don't. This checklist gives a repeatable set of categories to walk through explicitly for any change that touches input handling, auth, data access, or external systems, so coverage doesn't depend on what's top of mind. It's the working tool behind the `security-auditor` agent, but it's usable by anyone reviewing a diff.

## When to use it

For any change touching: user input (forms, query params, file uploads, API payloads), authentication or authorization logic, database queries, file paths or filesystem access, external API/network calls, cryptography or session/token handling, or dependency additions/updates. Skip it for changes with none of the above (e.g., a pure UI copy change) — mark the whole review N/A rather than force-fitting categories that don't apply.

## The checklist

Walk each category and mark it PASS (verified, no issue), FAIL (issue found — blocking), or N/A (doesn't apply to this diff), with a one-line note for anything not PASS/N/A:

1. **Injection** — Are all queries parameterized (no string-concatenated SQL)? Are shell commands built without interpolating untrusted input? Are file paths validated against traversal (`../`) before use? Is user input reflected into templates/HTML escaped by default?
2. **Authentication** — Does this path require authentication where it should? Are session/token checks happening on every request that needs them, not just the first one in a flow?
3. **Authorization** — Does this check *ownership or permission*, not just that the requester is logged in? (A logged-in user reaching another user's resource is the single most common authz bug — verify the check compares the resource's owner to the current user, not just `is_authenticated`.)
4. **Secrets handling** — Are there any hardcoded credentials, API keys, or tokens in this diff? Are secrets read from environment/secret storage rather than committed config? Are secrets excluded from logs and error messages?
5. **Dependency risk** — Is a new dependency actively maintained and from a trustworthy source? Does a version bump's changelog mention security fixes worth noting? Is the dependency's permission footprint (network access, filesystem access) proportionate to what it's used for?
6. **Data exposure** — Does an API response or log line include more data than the caller needs (e.g., full user objects instead of the specific fields required)? Is PII handled consistent with how the rest of the codebase treats it?
7. **Cryptography and sessions**, where relevant — Are standard library/vetted implementations used instead of hand-rolled crypto? Do session tokens have reasonable expiry and get invalidated on logout/password change?
8. **Input validation boundaries** — Is untrusted input validated (type, length, format, range) at the boundary where it enters the system, not assumed valid deeper in the call stack?

## Expected output

A short report listing each applicable category with its verdict and a one-line justification, e.g. `Authorization: FAIL — /api/documents/{id} loads by ID without checking collection ownership`. Blocking (FAIL) items should be specific enough that the fix is obvious without re-deriving the finding. Ground findings in OWASP ASVS / OWASP Top 10 categories or NIST SSDF practices where the mapping is genuinely clear — it makes the finding checkable against an external standard rather than a matter of opinion.
