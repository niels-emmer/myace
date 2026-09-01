---
name: Test Strategy
description: How to decide what to test at what level — the test pyramid, risk-based coverage, and matching test depth to change risk.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [testing, strategy, coverage]
---
## Purpose

A test suite that's the right shape is cheap to run and catches real regressions. This skill is a checklist for deciding what to test at what level, so effort goes where the risk is rather than into a slow, brittle suite that mostly re-tests the same paths.

## When to use it

When starting a new feature, adding tests to an existing one, or reviewing whether a suite is well-shaped. Also when a suite has grown unwieldy and needs rebalancing.

## Checklist

- **Shape it like a pyramid.** Most tests at the unit level (fast, isolated), fewer at integration (boundaries between components), fewest at e2e (critical user journeys). A cone — lots of slow e2e tests — is a maintenance trap.
- **Test at the level that exercises the behavior.** Logic belongs in unit tests; a frontend-backend contract belongs in an integration test; a multi-service user journey belongs in e2e. Don't write a slow e2e test for something a unit test covers.
- **Risk-based depth.** The deeper the test investment, the higher the change risk: auth, payments, data migration, and concurrency deserve more coverage than a pure UI copy change.
- **Cover failure modes deliberately.** Boundaries, empty/null input, partial failures, concurrency, and authorization denials — the happy path is the least likely case to break in production.
- **Coverage is a signal, not a target.** Use coverage to find untested paths, not as a pass/fail gate. A covered module with no behavioral assertions isn't tested.

## Expected output

A suite that's fast enough to run often, shaped like a pyramid, and concentrated on the behaviors most likely to break — with failure modes covered deliberately rather than by accident.