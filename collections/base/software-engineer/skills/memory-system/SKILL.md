---
name: Memory System
description: Maintain a tiered, file-based memory system so project context and decisions survive across sessions instead of being rediscovered or contradicted each time.
version: "1.0.0"
priority: 60
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [memory, process, documentation]
---
## Purpose

A coding agent's context resets between sessions. Without a durable place to record decisions, conventions, and the reasoning behind them, every new session either re-derives context from scratch (slow, and prone to contradicting earlier decisions) or plows ahead without it (fast, and prone to redoing work or reversing a decision nobody remembers making). This skill defines a small, low-overhead file layout that fixes that, and the routine for keeping it current.

## When to use it

At the start of every nontrivial task, before touching code. At the end of every nontrivial task, before considering it done. "Nontrivial" means: it involved a design or approach decision, it changed behavior a future session would need to know about, or it took more than a few minutes of back-and-forth to get right. A one-line typo fix doesn't need a memory update; a new feature, an architecture change, or a fix for a subtle bug does.

## File layout

Create these under `docs/memory/` in the project root the first time this skill is used on a project that doesn't have them yet:

- **`docs/memory/core-principles.md`** — the stable layer. Architectural decisions and constraints that rarely change: the chosen stack, non-negotiable invariants, things that would require a real conversation to reverse. Keep this short — if it's growing every week, content belongs in one of the other files instead.
- **`docs/memory/workflow.md`** — the process layer. How this specific team/project actually works day to day: branching conventions, how releases happen, where things like migrations or config live, anything a new session needs to act consistently with existing practice. Changes more often than core-principles but still infrequently.
- **`docs/memory/decisions.md`** — the evidence/decision log. Append-only. Every nontrivial task adds one dated entry here. Never edit or delete a past entry to "clean it up" — if a decision was later reversed, add a new entry noting the reversal and why; the history is the point.

## Startup routine (mandatory)

Before starting any nontrivial task:
1. Read `docs/memory/core-principles.md` and `docs/memory/workflow.md` in full — they're meant to stay short enough that this is cheap.
2. Skim the tail of `docs/memory/decisions.md` for anything relevant to the area you're about to touch (grep for the module/feature name if the log has gotten long).
3. If any of these files don't exist yet, that's fine — proceed, and create them as part of the update protocol below when the task completes.

## Update protocol (end of task)

Append to `docs/memory/decisions.md` an entry containing, at minimum:
- **What was decided** — the approach taken and, briefly, the alternative(s) considered and why they were passed over.
- **How it was tested** — what was actually run to confirm the change works (see the `test-patterns` skill), not just "added tests."
- **What documentation was touched** — which files were updated to reflect this change.

If the task changed something in the stable or process layer (a new architectural constraint, a changed convention), update `core-principles.md` or `workflow.md` directly rather than only logging it in the decision log — the decision log records that the change happened; the stable/process files are what future sessions actually read by default.

## Definition of done

A task is not complete until the decision log entry exists and accurately reflects what was actually done — not what was planned. A stale or missing entry is a real defect, not a nice-to-have: it's the exact failure mode this system exists to prevent. If you're tempted to skip the update because the task felt small, apply the "nontrivial" test above rather than skipping by default.
