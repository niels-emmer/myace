---
description: Turn a short feature request into a written spec — user-facing behavior and testable acceptance criteria, deliberately free of implementation detail — before any planning starts.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
---
1. Restate the request as a short slug (`kebab-case`, e.g. `sso-login`) and create `docs/specs/<slug>/spec.md`.
2. Write the spec in terms a non-technical stakeholder could review: user stories ("As a ..., I want ..., so that ..."), functional requirements, and explicit out-of-scope items. Say nothing about frameworks, data models, or file structure here — that's `sdd-plan`'s job, not this one.
3. Write acceptance criteria as testable statements, not adjectives — "the export completes within 30s for a 10k-row account" is testable; "the export is fast" is not.
4. Where the request is genuinely ambiguous, don't guess silently and don't stall on every open question — make the reasonable, industry-standard assumption and note it, and only mark the ones that actually change scope, data ownership, or security posture as `[NEEDS CLARIFICATION: ...]`. Cap it at the handful that matter; a spec with twenty clarification markers wasn't specified, it was punted.
5. List edge cases explicitly (empty states, concurrent access, partial failure) — a spec that only describes the happy path will produce a plan and task list that only covers the happy path.
6. Read the project constitution (`docs/constitution.md`, if `sdd-constitution` has been run) and flag anything in the request that appears to conflict with a listed principle, rather than silently specifying around it.
7. Report the spec's location and a one-line summary of what's still marked `[NEEDS CLARIFICATION]`. If there are any, the next step is `sdd-clarify`, not `sdd-plan`.
