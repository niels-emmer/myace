---
name: Subject Request Handling
description: Runbook design for access, export, correction and erasure requests and for breach response. Use when building or reviewing the systems and process behind data-subject rights.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [privacy, operations, gdpr]
---
## Purpose

Make it possible to answer a person's request and to respond to an incident within legal deadlines.

## When to use it

When building a self-service export or deletion, a support workflow for requests, or an incident runbook for personal-data breaches.

## Checklist

- **Deadline**: GDPR Art. 12(3) requires a response without undue delay and within one month, extendable by two further months for complex or numerous requests; record when the clock started.
- **Verify identity** proportionately before releasing or deleting anything; do not collect more data to do it.
- **Find everywhere**: use the inventory; include processors, search indexes, analytics and support tools.
- **Export**: a structured, commonly used, machine-readable format for data the person provided.
- **Erasure**: delete or irreversibly anonymise; define what backups do (expire on their normal cycle) and what must be kept for legal reasons, and say so to the requester.
- **Do not break integrity**: soft-delete flags are not erasure; check foreign keys and downstream copies.
- **Breach response**: detect, contain, scope what personal data and how many people, tell the privacy lead immediately; the 72-hour regulator clock (Art. 33) starts at awareness, and high-risk breaches may also require telling individuals (Art. 34). Those notifications are a human decision.
- **Legislative watch**: the EU Digital Omnibus proposal would amend GDPR; as of November 2026 the Council had agreed a position but no final text was adopted as far as could be verified, so confirm the current text before relying on any change.

## Expected output

A runbook and system support that can find, export, correct and delete a person's data and handle an incident inside the deadlines, with each legal decision assigned to a named human.
