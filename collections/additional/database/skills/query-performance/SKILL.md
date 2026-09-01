---
name: Query Performance
description: Checklist for writing and reviewing queries that hold up under realistic data volume — index selection, plan verification, and the common failure patterns.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [database, performance, queries]
---
## Purpose

A query that works on a toy dataset but degrades under real data volume is a defect, not a surprise. This skill is a checklist for verifying that queries are indexed for the access patterns the application actually uses, and that the plan matches intent before the query ships.

## When to use it

Every time you write or review a query that touches a table with meaningful data volume — not just for "slow" queries. The discipline should be automatic.

## Checklist

- **Index for the queries you actually run.** Add indexes based on measured access patterns, not speculation. Every index has a write cost; don't index a pattern nothing executes.
- **Verify with `EXPLAIN`.** Confirm the plan uses the index you expect, not a full-table scan. If the plan doesn't match intent, the query isn't done.
- **Watch for N+1.** A loop that issues one query per row is the most common performance defect in application code. Batch the fetch or join instead.
- **Test with realistic data.** Profile against data volume and distribution that resembles production, not a handful of rows. A plan that's fine on 100 rows can be catastrophic on 10 million.
- **Check the write path too.** Inserts/updates that touch many rows, or that fight an index, are as important as read performance. Batch writes where the pattern allows.
- **Flag full-table scans in review.** A scan on a hot table is a review finding, even if it's "fast enough" today — it won't stay that way.

## Expected output

Queries that are verified against a realistic plan (via `EXPLAIN`), indexed for the access patterns the application actually executes, and free of N+1 and full-table-scan surprises — with the performance work treated as part of the change, not a follow-up.