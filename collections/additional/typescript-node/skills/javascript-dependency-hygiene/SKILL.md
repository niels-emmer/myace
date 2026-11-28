---
name: JavaScript Dependency Hygiene
description: npm dependency and publishing checklist for supply-chain safety. Use when adding, upgrading or publishing packages.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [node, npm, supply-chain]
---
## Purpose

Reduce the chance that a compromised or careless dependency reaches production or your published package.

## When to use it

When adding or upgrading a dependency, changing CI install steps, or publishing a package.

## Checklist

- **Lockfile**: committed; CI installs with `npm ci` and fails if `package.json` and the lockfile disagree.
- **Adding**: check the package is needed, maintained, and not a near-duplicate of one already present; look at its install scripts and its own dependency count.
- **Scripts**: run installs with lifecycle scripts disabled where the project allows it, and allow-list the few packages that need them.
- **Ranges**: pin exact versions for applications; libraries use ranges consumers can satisfy.
- **Audit**: run the audit command in CI and triage findings rather than ignoring them; verify registry signatures and provenance where supported.
- **Publishing**: publish from CI using trusted publishing (OIDC) or provenance rather than a long-lived token, protect the publishing job with required approval, and keep the package's `files` list minimal.
- **Tokens**: any remaining automation token is scoped, short-lived and not readable by pull-request workflows.

## Expected output

A dependency set that is intentional, reproducible and published without long-lived credentials.
