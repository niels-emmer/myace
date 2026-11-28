---
name: Developer Voice
description: The register for text a developer publishes under their own name (review replies, PR descriptions, commit subjects, chat messages): plain, short, and specific. A style guide only: it never changes who is credited, and any project rule that marks AI-authored work still applies.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [writing, tone, review, commits, communication]
---

## Purpose

Most text an agent writes for a developer is read by another developer in a channel that is already informal: a review thread, a PR description, a commit subject, a chat message. That register is short, plain, and uneven. Padded text tends to the opposite: evenly weighted sentences, decorative structure, a closing line nobody needed. This skill covers the voice itself. It is about clarity and brevity, not about hiding how a text was produced: when the project requires an authorship marker (for example an AI-authored commit marker), add it as the project says. The shape of each genre is in the review-and-commit-wording skill.

## When to use it

- Writing a review comment, a reply to one, a PR description, a commit subject or body, a code comment, or a status message to a colleague.
- Reviewing a draft of any of those before it goes out.
- Rewriting text that reads fine but sounds like a brochure.

## Baseline

Concise, plain, conversational. State the point in the fewest words that keep it precise, then stop.

Hard rules, not preferences:

- No em or en dashes. Rewrite with a comma, a period, or a break.
- No exclamation marks and no emoji.
- No stock filler vocabulary: crucial, robust, leverage, seamless, comprehensive, streamline, enhance, additionally, ensure, and "key" as an adjective.
- No "not X but Y" framing when nobody proposed X.
- No closer that only rounds the text off. A last line that carries the ask or the verdict stays.
- No invented events, meetings, or discussions.
- Names as people use them, not identifiers.

## Softer tells worth removing

These are tips, not bans; cut them when they add nothing.

- **Openers that stall.** "Good question", "quick note", "just to clarify", "honestly": start with the substance.
- **Arguing with nobody.** Answering an objection that was never raised. Cut it, or state the claim it was hiding.
- **Threes by reflex.** Three adjectives, three examples, three facts and a lesson. Keep three only when there are three.
- **Stacked qualifiers.** "could potentially", "might arguably": one hedge at most, and only for real doubt.
- **Over-precision.** Naming every path, value and timestamp to prove you looked is noise. Keep the precision the point needs; let the rest stay plain ("the lock timeout", not "`lockTimeoutMs: 30000`").
- **Dense blocks.** Past a couple of sentences, one idea per short paragraph.
- **Decoration by rule.** A bold label and colon on every bullet, title-case headings, decorative arrows. Bold only what needs it.

## Before sending

Re-read the finished text once, looking only for the rules above. Reword every dash away, flatten every contrast that only adds weight, delete an ending that only rounds off. Reciting the rules while drafting does not catch these; the pass over the final text does.

## Expected output

The message itself, in the channel's own register, with no preamble about the work of writing it. If asked to review someone else's text, return the specific lines that break a rule and the replacement, not a general note about tone.
