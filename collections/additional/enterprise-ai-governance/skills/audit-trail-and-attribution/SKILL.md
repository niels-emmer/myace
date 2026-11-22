---
name: Audit Trail and Attribution
description: Record what changed, why, and whether it was AI- or human-authored, with per-session records and explicit commit and PR conventions.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [governance, audit, attribution, provenance, commits]
---
## Purpose

When agents make changes, "who did this and why" stops being obvious. An audit
trail answers three questions for every change — **what** changed, **why**, and
**whether a human or an AI produced it** — so reviewers can weigh it and future
maintainers can reconstruct intent.

## When to use it

On every unit of work that changes shared state: a commit, a pull request, a
deployment, a configuration change, or a decision with lasting consequences.

## What every record contains

- **What changed** — files, services, or data, grouped by intent.
- **Why** — the problem or request that motivated it.
- **Authorship** — AI-authored, human-authored, or AI-assisted and human-reviewed.
- **Evidence** — the commands run and their results.
- **Time and scope** — when it happened and what it deliberately excluded.

## Per-session record

Keep a short running record for the session, and persist it where the project
keeps its notes:

```
## Session record — <date>
- Task: <goal>
- Authorship: AI-authored / human-authored / AI-assisted
- Changes: <files and intent>
- Commands run: <verification commands and results>
- Decisions: <links to decision-log entries>
- Deferred / excluded: <known gaps>
```

A session record is not a substitute for commit history; it captures context
that does not fit in a diff.

## Commit conventions

- Use conventional commits (`<type>(<scope>): <summary>`).
- Mark AI-authored commits with an `[ai]` marker in the body, and record the
  model or tool when the project tracks it.
- Mark AI-assisted, human-reviewed work as reviewed, not as fully human-authored.
- Never attribute a human reviewer's approval as authorship.
- One logical change per commit, so attribution stays accurate.

Example body:

```
[ai] Generated with an AI coding agent; human-reviewed before merge.

Refs: #412
```

## Pull-request conventions

- Summary of what changed and why.
- Tests run, with results.
- Risks and known limitations.
- An attribution line stating whether the change was AI-authored, AI-assisted,
  or human-authored.
- A link to the originating issue or decision record.

## Decisions and immutability

- Record expensive-to-reverse decisions in the decision log, not only in chat.
- Treat the trail as append-only: correct a record with a follow-up entry rather
  than rewriting history.
- Never put secrets, credentials, or regulated data in an audit record.
- Retain records according to the project's policy; if none exists, keep them
  with the change they describe.

## Output format

```
## Audit entry
- Change: <what>
- Why: <motivation>
- Authorship: ai-authored / human-authored / ai-assisted (reviewed)
- Evidence: <commands and results>
- Decisions: <links or none>
- Gaps: <deferred or unverified>
```
