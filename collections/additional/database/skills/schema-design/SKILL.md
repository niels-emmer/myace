---
name: Schema Design
description: Principles for designing database schemas that stay additive, constraint-driven, and safe to evolve as the application grows.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [database, schema, design]
---
## Purpose

A schema is the longest-lived artifact in most systems — it outlives every framework and most of the code that reads it. This skill is a checklist for designing schemas that stay easy to evolve: additive by default, constraint-driven, and explicit about the decisions that are hard to reverse.

## When to use it

Whenever you're designing a new table, changing an existing one, or reviewing a schema change. The discipline matters most for tables that will accumulate data and consumers over time.

## Checklist

- **Additive by default.** New columns are nullable or have a default; new tables are created empty. A breaking change (rename, drop, type change) is a deliberate, reviewed decision with a migration path — not an accident of editing a column.
- **Constraints over convention.** Enforce invariants with foreign keys, uniqueness, check constraints, and not-null wherever the DB can express them. If an invariant can be violated by any code path that forgets it, it belongs in the DB.
- **Explicit soft vs. hard delete.** Decide per entity, and make the decision visible. Soft-delete columns need to be filtered everywhere; hard-delete is irreversible. Don't default to one silently.
- **Types match meaning.** Use the narrowest type that fits the data (dates as dates, not strings; money as a decimal, not a float). A type that's too loose invites bugs that are hard to find later.
- **Keys are stable.** Prefer surrogate keys that never change meaning. A natural key that can change (email, username) makes a poor primary key.
- **Naming is consistent.** One convention for table/column/index names across the schema. A new table that drifts from the surrounding naming is a review finding, not a style preference.

## Expected output

A schema that a developer familiar with the system can extend without guessing: new columns are additive, invariants are enforced by the DB, delete semantics are explicit per entity, and the naming/typing is consistent with everything around it.