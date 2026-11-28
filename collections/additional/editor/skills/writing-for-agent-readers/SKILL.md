---
name: Writing For Agent Readers
description: How to write documents an agent executes — skills, AGENTS.md/CLAUDE.md lines, specs, tickets and runtime prompts — so it follows the same process every run instead of needing a longer document.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [documentation, agents-md, skills, prompting, writing]
---

## Purpose

A document an agent reads is not explanation, it is instructions. The reader has already read everything you have, so a line that explains what the model knows changes no behaviour while still spending context on every turn. This skill is the review pass for that class of document: delete what does nothing, name the concept the agent should think with, and make each step's done-condition demanding enough that the agent cannot stop early.

## When to use it

- Writing or editing a skill, an `AGENTS.md`/`CLAUDE.md` rule, a spec, a ticket, or a prompt that hands work to a fresh session.
- Reviewing a draft of any of those that came out longer than it needs to be.
- A document already exists but the agent misbehaves when it runs it — diagnose with the vocabulary below before adding more text.

Not for prose a human reads for pleasure or persuasion. Use the editorial skills for that; the tests here would strip material a human reader wants.

## The two loads

Every document and every pointer spends one of two budgets.

- **Context load** is what sits in the window on every turn whether or not it fires: an `AGENTS.md` line, a skill's description, anything always loaded. This is the one to minimise.
- **Cognitive load** is the cost to the human of remembering which document exists and when to reach for it. Do not minimise this one; it is the price of the human staying the index.

Most authoring arguments are this one trade in different clothes: split or not, inline or disclose, point or push.

## The levers

**Context pointers.** A pointer is the in-context line that names out-of-context material and says when to reach it. A skill description and an `AGENTS.md` line naming a doc are the same device. The pointer's wording decides whether the agent actually reaches for it; the target's quality is irrelevant if the pointer never fires. Write the pointer for the situation ("when a migration won't roll back"), not for the topic ("database stuff").

**Information hierarchy and progressive disclosure.** Three rungs: a step in the file, reference in the file, reference behind a pointer. Move material down the ladder whenever the top stays readable without it. A branch only one path needs belongs behind a pointer, so the other paths never pay for it.

**Completion criteria and legwork.** Each step needs a done-condition specific enough that the agent can tell it has not met it yet. Vague ones invite **premature completion** — the agent declares victory at the first plausible stopping point because nothing told it to keep going. Demand the checking work explicitly (run it, diff the output, re-read the file), rather than hoping the agent infers it.

**Leading words.** A compact word already loaded with the right associations in the model's training — *tight*, *red*, *tracer bullet*, *greenfield* — lets one token carry a paragraph of behaviour. It works twice: in the body it steers execution, in the pointer it triggers invocation. Prefer a strong existing word to a freshly coined phrase the model has to learn from your file.

**Pruning.** Apply the no-op test sentence by sentence: delete the line and ask whether the agent's behaviour changes. If not, it was a no-op, and it costs context on every run. When a sentence fails, delete the whole sentence rather than trimming words from it — trimming keeps the no-op.

## Diagnose with this vocabulary

Name the failure first, then fix that one:

- **Duplication** — the same fact stated twice in any form. The most reliable sign a document was never tested.
- **Sediment** — layers from earlier edits that nobody removed because removing them felt risky.
- **Sprawl** — material in the main file that belongs behind a pointer, or in another document entirely.
- **No-op** — a true sentence that changes no behaviour.
- **Orphan** — a pointer to something that moved, or a rule nothing reads.
- **Premature completion** — the agent stopping where the document let it stop.

## Procedure

1. Read the document as the agent would: what does it do on turn one, and where would it plausibly stop?
2. Mark every line that would change no behaviour, then delete those whole lines.
3. Check each pointer for wording: does it name the situation that should trigger it?
4. Check each step's done-condition. If you cannot state how the agent proves the step is finished, the criterion is missing, not implied.
5. Move branch-specific material behind a pointer.
6. Re-read the result and ask whether it got shorter while getting more specific. Both should be true.

Settle disagreements by running the document, not by arguing about it. A rewrite that only feels tighter has not been tested.

## Expected output

For a new or rewritten document: the document itself, plus a one-line note on which load each major section spends. For a review: the failure mode by name, the line it applies to, and the deletion or rewording that fixes it — never a general instruction to "make it more concise".
