---
description: Execute a task list in dependency order, tests before implementation for each task, halting on any non-parallel failure instead of pressing ahead.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
---
1. Read `docs/specs/<slug>/tasks.md` and the underlying `spec.md`/`plan.md`. If `sdd-analyze` hasn't been run and the spec or plan changed after `sdd-tasks` was generated, run it first rather than implementing against a possibly-stale task list.
2. Work through tasks in the order and grouping `sdd-tasks` produced. Within a group, tasks marked parallel-safe may be done in any order; tasks with a stated dependency must wait for it.
3. For each task, write the test that would fail without the change first, then implement until it passes — the same discipline as the `test-patterns` skill, applied task-by-task rather than once at the end.
4. Mark each task complete in `tasks.md` as it finishes, so progress is visible and a resumed session picks up where the last one left off instead of re-deriving what's already done.
5. On a failure in a non-parallel task, stop and surface it rather than skipping ahead to unblocked-looking later tasks — a later task may implicitly depend on the failed one in a way `sdd-tasks` didn't capture explicitly.
6. Once every task is complete, hand off to the base `verify` command (if composed) for the full pre-merge check — this command's job is to execute the task list correctly, not to duplicate the project's whole test/lint/security/docs gate.
7. Report which tasks completed, which were skipped and why, and the spec's acceptance criteria status — don't report the feature done until every acceptance criterion in `spec.md` is demonstrably met, not just every task checked off.
