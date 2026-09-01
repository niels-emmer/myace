---
name: Data Integrity
description: Checklist for protecting data correctness — transactions, idempotency, referential integrity, and explicit delete semantics.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [database, integrity, transactions]
---
## Purpose

Data integrity failures are the most expensive bugs a system can have — they corrupt state that other code, reports, and users depend on, and they're often discovered long after the damage. This skill is a checklist for protecting correctness at the database layer rather than hoping application code gets it right.

## When to use it

Whenever a change writes data — new writes, updates, deletes, or batch operations — or when reviewing a change that does. The discipline matters most for multi-step operations where a partial failure would leave inconsistent state.

## Checklist

- **Use transactions for multi-step writes.** If an operation updates several rows or tables, it belongs in a transaction so a failure doesn't leave a half-applied state. Know your database's isolation level and what it actually guarantees.
- **Prefer idempotent writes.** Design mutating operations so retries are safe: idempotency keys, uniqueness constraints, or naturally idempotent operations (`set status = X` over `increment counter`). A retried request should not double-apply.
- **Let the DB enforce referential integrity.** Foreign keys prevent orphaned rows. If you're deleting a parent, decide explicitly what happens to children (cascade, restrict, nullify) — don't leave it to application code to remember.
- **Make delete semantics explicit.** Soft-delete vs. hard-delete is a per-entity decision, not a default. If soft-delete, every read path must filter deleted rows; if hard-delete, the data is gone — say so.
- **Never silently coerce or truncate.** A write that drops data to make a constraint pass (truncating a string, coercing a type, swallowing a uniqueness violation) is hiding a bug, not fixing one.
- **Verify under failure.** Test what happens when a write fails partway — a transaction that rolls back cleanly is verified code, not assumed code.

## Expected output

Writes that are transactional where they span multiple steps, idempotent where retries are possible, protected by DB-level referential integrity, and explicit about delete semantics — with failure paths tested rather than assumed.