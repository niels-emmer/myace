---
name: Agent Instruction Drift Check
description: Procedure for comparing an agent-facing instruction doc (AGENTS.md/CLAUDE.md-style) against the actual current code and configuration to find and flag mismatches.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [documentation, drift, review, agents-md]
---

## Purpose

Agent-facing instruction files (AGENTS.md, CLAUDE.md, or similar) are read by coding agents at the start of a task, not exercised by tests or compilers — nothing forces them to stay correct when the code changes underneath them. A stale instruction file actively misleads whichever agent reads it next: it can point at a command that no longer exists, describe a directory layout that moved, or state a rule the codebase no longer follows. Use this skill periodically, before a release, or whenever you suspect an instruction doc has gone stale.

## When to use it

- Before cutting a release, as part of a documentation pass.
- After a significant refactor, migration, or dependency upgrade that could have invalidated commands or paths described in the doc.
- When an agent visibly acts on a rule that turns out to be wrong or outdated — that's a signal to check the whole doc, not just the one rule.
- On a regular cadence (e.g. monthly) for actively-developed projects, even with no specific trigger.

## Procedure

1. **Inventory the doc's claims.** Read through the instruction file section by section and list every concrete, checkable claim: commands, file paths, directory structures, described behaviors, architectural statements, named tools or dependencies.
2. **Verify each claim against the real thing**, not against memory or the doc's own earlier version:
   - Commands: actually run them (or confirm they exist in package.json/Makefile/pyproject.toml/etc.) with the flags the doc shows.
   - File paths: confirm the file or directory still exists at that path.
   - Described behavior: read the current implementation and confirm it still does what's described.
   - Named tools/dependencies: confirm they're still in use (check the dependency manifest) rather than replaced or removed.
3. **Classify each finding**:
   - *Broken* — command/path no longer exists, will fail if followed.
   - *Stale* — still technically works but describes old behavior, defaults, or structure.
   - *Unclear* — doesn't contradict the code but wouldn't be enough for a reader who wasn't there to act on correctly.
   - *Accurate* — confirmed correct, no action needed.
4. **Propose a specific fix for each Broken or Stale finding** — the corrected command, path, or description — rather than just flagging that something's wrong.
5. **Check for cross-doc duplication while you're in there.** If the same fact also appears in a human-facing doc (README, docs/), confirm both were checked and both get the same fix — don't correct one copy and leave the other stale.

## Expected output

A findings list grouped by classification (Broken / Stale / Unclear / Accurate), each with the specific location in the doc, what's wrong, and a concrete suggested correction. End with a one-line overall verdict: doc is current, doc needs the listed fixes, or doc needs a broader rewrite because drift has compounded past small fixes.
