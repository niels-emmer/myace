---
name: Test Patterns
description: What "well-tested" actually means — covering edge cases and failure modes deliberately, not just confirming the happy path runs once.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor]
tags: [testing, quality, edge-cases]
---
## Purpose

A test suite that only exercises the happy path proves the code works when everything goes right, which is the case least likely to break in production. The failure modes — bad input, empty state, concurrent access, partial success — are where real bugs live and where a thin test suite gives false confidence. This skill is a checklist for deliberately covering that space instead of stopping at the first green run.

## When to use it

Any time you write or extend tests for a nontrivial change — new functionality, a bug fix, or a refactor of logic that has any conditional branching. Run through the checklist below as a deliberate step, not an afterthought after the happy-path test already passes.

## Checklist

- **Happy path** — the code does the intended thing with valid, typical input. Necessary but not sufficient; don't stop here.
- **Boundary values** — empty string/list/collection, zero, negative numbers where they're conceptually possible, the first and last valid index, one-past-the-boundary values that should be rejected.
- **Null/missing/malformed input** — `None`/`null`/`undefined` where a value is expected, a required field missing from a payload, a type that doesn't match what's expected, malformed JSON or encoding.
- **Failure and partial-failure modes** — what happens when a dependency (network call, database, filesystem) fails outright, times out, or returns a partial/unexpected result. A test that only mocks the success response isn't testing the failure path at all.
- **Concurrency and ordering**, where relevant — two callers hitting the same code path at once, operations that assume an order that isn't actually guaranteed, idempotency (does calling this twice with the same input cause a problem it shouldn't).
- **Regression coverage for bug fixes** — a fix without a test that fails on the old code and passes on the new one isn't confirmed to have actually fixed anything; it's confirmed to compile.
- **Authorization boundaries**, where applicable — does a test confirm that a user without permission is actually denied, not just that a user with permission is allowed. A missing negative-authorization test is a common way authz bugs slip through.

## Expected output

For a nontrivial change, a reviewer should be able to look at the test file and answer "what happens if this gets bad input" and "what happens if the fix regresses" without reading the implementation — the tests themselves should make the covered scenarios legible. If a category above is deliberately skipped (e.g., concurrency doesn't apply), that's fine, but it should be a conscious call, not an oversight.
