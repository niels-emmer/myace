---
name: README Structure
description: A solid default README shape (what it is, quickstart, key commands, where to find more) and guidance on when a project has outgrown a single README.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [documentation, readme, structure]
---

## Purpose

A README is usually the first (and sometimes only) doc a new contributor or user reads. Use this skill when creating a new README from scratch, restructuring one that's grown unwieldy, or deciding whether new content belongs in the README or needs its own page.

## When to use it

- Starting a new project or package that doesn't have a README yet.
- A README has become long enough that readers are visibly skipping sections or asking questions the README already answers (a sign of structure, not content, failure).
- Deciding where a new piece of documentation belongs — extend the README, or start a docs/ page.

## Default README shape

1. **What it is** — one or two sentences: what the project does and who it's for. No setup instructions yet, no history, just the summary a stranger needs before deciding to keep reading.
2. **Quickstart** — the shortest path from "nothing installed" to "it's running." Concrete, copy-pasteable commands, not a description of the steps. If there are prerequisites, list them right before the commands that need them, not in a separate section the reader has to hunt for.
3. **Key commands** — the small set of commands a working contributor actually uses day to day (run tests, run the linter, start the dev server, build). Not an exhaustive CLI reference — link out to that if it exists.
4. **Where to find more** — links to deeper docs: architecture notes, contribution guidelines, the agent-facing instruction file if there is one, API references. This section is what makes it safe to keep the README itself short.

Optional sections (license, badges, changelog link) go after this core, not before it — nothing should push the quickstart below the fold.

## When a project needs more than a README

A single README stops being the right shape when any of these are true:
- The quickstart section can no longer stay short because there are genuinely multiple setup paths (e.g. different platforms, different deployment targets) that each need real explanation.
- There's enough architectural or design-rationale content that inlining it would bury the quickstart — this belongs in a docs/ directory or dedicated architecture doc, linked from the README.
- Contribution process, coding standards, or review requirements have grown past a few bullet points — split into CONTRIBUTING.md and link it.
- Multiple audiences need fundamentally different entry points (end users vs. plugin authors vs. core contributors) — consider a docs/ directory with per-audience landing pages instead of one README trying to serve everyone.

When splitting content out, leave a short pointer in the README rather than removing all trace of the topic — a reader scanning the README should still learn that deeper docs on that topic exist and where to find them.

## Expected output

When applying this skill, either produce a README following the shape above (with real, verified commands — not placeholders) or, for a review, a short assessment of which section is missing, misplaced, or overgrown, with a concrete suggestion for fixing the structure.
