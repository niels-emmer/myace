---
name: Commit Format
description: A simple Conventional Commits style for clear, scannable commit history.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [git, commits]
---
## Purpose

Give every commit a consistent, scannable shape so `git log` stays readable without requiring a full commit-message ceremony.

## When to use it

Every time you make a commit. This applies whether you're committing after every small step or batching a few related changes together.

## Format

```
<type>: <short imperative summary>

<optional body — the "why", if it's not obvious from the summary>
```

Common types:
- `feat:` — new user-facing functionality
- `fix:` — bug fix
- `chore:` — dependency bumps, config, tooling, cleanup with no behavior change
- `docs:` — documentation only

Keep the summary line imperative ("add retry logic", not "added" or "adds") and short — aim for under ~65 characters so it doesn't wrap in most git tools. If the change needs more explanation than that, put it in the body as a sentence or two, not the summary.

## Guidelines

- One logical change per commit where practical — makes it easy to revert just the part that turns out wrong.
- Don't bother with a body for genuinely self-explanatory commits ("fix: correct off-by-one in pagination" needs no further explanation).
- Do add a body when the "why" isn't obvious from the diff alone — e.g. working around a library bug, a deliberate tradeoff, or a non-obvious edge case being fixed.
- Avoid vague summaries like "update stuff" or "fixes" — they're useless six months later.

## Expected output

A commit message that reads clearly on its own in `git log --oneline`, with enough of a body (when needed) that someone skimming history later understands the reasoning without re-reading the diff.
