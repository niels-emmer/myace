---
description: Pre-commit gate — review the staged diff, scan for secrets, run lint and tests, and confirm the change is ready to commit.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
---
Run the pre-commit gate before committing. Do not commit if any gate fails.

1. **Review the diff** — `git status --short` and `git diff --cached` (or
   `git diff` when nothing is staged). Confirm the change matches the intended
   task and contains no unrelated edits.

2. **Scan for secrets** — check the diff for tokens, keys, passwords,
   connection strings, environment-file contents, and private addresses or
   credentials. Confirm no secret-bearing file is newly tracked (for example
   environment files, credential stores, private keys, or certificate
   bundles).

3. **Lint and format** — run the project's linter and formatter in check mode,
   using the command documented in the project's own contributing notes.

4. **Tests** — run the full suite, or the affected subset when the suite is
   slow. Report pass and fail counts.

5. **Commit message** — propose a conventional message
   (`<type>(<scope>): <summary>`). Add an AI-authorship marker in the body when
   the change was AI-authored.

6. **Report** — list which gates passed or failed and the exact next action.

## Rules

- A failed gate blocks the commit; report the failure instead of committing
  anyway.
- Never commit environment files, credentials, or generated secrets.
- Keep the commit scoped to one logical change.

## Output format

```
## Pre-commit gate
- Diff reviewed: yes / no
- Secrets: clean / FOUND <detail>
- Lint/format: passed / failed / n/a
- Tests: <n> passed, <n> failed
- Message: <proposed>
- Ready to commit: yes / no
```
