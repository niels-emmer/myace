---
name: Security Checklist
description: A PASS/FAIL/N-A checklist covering injection, authorization, secrets handling, dependency risk, and input validation for reviewing a diff or codebase.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor]
tags: [security, review, checklist, owasp]
---
## Purpose

Give a security review a fixed, repeatable shape so two different reviewers checking the same change produce comparable results, and so nothing gets skipped because it wasn't top of mind that day.

## When to use it

Any time you're reviewing a diff, a pull request, or a codebase specifically for security issues — whether that's the `security-auditor` agent doing a full pass or a quick self-check before a change ships. Run through every category below; mark items N/A with a one-line reason rather than silently skipping them.

## Checklist

For each item: record **PASS**, **FAIL**, or **N/A**. Every FAIL needs a concrete failure scenario (the specific input/state and the specific bad outcome) and, where it fits, a citation (CWE number, OWASP Top 10/ASVS category, or NIST SSDF practice).

### Injection
- User-controlled input never reaches a SQL query, shell command, template engine, or log sink by string concatenation or interpolation — parameterized queries, prepared statements, or an equivalent safe API are used instead. (Maps to CWE-89, CWE-78, OWASP A03:2021 – Injection.)
- Any use of `eval`, dynamic code execution, or deserialization of untrusted data is either absent or explicitly justified and sandboxed.

### Authorization and authentication
- Every endpoint or handler that touches non-public data checks both that the caller is authenticated *and* that they're authorized for the specific resource being accessed (object-level authorization, not just route-level). (OWASP A01:2021 – Broken Access Control.)
- Session tokens, API keys, and password reset tokens are generated with a cryptographically secure random source, expire, and are invalidated on logout/rotation.
- Privilege checks happen server-side; client-supplied role/permission fields are never trusted as-is.

### Secrets handling
- No credential-shaped string (API key, token, password, connection string, private key) appears in the diff, in source, in config committed to the repo, or in a log line. Any hit here is an automatic FAIL — see the `secrets-scan-checklist` skill.
- Secrets are loaded from an environment variable or secret-management service, not hardcoded or committed, even in test fixtures.

### Dependency risk
- New or updated dependencies come from a trustworthy source (official package index, verified publisher) rather than an unpinned git reference or unknown mirror.
- No dependency with a known critical/high CVE affecting the version in use is introduced without an explicit, documented reason.
- Dependency permissions/scopes (e.g. an OAuth app requesting broad scopes, an npm package with postinstall scripts) are proportionate to what the dependency actually needs to do.

### Input validation and output handling
- Every external input (request body, query param, header, file upload, webhook payload) is validated for type, shape, and business constraints at the boundary before use (see the `Validate At The Boundary` rule in the backend collection, if layered in).
- Output rendered into HTML, shell commands, or other interpreted contexts is escaped/encoded for that context — not just validated on the way in.
- Error responses returned to a caller never include stack traces, raw database errors, or internal file paths.

### New attack surface
- Any new network-facing endpoint, new data store, or new trust boundary introduced by this change has a recorded threat-model pass (see `threat-modeling-quickstart`) — absence of one is itself a FAIL on this line, regardless of what the rest of the review finds.

## Expected output

A findings table or list, one row per checklist item, in the shape:

```
[PASS|FAIL|N/A] <item> — <evidence: file:line, snippet, or reason N/A>
  (FAIL only) Scenario: <specific input/state> → <specific bad outcome>
  (FAIL only) Reference: <CWE-xxx / OWASP Axx:2021 / NIST SSDF practice>
```

Followed by a one-line overall summary (e.g. "3 FAIL, 1 of them a hard-fail secret — escalated separately per the Secrets rule").
