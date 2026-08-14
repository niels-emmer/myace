---
description: Produce a short written plan before implementing anything nontrivial, so the approach is explicit before code starts.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
---
1. Restate the task in one or two sentences, in your own words — confirms you've understood what's actually being asked before designing around a misreading of it.
2. Read the project's memory files (`docs/memory/core-principles.md`, `docs/memory/workflow.md`, and the tail of `docs/memory/decisions.md` for anything relevant) so the plan fits existing conventions and doesn't repeat a decision already made and logged.
3. Decide whether this task needs the `architecture-review` skill's design pass — a new data model, a new service boundary, an auth/security-relevant change, or a genuinely ambiguous approach all qualify. If it does, write the short design note that skill describes before continuing.
4. Break the task into an ordered list of concrete, checkable steps — not vague phases. Each step should be small enough to verify on its own (e.g., "add the migration," "update the query to filter by owner," "add the denial-path test," not "implement the feature").
5. Identify what could go wrong or turn out to be bigger than expected — a step that touches a shared/critical path, a migration without an obvious rollback, a security-relevant boundary — and flag those specifically rather than letting them look like routine steps.
6. Set up tracking for the plan per the `plan-tracking` skill so progress stays visible as steps complete.
7. Share the plan before starting implementation if the task is large, ambiguous, or touches something risky enough that the user would want a chance to redirect before code gets written; otherwise proceed straight into the `builder` agent's work with the plan as the checklist.
