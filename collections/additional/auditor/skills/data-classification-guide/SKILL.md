---
name: Data Classification Guide
description: Public / internal / sensitive data tiers and what's allowed to touch an AI prompt, a log line, or a committed file at each tier.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [security, data-classification, privacy]
---
## Purpose

Give reviewers a shared, concrete way to decide how carefully a piece of data needs to be handled, instead of relying on a case-by-case judgment call every time. Most security and privacy findings ("this shouldn't be in the log," "this shouldn't be in the prompt") come down to misjudging which tier the data actually belongs to.

## When to use it

Whenever a review needs to answer "is it OK for this data to end up here" — in an AI prompt or context window, in an application or access log, in a committed file (including test fixtures and example config), or in an error message returned to a client. Use it alongside `security-checklist`'s injection/output-handling items and the `Data Classification Awareness` rule.

## The three tiers

**Public** — safe for anyone to see with no restriction: published documentation, open-source code, marketing content, anything already deliberately made public.

**Internal** — not secret, but not meant for outside distribution: internal architecture notes, non-sensitive business metrics, internal tooling config that doesn't grant access to anything, employee directory info the org treats as internal-only.

**Sensitive** — data whose exposure causes real harm: personally identifiable information (names tied to contact info, government IDs, dates of birth), authentication material (passwords, API keys, tokens, private keys, session identifiers), financial data (card numbers, account numbers, transaction details), health data, and anything a contract, regulation, or the project's own policy specifically restricts.

When a piece of data's tier isn't obvious, classify it at the higher (more restrictive) tier until someone with authority over the data confirms otherwise — the cost of over-protecting public-adjacent data is small; the cost of under-protecting sensitive data is not.

## What's allowed where, by tier

| Destination | Public | Internal | Sensitive |
|---|---|---|---|
| AI prompt / context window | Yes | Generally yes, if the tool/provider is already trusted with internal data | No, unless the specific tool is explicitly approved for that data class and the org has confirmed it — default to no |
| Application/access logs | Yes | Yes, if log access is itself restricted to internal staff | No — never log raw sensitive values; log a reference/ID instead if you need traceability |
| Committed files (repo, fixtures, examples) | Yes | Usually no — internal specifics don't belong in a public or widely-shared repo | Never — including "just for a test," "temporarily," or in a private repo (private repos still get cloned, forked, and mirrored) |
| Client-facing error messages | Yes | No | No |

## Steps for a review

1. Identify every place the change reads, writes, logs, or transmits data.
2. Classify the data at each point using the tiers above — err toward the more restrictive tier when unsure.
3. Check each destination against the table. Any sensitive-tier data reaching a "No" destination is a finding — treat it with the same urgency as the `Secrets Are Always A Hard Fail` rule if the data is a credential specifically, otherwise a standard FAIL with a concrete scenario.
4. Note where classification isn't documented anywhere in the project — that absence is itself worth flagging to `compliance-reviewer`, since a review can't reliably check handling against a tier nobody wrote down.

## Expected output

A short list of `data → tier → destination → verdict` lines, feeding into the same PASS/FAIL/N-A structure as the rest of a review:

```
Data: user email address — Tier: Sensitive (PII)
  Destination: application log (line 142, `logger.info(f"user {email} logged in")`)
  Verdict: FAIL — sensitive PII in logs accessible to broader internal audience than necessary; log user ID instead.
```
