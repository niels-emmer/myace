---
name: Rust Testing Patterns
description: Unit, integration, doc and property testing patterns for Rust. Use when writing or reviewing Rust tests.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [rust, testing]
---
## Purpose

Keep Rust tests close to the code, deterministic and meaningful.

## When to use it

When adding tests, testing error paths, or reviewing a change whose tests only cover the happy path.

## Checklist

- **Layout**: unit tests in a `#[cfg(test)]` module beside the code; integration tests in `tests/` using only the public API.
- **Doc tests**: examples in doc comments compile and run; keep them minimal and correct.
- **Errors**: assert on the error variant, not its string.
- **Determinism**: inject time and randomness; use temporary directories; no network.
- **Async**: use the runtime's test macro, and a paused clock for time-dependent tests where available.
- **Property tests** for parsers, encoders and invariants that example tests miss.
- **Unsafe code**: test under Miri where the project supports it.

## Expected output

Tests that cover the failure paths as well as the happy path and run the same way locally and in CI.
