---
name: Plan Tracking
description: Keep a running, visible record of task/plan state across a multi-step session so nothing silently gets dropped or forgotten.
version: "1.0.0"
priority: 45
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [planning, process, session-management]
---
## Purpose

A multi-step task loses steps when its plan only exists in working memory — a subtask gets implicitly dropped, a "come back to this" note never gets revisited, or the scope quietly drifts without anyone noticing it drifted. Writing the plan down, and updating it as steps complete, makes progress and remaining work visible to the user and to any agent picking the task back up.

## When to use it

Any task that will take more than roughly 3 sequential steps, spans multiple files or subsystems, or is likely to be interrupted and resumed. Not needed for a single, self-contained edit — the overhead isn't worth it for something that's done in one pass.

## Steps / checklist

1. **Write the plan before starting**, as a short ordered list of concrete steps — not vague phases like "implement the feature" but specific, checkable actions ("add the `visibility` column + migration", "update `authorize_access` to check it", "add tests for the new denial case"). If the environment has a structured todo/plan tool, use it; otherwise a plain markdown checklist in the working notes is fine.
2. **Keep exactly one step marked in-progress at a time.** This makes it obvious, at a glance, what's actually being worked on right now versus what's queued.
3. **Update state as you go, not in a batch at the end.** Mark a step complete the moment it's actually done (built, run, confirmed) — not before, and not deferred until a later "cleanup the tracking" pass that may not happen.
4. **Surface scope changes explicitly.** If a step turns out to need sub-steps that weren't in the original plan, add them to the visible plan rather than silently expanding scope and hoping it's fine.
5. **Never mark a step done that isn't.** A step is complete when it's actually been verified to work, not when the code for it has been written. Marking things done prematurely defeats the entire purpose of tracking — it becomes a list that can't be trusted.
6. **On handoff or session end, leave the plan in a state a fresh reader can act on** — what's done, what's in progress, what's still pending, and any blocker that's stalling progress. Pair this with the `memory-system` skill's decision log if the session is ending and the task isn't finished.

## Expected output

A plan artifact (todo list, tracked checklist, or equivalent) that stays accurate throughout the task — at any point, a reader should be able to tell what's done, what's next, and what's blocked without asking. The value is entirely in it being trustworthy; a stale or optimistic plan is worse than no plan because it creates false confidence about how much is actually finished.
