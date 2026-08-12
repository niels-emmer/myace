---
description: The standard pre-merge verification checklist — tests, lint, security pass, and documentation, all confirmed before a change is considered done.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
---
1. Run the full relevant test suite and confirm an actual pass — quote the real result (counts, or the specific failing tests), don't summarize a run you didn't just do.
2. Confirm the change added or updated tests that cover it, checked against the `test-patterns` skill's checklist (edge cases and failure modes, not only the happy path) — not just that some test somewhere still passes.
3. Run the linter and type checker; both must be clean. A warning that's routinely ignored project-wide is a judgment call to note explicitly, not to silently pass over.
4. Run the build (or equivalent — compile step, package build) and confirm it succeeds.
5. If the change touches input handling, auth, data access, secrets, or external calls, run it through the `security-checklist` skill and resolve every FAIL before continuing — don't defer a blocking finding to "a follow-up."
6. If the change includes a schema or data migration, confirm the rollback path has actually been exercised, not just written.
7. Confirm documentation — README, AGENTS.md-style rule files, inline comments describing now-stale behavior — has been updated to match the change, in this same change set.
8. Append the decision-log entry per the `memory-system` skill: what was decided, how it was tested (point at the specific runs from steps 1-4), and which docs were touched.
9. Only report the change as done once every applicable step above is actually true — not once the code compiles, and not once "most of it" is finished.
