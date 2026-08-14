---
name: End-to-End Testing
description: E2E test patterns — what to test, how to structure tests, environment management, avoiding flakiness.
version: "1.0.0"
priority: 55
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [fullstack, testing, e2e]
---
## Purpose

Catch integration bugs that layer-isolated tests miss.

## When to use it

For every feature that spans frontend and backend.

## Checklist

- **Scope**: test critical user journeys (login, CRUD, error paths) — not every UI permutation.
- **Structure**: use page objects or fixtures for maintainable test code.
- **Environment**: dedicated test database, clean state per test run.
- **Data seeding**: set up test data as part of the test, not in shared fixtures.
- **Flakiness prevention**: use wait strategies for async operations, retry on transient failures.
- **CI integration**: run E2E tests in CI, not just locally. Fail the build on E2E failures.

## Expected output

A suite of E2E tests covering the critical paths of each feature, running in CI with reliable pass/fail results.
