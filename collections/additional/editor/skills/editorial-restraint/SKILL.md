---
name: Editorial Restraint
description: Keeping factual documents honest and calm — every claim traceable, tone free of inflation, structure matching the content's shape, and gaps stated rather than filled with plausible-sounding prose.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [documentation, writing, editing, accuracy]
---

## Purpose

Documentation fails in ways a spellcheck will not catch: claims nobody can check, a tone that oversells a change, a paragraph holding four points that should be a list, and a confident conclusion built from material that does not support one. This skill is the content-level pass over a factual document — README section, docs page, release note, report, ADR. It asks one question of every sentence: can a reader verify this?

For the register of a message, review comment, or commit subject, use a voice skill if one is installed; this skill governs claims, not conversational tone.

## When to use it

- Writing or editing anything a stranger will read to make a decision.
- Reviewing someone else's prose for substance rather than structure (pair with the Documentation Standards skill for shape and drift-check for accuracy against code).
- Before publishing a document that summarises material you did not write.

## Every claim carries its evidence

- A number, date, version, benchmark, or link must match its source exactly. Do not round, convert, or "tidy" a figure you did not compute.
- An inference is not a fact. Mark it as an inference, or cut it.
- Elaboration past what the source supports is a deletion, not a caveat. If the material stops short of the conclusion, the document stops there too.
- Sources you actually used go in a list at the end: files, links, repositories, papers. A source you did not use does not belong in that list, and a claim does not belong in the document without one of them behind it.

## Tone stays restrained

- No exaggeration, no superlatives, no labels ("revolutionary", "blazingly fast", "seamless").
- No business jargon or abstract stock phrases standing in for the specific thing. If a plain noun exists, use it.
- No adverbs doing the work of evidence ("significantly", "dramatically") unless a measurement follows.
- No emoji in technical or reference prose.
- State the change, not the excitement about the change.

## Structure follows the content

- Independent points that sit side by side belong in a list or a table. Burying them in one paragraph forces the reader to reconstruct a list you already had.
- Steps a reader must perform in order are numbered, one action each, with the expected result where it is not obvious.
- A single short fact does not need a heading, a table, or a bulleted list of one. Structure should not outrun the content.

## Names stay as written

Proper nouns, code identifiers, file names, commands, configuration keys, and API field names keep their exact spelling and casing, in backticks where they render as code. A renamed identifier in prose sends the reader looking for something that does not exist.

## Say what the material cannot support

When the evidence does not decide the question, write that no conclusion can be drawn, and what would be needed to draw one. Filling the gap with background, common sense, or a transition sentence is the most common way a factual document becomes fiction.

## Cut what repeats

Keep one instance of each fact — the most complete one — and replace the others with a pointer. Anything that fits in one clear sentence does not become a paragraph. Repetition reads as emphasis and gets treated as noise.

## Expected output

For an edit: the revised text, plus a short list of what was removed and why (unsupported claim, duplicated fact, inflated wording). For a review: each finding as the quoted sentence, the rule it breaks, and the replacement sentence. If a document is accurate but structurally poor, say so and send it to the Documentation Standards skill rather than rewriting its shape here.
