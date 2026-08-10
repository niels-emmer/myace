---
name: Backend Test Patterns
description: Guidance for covering the failure and edge paths of a backend change — bad input, concurrent writes, partial failure — not just the happy path.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor]
tags: [testing, backend]
---
## Purpose

A backend test suite that only exercises the happy path proves the feature can work, not that it's safe. This skill is guidance for rounding out test coverage on the paths that actually cause incidents: bad input, concurrent access, and partial failure — the situations a demo never hits but production eventually will.

## When to use it

Whenever you finish implementing an endpoint, service method, or migration-adjacent code path and are writing or reviewing its tests. Especially relevant for anything that mutates state, touches more than one row/table, or could be called concurrently or retried.

## Bad-input coverage

- For every field an endpoint accepts, test at least one case of: missing when required, wrong type, out-of-range value, and a value that's syntactically valid but semantically nonsensical (e.g. an end date before a start date).
- Test the boundary values, not just clearly-invalid ones — the empty string, zero, the maximum allowed length, a list with one item versus the max allowed items.
- Confirm the *response* on bad input, not just that it fails: right status code, error shape matches the rest of the API, and no internal detail (stack trace, DB error text) leaked into the body.

## Concurrency and race coverage

- For anything backed by a uniqueness constraint (can't have two of the same thing), write a test that attempts two near-simultaneous creates and confirms exactly one succeeds with a sane error on the other — not a crash or a silent duplicate.
- For read-modify-write logic (increment a counter, transition a status field), consider what happens if two requests interleave. If the code relies on an optimistic-locking version check or a database-level atomic operation, test that the loser of the race gets a clear conflict response rather than silently clobbering the winner's update.
- These don't always need true multi-threaded tests — simulating the interleaving directly (e.g. issuing the two writes in the order a race would produce, or asserting the query includes the guard condition it needs) is often enough to catch the bug without a flaky concurrency test.

## Partial-failure coverage

- For any operation that touches multiple resources or does multiple steps (create a row, then call an external service, then update a status), test what happens when a later step fails: does the earlier work get rolled back, retried, or left in a consistent-but-incomplete state on purpose? Whichever is intended, there should be a test asserting it, not just an assumption.
- For idempotent/retryable endpoints, write a test that calls the endpoint twice with the same input/idempotency key and asserts the end state matches a single call — this is the concrete way to verify the idempotency guarantee actually holds, not just that it was intended.
- If a failure path logs or reports to an external system (metrics, alerting), it's reasonable to at least assert that the failure path is reached and handled, even if you don't assert the exact log content.

## Expected output

A test file where, for each mutating endpoint or service method, at least one test exists for a bad-input case, a conflicting/concurrent-write case (where relevant), and a partial-failure case (where the operation has more than one step) — alongside the happy path, not instead of it.
