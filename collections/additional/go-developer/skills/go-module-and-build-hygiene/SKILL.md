---
name: Go Module And Build Hygiene
description: Module, layout and dependency checklist for Go projects. Use when creating a module, adding dependencies or setting up CI.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [go, build, modules]
---
## Purpose

Keep a Go build reproducible and its dependencies reviewed.

## When to use it

When creating a module, bumping dependencies or the Go version, or setting up CI for a Go project.

## Checklist

- **Layout**: `cmd/<app>` for binaries, `internal/` for code not meant to be imported elsewhere; avoid a `util` package.
- **Module files**: `go.mod` and `go.sum` committed; CI runs `go mod tidy` and fails on a diff.
- **Go version**: set the `go` directive to the minimum you support and test on it and on the latest release.
- **Dependencies**: read the changelog for a bump; avoid dependencies that wrap a few lines of standard library.
- **Vulnerabilities**: run `govulncheck` in CI; fix by upgrading, or record why a finding is unreachable.
- **Build**: reproducible flags (`-trimpath`), version injected via `-ldflags`, static binary where the deployment allows it.
- **Generated code**: committed or generated in CI, but not both; CI verifies it is up to date.

## Expected output

A module that builds the same way locally and in CI and whose dependency changes are explicit and reviewed.
