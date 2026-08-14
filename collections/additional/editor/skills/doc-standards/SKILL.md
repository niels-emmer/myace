---
name: Documentation Standards
description: Structure, tone, and formatting conventions for writing technical docs that stay accurate and get actually read.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [documentation, writing, style]
---

## Purpose

Give any doc you write or edit a consistent shape so readers (and agents) can scan it, trust it, and find what they need without re-deriving your conventions each time. Use this whenever you're writing a README section, a docs/ page, an agent-facing instruction file (AGENTS.md/CLAUDE.md-style), or reviewing someone else's doc for structural issues.

## When to use it

- Writing a new doc section or page from scratch.
- Reviewing an existing doc for structure, not just factual accuracy (pair with the drift-check skill for accuracy).
- Deciding whether new content belongs in an existing doc or needs its own page.

## Conventions

### Structure
- Lead with what the thing is and why it exists before diving into how to use it. A reader deciding whether to keep reading needs that in the first sentence or two.
- Use headings that describe content, not narrate process ("Configuration" not "How We Set This Up"). Keep heading depth shallow — two or three levels is almost always enough.
- Put the most commonly needed information first (quickstart, common commands) and push edge cases, advanced options, and rationale further down or into a linked doc.

### Examples
- Every non-trivial command or API shown should be a working, copy-pasteable example, not pseudocode. If you can't verify it runs, say so explicitly rather than presenting it as tested.
- Show the expected output or result when it's not obvious, especially for CLI commands and API calls — readers verify they did it right by comparing output, not by re-reading the instructions.

### Language
- Avoid unexplained jargon and internal shorthand. If a term is project-specific (a service name, an internal abbreviation), define it on first use or link to where it's defined.
- Avoid references that assume shared context the reader doesn't have — no "as discussed," "the fix from before," or ticket/PR numbers without enough surrounding explanation to be useful standalone.
- Prefer active voice and direct imperatives for instructions ("Run X," not "X should be run").

### Keep both audiences in sync
- A behavior or config change usually has two doc surfaces: human-facing docs (README, docs/) and agent-facing instruction files (AGENTS.md, CLAUDE.md-style). Update both in the same change when the change affects both — don't let one lag.
- If a fact is genuinely shared between the two (e.g. a setup command), write it once in whichever doc is more canonical for that audience and link the other to it, rather than maintaining two copies.

## Expected output

When applying this skill to a review, produce a short list of structural issues (heading depth, missing examples, unexplained jargon, misplaced content) each paired with a concrete suggested fix — not a rewritten doc unless asked to write one directly.
