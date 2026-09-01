---
description: The standard pre-merge verification checklist for infrastructure changes — plan/validate/lint/policy checks, tests, security pass, rollback path, and documentation, all confirmed before a change is considered done.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
---
1. Run `plan`/`validate`, format/lint, and policy-as-code checks and confirm an actual pass — quote the real output, don't summarize a run you didn't just do.
2. Read the plan output and confirm it matches the intended change — no resources created or destroyed that the task didn't ask for.
3. Confirm the change added or updated tests that cover it (pipeline unit tests, deployment integration/smoke tests), checked against the `test-patterns` skill's checklist — not just that some test somewhere still passes.
4. Run the linter and type checker; both must be clean. A warning that's routinely ignored project-wide is a judgment call to note explicitly, not to silently pass over.
5. If the change touches identity, secrets, network exposure, data, images, or dependencies, run it through the `devsecops-checklist` skill and resolve every FAIL before continuing — don't defer a blocking finding to "a follow-up."
6. If the change includes a state migration or a change to a shared/critical path, confirm the rollback path has actually been exercised, not just written.
7. Confirm documentation and runbooks — README, AGENTS.md-style rule files, inline comments describing now-stale behavior — have been updated to match the change, in this same change set.
8. Append the decision-log entry per the `memory-system` skill: what was decided, how it was tested (point at the specific runs from steps 1-4), and which docs were touched.
9. Only report the change as done once every applicable step above is actually true — not once the code compiles, and not once "most of it" is finished.