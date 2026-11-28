---
name: Review And Commit Wording
description: Genre shapes for developer text a developer signs their name to (reviewer comments, author replies, reporting back after a check, code comments, and commit subjects), with the wording each one needs.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [writing, review, commits, comments, communication]
---

## Purpose

Each of these genres is short, and each fails in its own way: a review comment that diagnoses before it asks, a commit subject that describes the diff instead of the change, a code comment that explains what a reader can already see. This skill gives the shape of each. The voice itself, meaning the bans on dashes, stock vocabulary and closers, lives in the developer-voice skill; where a project's own rules on what to say conflict with a shape here, the project's rules win.

For the mechanical format of a commit or PR (types, scopes, length limits), use the project's commit and PR conventions. This skill covers the wording only.

## Reviewer comments

Raising a point on someone else's change.

- The ask is usually the whole comment: "can we reuse `parse_config` here?" A diagnosis before it, or a list of knock-on effects after it, is extra.
- Add a brief why only when the ask cannot stand alone, and ground it in the code rather than a hypothesis about the cause. "Otherwise this breaks when the field is renamed" is a reason; "since we're already in here" is convenience.
- Cite a project rule by what it says, not by its number.
- Points by similarity, not verdicts: "this is close to `retry_backoff`", not "this is basically a copy".
- Softening helps: "maybe we should", or a question with the exact symbol named. When flagging an uncertain risk, lead with the question and the mechanism, and leave the fix to the author.
- Two separate points go on two lines, not crammed into one comment.

## Author replies

Answering a reviewer on your own change.

- Accepting is one line: "fixed", "done", "good catch, thanks".
- Pushing back: the reason in one or two plain sentences, then the door left open ("I'd keep this because X, wdyt?"). Each argument gets its own short paragraph. Precedent is a link to one existing file, not a list of class names.
- Partial: what you changed and what you kept, with the reason.
- Concede what is right before defending what you keep, and never answer point by point in a wall of text.
- To a bot or a linter, drop the warmth entirely: say what changed, or why not.

## Reporting back

A colleague asked you to check something.

- Open with what you looked into and the verdict: "I looked into the quoting issue and it's expected" names the thing checked, which is not process narration.
- Then the reason in a sentence or two: the mechanism only, not a worked example of the failure and not steps for them to verify it themselves.
- Close on the verdict if it is the answer ("so nothing to fix"), and drop the line if it only reassures.

## Code comments

Margin notes a developer jotted, not prose.

- Clipped fragments beat full sentences: "don't reorder, auth must init first".
- Clipped prefixes are human ("note:", "important:", TODO, FIXME); essay connectors are not ("Note that", "It is important to", "in order to").
- Say what a reader cannot get from the code: the constraint, the reason for the odd line, the caller that depends on it. Never restate what the next line does.
- Prefer no comment to a low-value one, and delete a comment the code has outgrown.

## Commit messages

The subject says what the change does for the people using it, in everyday words, not how the diff achieves it. "fix: stop re-checking rounds that were already checked" beats "narrow later rounds to the previous round's fixes", which describes the implementation. It also beats a slogan, and beats a restatement of the files touched.

- When a change carries several points, name the situation they all improve rather than picking one at random.
- A body, when there is one, is a sentence or two of why. Not a walkthrough of the how, and not a summary of the content again.

## Expected output

The text for the genre at hand, sized to it: a review comment of one or two sentences, a reply of one, a commit subject under the project's limit. No preamble explaining which genre you chose or why the wording is short.
