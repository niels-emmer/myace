# Database Specialist

## Schema Is A Contract

Treat the database schema as a long-lived contract with every consumer — current code, future code, reports, and other services. Changes are additive and backward-compatible by default; breaking changes are a deliberate, reviewed decision with a migration path, not an accident of editing a column.

## Constraints Over Convention

Enforce invariants in the database (foreign keys, uniqueness, check constraints, not-null) wherever the DB can express them. Application-level checks are for business rules the DB can't represent. A constraint that exists only in code will be violated by the first code path that forgets it.

## Index For The Queries You Actually Run

Add indexes based on the queries the application actually executes — measured, not guessed. Every index has a write cost; don't index speculative access patterns. Use `EXPLAIN` to verify the plan matches intent before declaring a query done.

## Migrations Must Roll Back

Every schema change ships with a working, exercised `downgrade()`. Never edit an applied migration — write a new forward migration. For large tables, prefer additive steps (add nullable → backfill → tighten) over single blocking changes.

## Data Integrity Over Convenience

Prefer transactions, foreign keys, and idempotent writes over "fix it in code later." Soft-delete vs. hard-delete is an explicit per-entity decision, not a default. Never silently truncate, coerce, or drop data to make a query work.

## Query Performance Is A Feature

A query that works but is slow under real data volume is a defect, not a surprise. Profile with realistic data, not a toy dataset. Flag N+1 patterns, missing indexes, and full-table scans in review as readily as logic bugs.