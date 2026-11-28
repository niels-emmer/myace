# Backend Specialist

## Validate At The Boundary

<!-- myace: priority=90 tags=backend,security -->

Treat all external input (request bodies, query params, headers, webhook payloads, uploads) as untrusted until validated at the edge. Validate shape, type, and business constraints before data enters internal code paths. Once validated, trust it — don't re-check the same invariant at every layer.

## Every Schema Change Needs A Working Rollback

<!-- myace: priority=70 tags=backend,database -->

Write and exercise `downgrade()` alongside `upgrade()`. Never edit applied/merged migrations — create a new forward migration instead. For large tables, prefer additive steps (add nullable → backfill → tighten) over single blocking changes.

## Design For Idempotency

<!-- myace: priority=70 tags=backend,reliability -->

Design all mutating endpoints to handle retries idempotently. Use idempotency keys, uniqueness constraints, or naturally idempotent operations (`set status = X` over `increment counter`). Document which mechanism applies.

## Fail Loud Internally, Fail Safe Externally

<!-- myace: priority=90 tags=backend,security -->

Return consistent, minimal errors to callers: stable error code, human-readable message, no internals (stack traces, DB errors, file paths). Internally, log the real exception with enough context to debug without reproducing live.

## Prefer DB Constraints Over App-Only Checks

<!-- myace: priority=70 tags=backend,database -->

Use database constraints (foreign keys, uniqueness, not-null, check) for invariants the DB can enforce. Application code handles business rules the DB can't express. Make soft-delete vs. hard-delete an explicit per-entity decision.
