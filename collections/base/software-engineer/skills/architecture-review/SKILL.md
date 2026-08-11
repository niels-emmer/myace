---
name: Architecture Review
description: When a design needs a second look before implementation starts, and what to actually evaluate when giving it one.
version: "1.0.0"
priority: 45
compatibility: [opencode, claude-code, cursor]
tags: [architecture, design, review]
---
## Purpose

Most changes don't need a design discussion — they need someone to write the code. A smaller set of changes are expensive to reverse once built (a new data model, a new service boundary, a new public API shape, a change to how auth or permissions are structured) and are worth a deliberate design pass before implementation starts, because the cost of redoing them after the fact is much higher than the cost of a short review up front.

## When a design needs review before building

Reach for this before writing code when a change involves any of:
- A new persistent data model or a change to an existing one that existing data has to migrate through.
- A new service boundary, API contract, or integration point other code will depend on.
- A change to how authentication, authorization, or a security boundary works.
- Introducing a new dependency or pattern that doesn't exist elsewhere in the codebase yet (the first use sets a precedent others will copy).
- Anything where two reasonable engineers would likely propose different approaches — that disagreement is a signal the choice matters.

Skip it for: a bug fix within existing structure, an addition that clearly follows an established pattern, or anything where the "design" is genuinely obvious once you read the ticket.

## What to evaluate

1. **Does this need to be general, or does it need to solve the actual problem?** Check against the rule of least power — the simplest structure that handles today's real requirement beats a flexible one built for requirements that don't exist yet. A generic plugin system for two known implementations is premature; a generic plugin system for one is almost certainly wrong.
2. **What's the blast radius if this is wrong?** A data model that's hard to migrate later deserves more scrutiny than a function whose callers can be updated in one commit if the shape changes.
3. **Does it fit how the rest of the system is structured**, or does it introduce a second way of doing something the codebase already does one way? A deliberate departure from an existing pattern should have a stated reason, not just be an accident of who wrote it.
4. **What's the failure mode**, not just the success path — what happens when this component is unavailable, slow, or returns something unexpected, and does the design account for that or silently assume it won't happen.
5. **Is the rollback path real?** For anything involving persisted data, can this be undone if it turns out to be wrong, or does shipping it lock in the decision.

## Expected output

For a change that warrants review, a short written note (a few sentences to a short paragraph, not a formal design doc) covering: the approach chosen, the main alternative considered and why it was passed over, and what happens in the primary failure mode. This is cheap to write and gives `code-reviewer` and `orchestrator` something concrete to evaluate against, rather than discovering the design rationale only by reverse-engineering the diff.
