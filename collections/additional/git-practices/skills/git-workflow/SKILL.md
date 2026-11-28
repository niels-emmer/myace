---
name: Git Workflow Discipline
description: Branching, commit, and staging conventions that keep history readable, reviewable, and safe to share.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [git, workflow, branching, commits]
---
## Purpose

This is the team-repository workflow. If the Vibecoder base pack's lighter `Git Workflow` skill is also in the setup, use that one only for solo prototype branches and this one for anything shared.


Git history is shared documentation. Every branch name, commit message, and staged hunk is read later by a reviewer, a teammate, or your future self. This skill keeps that record small, honest, and easy to reverse — without turning every change into ceremony.

## When to use it

Any time you start new work, stage a change, write a commit, or prepare a pull request.

## Branch naming

Work on a branch, never directly on the default branch. Use a short type prefix, then a description:

- `feat/<short-description>` — new functionality
- `fix/<short-description>` — bug fixes
- `chore/<short-description>` — tooling, dependencies, CI, cleanup
- `docs/<short-description>` — documentation only
- `release/<version>` — release preparation (maintainers)

Keep the name short enough to read in a shell prompt. If a change spans several types, pick the one that best describes the user-visible effect.

## Commit messages

Use a conventional form so the log is scannable:

```
<type>(<scope>): <imperative summary>

<body — why this change exists, wrapped at ~72 chars>

<footer — references, breaking changes>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`, `security`.

Rules:

- Summary in the imperative mood, no trailing period, roughly 50 characters.
- The body explains **why**, not what — the diff already shows what changed.
- Reference issues in the footer, e.g. `Refs: #42` or `Closes: #117`.
- Mark breaking changes with `BREAKING CHANGE: <description>`.
- One concern per commit. Do not bundle unrelated changes.

Example:

```
fix(auth): reject expired password-reset tokens

The reset endpoint accepted tokens past their expiry because the
comparison used the issue time instead of the expiry. This let a
leaked link stay valid indefinitely.

Refs: #318
```

## Staging discipline

- Stage deliberately with `git add -p`; stage only hunks that belong to this change.
- Run `git diff --cached` before committing and confirm the staged content is what you intend.
- Run the formatter/linter before staging when the project has one, so formatting noise never hides a real diff.
- Keep generated files and dependency directories out of the commit.

## What never belongs in a commit

- Secrets, API keys, tokens, passwords, or connection strings.
- `.env` files or machine-local config overrides.
- Commented-out dead code — delete it instead.
- Debug leftovers such as `console.log`, `print()`, or `debugger`.
- Build output, caches, or vendored dependencies unless the project explicitly commits them.
- Large binaries unless they are a deliberate, reviewed asset.
- Editor or IDE state directories.

## Before opening a pull request

- [ ] The branch name follows the convention.
- [ ] Commits are atomic and messages explain intent.
- [ ] No secrets, debug artifacts, or generated files are staged.
- [ ] Lint and tests pass locally where runnable.
- [ ] The diff contains only the intended change.
- [ ] New configuration variables are documented in the example env file.
- [ ] Breaking changes are called out in the commit footer and PR body.

## Working with shared branches

- Never force-push a shared branch or a branch with an open pull request.
- Rebase your feature branch onto the latest default branch before opening the PR.
- Resolve merge conflicts locally and verify the result still builds.
- Prefer `git pull --rebase` to avoid unnecessary merge commits on local work.

## Expected output

A well-named branch, a small set of focused commits with recoverable intent, and a pull request whose diff a reviewer can trust without reverse-engineering it.
