---
name: Git Workflow
description: Lightweight branch naming and pull-request-vs-direct-push guidance for fast solo/small-team iteration.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [git, workflow]
---
## Purpose

Keep git usage simple enough that it never gets in the way of moving fast, while still leaving a clean, readable history and a clear signal for when something needs a second look.

## When to use it

Any time you're starting new work, deciding whether to branch, or deciding whether a change needs a pull request versus just landing directly.

## Branch naming

Use a short prefix that says what kind of change it is, then a few words describing it, separated by hyphens:

- `feat/short-description` — new functionality
- `fix/short-description` — bug fix
- `chore/short-description` — maintenance, deps, config, cleanup
- `docs/short-description` — documentation only

Keep the branch name short enough to read in a terminal prompt. If the work doesn't fit cleanly into one of these, `feat/` is a safe default.

## Commit messages

Write each commit as a small, coherent unit with a message that states what changed and why. Use a conventional prefix so the history is scannable:

- `feat:` — new functionality
- `fix:` — bug fix
- `chore:` — maintenance, deps, config, cleanup
- `docs:` — documentation only

Keep the subject under ~50 characters and imperative ("add retry to the fetch", not "added retry"). If the "why" isn't obvious from the diff, add a short body paragraph — the message should make the intent recoverable later, not just describe the diff.

## When to open a PR vs. just push

For solo or low-stakes prototype work on your own feature branch, it's fine to push directly and merge without ceremony — a PR that nobody else will read doesn't add safety, it just adds a click.

Open a real pull request (even solo) when:
- The change touches shared/production infrastructure, data migrations, or anything hard to undo.
- You want a second pass before it lands — e.g. you're not fully confident in the approach.
- Other people are working in the same repo and need visibility before it merges.
- The default/main branch is protected and requires one anyway.

Otherwise, commit on the feature branch and merge or push straight to the target branch once it works.

## PR description

When you do open a PR, write a short description covering what changed and why, how it was tested, and anything a reviewer should pay attention to. A reviewer shouldn't have to reverse-engineer the intent from the diff.

## Checklist before pushing

1. Does the code run, and did you actually run it (not just read it)?
2. Is the diff limited to what the task needed — no stray unrelated changes?
3. Are commit messages clear enough that "why" is recoverable later?
4. Nothing secret (keys, tokens, `.env` contents) in the diff?

## Expected output

A branch named per the convention above, a small number of clean commits, and either a direct push/merge (low-stakes) or an opened PR with a short description of what changed and why (higher-stakes).
