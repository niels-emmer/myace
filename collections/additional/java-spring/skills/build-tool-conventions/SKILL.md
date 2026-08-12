---
name: Build Tool Conventions
description: Maven/Gradle standard layout, dependency management, plugin versioning, and reproducible builds.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [java, build, maven, gradle]
---
## Purpose

Keep builds reproducible and dependency management predictable.

## Checklist

- **Standard layout**: Maven (`src/main/java`, `src/test/java`) or Gradle (`src/main/java`, `src/test/java`) conventions.
- **Dependency pinning**: all dependency versions declared in a BOM (`dependencyManagement` in Maven, `platform` in Gradle) or pinned per-dependency.
- **Lockfiles**: Maven Enforcer plugin or Gradle dependency locking to prevent unexpected transitive upgrades.
- **Plugin versions**: all build plugins pinned to specific versions, not latest.
- **Reproducible builds**: `mvn clean verify` or `gradle clean build` produces the same output from the same source + lockfile.
- **CI integration**: build runs in CI with the same lockfile; dependency cache is content-addressed.

## Expected output

A build configuration where `checkout → build` produces deterministic output, and dependency changes are explicit version bumps, not accidental transitive upgrades.
