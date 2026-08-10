# Backend Specialist

Rules for anyone building or changing APIs, services, and the schemas behind them. Layer this on top of a base rule set — it adds backend-specific discipline around boundaries, migrations, and failure handling, it doesn't replace general engineering judgment.

## Validate At The Boundary

Treat anything that crosses into your system from outside — request bodies, query params, path segments, headers, webhook payloads, uploaded files — as untrusted until it's been checked. Validate shape, type, and any business constraints (ranges, required combinations, referential existence) right at the edge, before the data enters your normal code paths, and reject with a clear error the moment something doesn't fit.

Once data has passed boundary validation and is flowing through internal function calls, trust it. Re-checking the same invariant at every internal layer ("just in case") adds noise without adding safety — it's redundant work that makes the real validation logic harder to find. If an internal function genuinely has a precondition an earlier layer can't guarantee, that's a sign the boundary check is incomplete; fix the boundary rather than sprinkling defensive checks deeper in.

## Every Schema Change Needs A Working Rollback

A migration isn't done when `upgrade()` runs — it's done when `downgrade()` has actually been exercised and reverses the change cleanly. Write and test the rollback path as part of the same change, not as an afterthought you'll get to if something breaks. A migration with a rollback that's untested (or a no-op stub) is a migration that will strand production the first time it needs to be reverted.

Never edit a migration file that's already been applied or merged, even to fix a typo — the deployed state and the file no longer agree once you do, and anyone who already ran it is now out of sync with anyone who runs the edited version. If a committed migration is wrong, add a new migration that corrects it forward.

Before shipping a migration, think about what it does to a large or heavily-written table at execution time: does it take a long-lived lock, rewrite the whole table, or block reads/writes for longer than the deployment can tolerate. A migration that's logically correct but locks a hot table for minutes is still an incident — prefer additive, backward-compatible steps (add nullable column → backfill → tighten constraint) over a single blocking change when the table is large enough for it to matter.

## Design For Idempotency

Assume every mutating endpoint that isn't purely internal will eventually get called twice with the same intent — a client retries after a timeout, a queue redelivers a message, a webhook fires more than once. Design so that a duplicate call produces the same end state as a single call, not a duplicate side effect (double charge, double row, double email).

The concrete mechanism depends on the operation: an idempotency key supplied by the caller and checked before executing, a natural uniqueness constraint that makes a repeat insert a no-op or a clean conflict, or an operation that's naturally idempotent by construction (`set status = X` rather than `increment counter`). Pick deliberately and document which one applies — don't leave it implicit and hope retries never happen.

## Fail Loud Internally, Fail Safe Externally

Callers of your API should get a consistent, minimal error: a stable error code or type, a human-readable message that doesn't assume they can see your code, and nothing that exposes internals — no stack traces, no raw database error text, no internal file paths or query fragments. Two different failures with the same external cause should look the same to the caller; don't let incidental implementation details (which layer happened to throw) leak into the response shape.

Internally, do the opposite: log the real exception, the relevant request context, and enough detail that you can actually debug the failure later without reproducing it live. A generic external error message paired with a genuinely useful internal log line is the goal — never trade away the internal detail for the sake of a clean external message, and never leak the internal detail outward for the sake of debugging convenience.

## Prefer DB Constraints Over App-Only Checks

Where the database can enforce an invariant — foreign keys, uniqueness, not-null, a check constraint — let it, rather than relying solely on application code to catch every path that writes to the table. Application-level validation is easy to bypass accidentally (a second endpoint, a background job, a one-off script, a future teammate who doesn't know the rule exists); a database constraint holds regardless of which code path writes the row.

This doesn't mean skip application-level validation — it means don't treat it as sufficient on its own for things the database can guarantee structurally. Application code is still the right place for business rules the database can't express (cross-table logic, conditional requirements, anything that needs a friendly error message before the query even runs).

Treat soft-delete versus hard-delete as a decision to make explicitly per entity, not a default to inherit from whatever the last table did. Soft-delete when you need audit history, undo, or referential integrity for records other rows still point to; hard-delete when the data has no future value and keeping it around is itself a liability (e.g. sensitive data past its retention window). Whichever you choose, make sure every read path (queries, indexes, uniqueness constraints) actually accounts for it — a unique constraint that doesn't exclude soft-deleted rows will block legitimate re-creation of a "deleted" record.
