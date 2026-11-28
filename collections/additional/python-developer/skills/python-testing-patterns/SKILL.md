---
name: Python Testing Patterns
description: pytest patterns for fast, deterministic tests. Use when writing or reviewing Python tests, fixtures or mocks.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [python, testing, pytest]
---
## Purpose

Keep tests fast, deterministic and meaningful so a failure points at a real defect.

## When to use it

When adding tests, fixing flaky ones, or reviewing a change whose tests mock too much.

## Checklist

- **Structure**: arrange, act, assert; one behaviour per test; names that state the behaviour.
- **Fixtures**: small fixtures with the narrowest scope that works; no hidden ordering between tests.
- **Parametrise** instead of copy-pasted cases; include the boundary and failure cases.
- **Isolation**: no real network, clock or randomness; inject or patch them. Use `tmp_path` for files.
- **Mocks**: mock at the boundary you own (the HTTP client, the repository), not the function under test; prefer fakes over deep patch chains.
- **Async**: use the project's async pytest plugin consistently; await everything.
- **Flaky tests are blocking**: find the cause (shared state, time, ordering); do not add retries or sleeps.

## Expected output

A test suite that is deterministic, runs quickly, and fails only when behaviour changes.
