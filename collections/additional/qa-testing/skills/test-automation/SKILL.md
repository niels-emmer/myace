---
name: Test Automation
description: Patterns for keeping the test suite fast, deterministic, and runnable in CI — mocking rules, isolation, and flakiness prevention.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [testing, automation, ci]
---
## Purpose

A test suite only earns its keep if it runs fast and reliably — in CI, on every change, without a human babysitting flaky failures. This skill is a checklist for keeping automated tests deterministic, isolated, and cheap enough to run often.

## When to use it

When writing or reviewing automated tests, setting up CI test runs, or debugging a flaky test.

## Checklist

- **Isolate tests from each other.** No shared mutable state, no ordering dependencies, no test that depends on another test having run first. Each test sets up what it needs and cleans up after itself.
- **Mock at the boundary, not the behavior.** Mock external dependencies (network, time, filesystem, databases) at the interface, and keep the mock's behavior realistic — a mock that only returns the success response isn't testing the failure path at all.
- **Control time and randomness.** Freeze clocks, seed random generators, and avoid wall-clock timing assertions. A test that passes only when the machine is fast enough is a flaky test.
- **Keep the suite fast.** Fast tests get run more often. If a test is slow, ask whether it's at the right level before accepting the cost.
- **Flakiness is a defect.** A flaky test erodes trust in every result. Fix the root cause (timing, ordering, shared state) rather than retrying, skipping, or deleting the test.
- **CI runs the real suite.** The CI gate runs the same tests a developer runs locally — no "CI-only" suite that diverges from what's verified on a machine.

## Expected output

A suite that runs deterministically in CI on every change: isolated tests, realistic mocks, controlled time/randomness, and no flaky failures — fast enough that running it is the default, not a chore.