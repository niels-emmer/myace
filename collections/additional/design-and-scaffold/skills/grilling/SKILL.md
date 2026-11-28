---
name: Design Grilling
description: Interview the user through a design tree until a plan is fully understood before any code is written.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [design, planning, requirements, interview]
---
## Purpose

Most rework comes from building against an unstated assumption. Design grilling
forces the assumptions into the open before implementation: turn the problem
into a tree of decisions, ask the questions that are answerable now, and keep
going until every branch has been settled or consciously accepted.

## When to use it

Before starting a feature that is under-specified, hard to reverse, or likely
to have more than one reasonable shape — a new data model, a new public
interface, an auth or deletion flow, a migration, or an ambiguous request.

## The design tree

Map the problem as a **design tree**: each decision branches into the decisions
that depend on it. Work the tree in **rounds**. The **frontier** is every
decision whose prerequisites are already settled — the questions you can ask
now without guessing at answers you have not heard.

Ask the whole frontier in one round. Number each question and give your
recommended answer, phrased so that "yes" accepts it.

```
Q1 — <question title>: <question body, including the options you see>

  Recommended: <your answer and a one-line reason>

Q2 — <question title>: <question body>

  Recommended: <your answer and a one-line reason>
```

Then wait for the answers before the next round. A question whose answer
depends on another question still open in this round belongs to a later round,
not this one.

## Facts are yours, decisions are the user's

Look up facts yourself — read the code, check the schema, inspect the API, or
delegate a focused research pass. Never ask the user for something you can
verify. Only decisions go to the user. Do not block the whole round on a fact
lookup: a running research task is an unsettled prerequisite, so only the
questions downstream of it wait; ask the rest of the frontier now.

## What good questions look like

- Bounded: one decision per question, with concrete options.
- Consequence-aware: name the trade-off each option makes.
- Example-driven for this role: "Should the export include soft-deleted rows?"
  is better than "What are the requirements?"
- Free of invented constraints: confirm a limit before designing around it.

## Done

The session is done when the frontier is empty: every branch of the design
tree has been visited and nothing is silently assumed. Summarize the settled
decisions, then confirm with the user that you share the same understanding
before writing any code.

## Expected output

A short record of the decisions taken, the options rejected, and the open
questions the user explicitly deferred — enough that implementation can start
without re-litigating the design.
