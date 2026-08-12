---
name: CI/CD Pipeline Design
description: Stage isolation, caching, secret injection, artifact promotion, and rollback strategy for CI/CD pipelines.
version: "1.0.0"
priority: 60
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [devops, ci-cd, pipelines]
---
## Purpose

Design pipelines that are safe, fast, and auditable.

## Checklist

- **Stage isolation**: each stage (build, test, deploy) runs independently; failure in one doesn't cascade.
- **Caching**: dependency caches are content-addressed and invalidated on lockfile changes.
- **Secret injection**: secrets come from a secrets manager at runtime, not from repo variables or baked-in.
- **Artifact promotion**: same binary/image promoted through environments — never rebuild for staging/prod.
- **Rollback**: production rollback is a one-click or one-command operation, tested regularly.
- **Gate conditions**: each environment requires the previous stage's tests to pass before proceeding.
- **Notifications**: pipeline failures notify the owning team with relevant context (commit, stage, logs).

## Expected output

A pipeline definition where each stage is independently verifiable, artifacts are immutable, and production rollback is faster than fix-forward.
