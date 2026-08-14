---
description: Quick pre-ship checklist to run before pushing or merging a change.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
---
Run through this before pushing or merging any change, even a small one. It should take under a minute for a small diff.

1. **Run it.** Actually execute the code path you changed (run the app, run the relevant test, hit the endpoint) — don't rely on reading the diff and assuming it works.
2. **Glance at the full diff.** Check for stray unrelated edits, leftover debug prints/console logs, and commented-out code that shouldn't ship.
3. **Scan for secrets.** Make sure no API key, token, password, or `.env` content snuck into the diff. If anything looks like a credential, pull it out before continuing.
4. **Check the commit message.** Does it clearly say what changed and, if not obvious, why?
5. **Decide push vs. PR.** Low-stakes solo work on a feature branch: push/merge directly. Anything touching shared infra, production data, or something you're not fully confident about: open a PR instead (see the git-workflow skill).
6. **Confirm before `git push`** if it targets a shared or default branch, or before any destructive command — this is a deliberate pause point, not a step to skip.

If any step surfaces a real problem, fix it first and re-run the checklist — don't ship past a known issue.
