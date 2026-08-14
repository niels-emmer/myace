---
description: Systematically find and resolve the highest-impact ambiguities in a spec before planning starts, instead of discovering them mid-implementation.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
---
1. Read the target `docs/specs/<slug>/spec.md`.
2. Check it against these categories for gaps, not just the markers already flagged: functional scope boundaries, data model and ownership, UX/error-state flows, non-functional constraints (performance, scale, availability), external integrations, edge cases, explicit exclusions, terminology consistency, and what "done" means. A spec can look complete and still be silently missing one of these.
3. Rank every open question — flagged or newly found — by how much it would change the plan if answered differently. Keep only the top five; lower-impact ones get a reasonable default noted in the spec instead of a question.
4. Ask one question at a time, each answerable in a short phrase or a multiple-choice pick, with your own recommended answer stated up front so the user is confirming or correcting, not starting from a blank page.
5. After each answer, immediately write it into the relevant spec section (not a separate changelog) and remove the corresponding `[NEEDS CLARIFICATION]` marker — don't batch edits until the end, since a session that gets cut short should still leave the spec more resolved than it started.
6. Stop once every top-five question is resolved or explicitly deferred with a stated default. Don't manufacture additional questions to seem thorough.
7. Report the updated spec's remaining open items, if any, and state plainly whether it's ready for `sdd-plan`.
