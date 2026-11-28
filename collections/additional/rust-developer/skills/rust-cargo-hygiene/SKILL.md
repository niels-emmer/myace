---
name: Rust Cargo Hygiene
description: Cargo workspace, feature and dependency checklist for Rust projects. Use when creating a crate, adding dependencies or setting up CI.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [rust, cargo, build]
---
## Purpose

Keep a Rust build reproducible, lean and checked for advisories.

## When to use it

When creating a crate or workspace, adding or upgrading dependencies, or setting up CI.

## Checklist

- **Edition and MSRV**: set `edition` and `rust-version`; test on the MSRV and on stable in CI.
- **Lockfile**: commit `Cargo.lock` for binaries and services; libraries may leave it out but should test against current dependency versions.
- **Features**: additive features only; default features minimal; document each feature; test the main combinations.
- **Workspace**: share dependency versions and lints through `[workspace.dependencies]` and `[workspace.lints]`.
- **Advisories**: `cargo audit` or `cargo deny check` in CI for advisories, licences, bans and sources.
- **Build scripts and proc-macros** run arbitrary code at build time; review new ones as you would an install script.
- **Profiles**: set `release` options deliberately (LTO, `panic`, `codegen-units`) and measure before tuning.

## Expected output

A crate or workspace whose dependency set is minimal, checked for advisories, and builds the same way everywhere.
