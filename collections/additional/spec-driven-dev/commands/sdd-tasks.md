---
description: Turn a plan into an ordered, independently-checkable task list, with every task traceable back to a requirement and every requirement covered by at least one task.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
---
1. Read `docs/specs/<slug>/spec.md` and `docs/specs/<slug>/plan.md`.
2. Group tasks by independently-shippable increment — usually one per user story from the spec — rather than by technical layer, so each group is a coherent, demoable slice rather than "all the backend work" followed by "all the frontend work."
3. Break each increment into concrete, checkable steps small enough to verify on their own (a migration, an endpoint, a test for a specific edge case) — not vague phases. This mirrors the base `plan` command's step-sizing rule; apply it per-increment here.
4. Mark tasks that can run in parallel (no shared file, no dependency on another unfinished task) so `sdd-implement` — or a human — knows what can be batched.
5. Verify coverage both directions: every functional requirement and edge case in the spec maps to at least one task, and every task traces back to a requirement in the spec or a supporting need from the plan (data model setup, a new dependency). A task with no requirement behind it is scope creep; a requirement with no task is a gap that will surface as a missed feature later.
6. Write the ordered, grouped list to `docs/specs/<slug>/tasks.md`.
7. Recommend running `sdd-analyze` before `sdd-implement` if the spec or plan went through more than one round of changes — the more a design shifts, the more likely spec/plan/tasks have quietly drifted out of sync with each other.
