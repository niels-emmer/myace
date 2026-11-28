---
name: DPIA Checklist
description: Checklist for drafting a data protection impact assessment. Use when a feature involves high-risk personal-data processing or a regulator or policy requires a DPIA.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [privacy, dpia, gdpr]
---
## Purpose

Draft a DPIA (GDPR Art. 35) that the privacy lead can review and sign off, with engineering facts filled in accurately.

## When to use it

Before launching processing that is likely to be high risk, such as large-scale or systematic monitoring, special-category data, profiling with significant effects, or new technology. The privacy lead decides whether one is required.

## Checklist

- **Describe the processing**: nature, scope, context, purposes, data categories, data subjects, recipients, retention.
- **Necessity and proportionality**: why this data, why this much, and what less invasive option was considered.
- **Lawful basis**: leave for the privacy lead; record the candidate basis only.
- **Risks to people**: unauthorised access, excessive collection, loss of control, discrimination, re-identification; rate likelihood and severity with the organisation's scale.
- **Measures**: encryption, access control, pseudonymisation, minimisation, retention, logging, subject-rights support, vendor controls; map each to a risk.
- **Residual risk and consultation**: record what remains and whether prior consultation with the supervisory authority may be needed (a human decision).
- **Review**: set a date and the triggers that reopen it (new purpose, new vendor, new data category).

## Expected output

A draft DPIA with engineering facts verified against the code, assumptions marked, and legal decisions left clearly open.
