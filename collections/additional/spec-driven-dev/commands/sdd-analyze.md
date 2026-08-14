---
description: Read-only cross-check of spec, plan, and tasks for consistency, duplication, gaps, and constitution violations before implementation starts.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
---
1. Read `spec.md`, `plan.md`, and `tasks.md` for the target feature, plus `docs/constitution.md` if it exists. This is a read-only pass — report findings, don't edit any of the three documents yourself.
2. Check for: requirements with no corresponding task (gaps), tasks with no corresponding requirement (scope creep), the same requirement covered by contradictory tasks (duplication/conflict), vague or placeholder language left unresolved (`TBD`, `[NEEDS CLARIFICATION]` markers that survived past `sdd-clarify`), and terminology drift (the same concept named differently across the three documents).
3. Check the plan and tasks against every constitution principle explicitly. A violation of a stated MUST principle is always a blocking finding — flag it as such even if fixing it means reopening `sdd-plan`, rather than letting an inconsistency ride because a task list already exists.
4. Rate each finding CRITICAL (constitution violation or a gap that would ship broken behavior), HIGH (contradiction or major ambiguity), MEDIUM (drift or minor gap), or LOW (cosmetic/terminology). Cap the report at the findings that actually matter — a 50-item nitpick list buries the three that block implementation.
5. For each finding, name the specific documents and sections involved and suggest a concrete fix — don't just flag "inconsistency between plan and tasks" without saying what's inconsistent.
6. Produce a summary table: requirement coverage (mapped / gap), finding count by severity, and a clear go/no-go recommendation for `sdd-implement`.
7. If any CRITICAL findings exist, recommend against starting `sdd-implement` until they're resolved via the relevant upstream command (`sdd-specify`, `sdd-clarify`, or `sdd-plan`) — don't let implementation start against a design known to be broken.
