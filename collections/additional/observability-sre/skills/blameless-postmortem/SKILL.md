---
name: Blameless Postmortem
description: Template and method for a blameless post-incident review with tracked actions. Use after any user-impacting incident or near miss.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [observability, incident, postmortem]
---
## Purpose

Turn an incident into durable system improvements without assigning personal blame.

## When to use it

Within a few days of an incident being resolved, or after a near miss that exposed a gap.

## Checklist

- **Summary**: what happened, who was affected, how long, and how it was detected.
- **Timeline**: from first signal to resolution in UTC, from logs and chat, marking decisions and the information available at each point.
- **Impact**: users, requests, data or money affected, measured rather than guessed.
- **Contributing factors**: several, across technology, process and tooling; ask how the system allowed it, not who did it. Avoid a single 'root cause' and 'human error' as a conclusion.
- **What went well, what was lucky, what was hard**: include detection, response and communication.
- **Actions**: each with an owner, a due date, a type (prevent, detect, mitigate) and a tracking ticket; prefer a few high-value actions over a long list.
- **Share and revisit**: publish the review, and check at the next review that actions were completed.
- **Facts only**: mark anything not verified from logs or data as an assumption.

## Expected output

A review with a factual timeline, several contributing factors, and a small set of owned, tracked actions.
