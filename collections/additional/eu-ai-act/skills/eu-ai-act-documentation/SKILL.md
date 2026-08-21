---
name: EU AI Act Documentation
description: What compliance documentation to produce under the EU AI Act — Annex IV technical documentation, EU declaration of conformity, risk-management file, data-governance records, and GPAI training-data summary — and how to structure it.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [compliance, eu-ai-act, documentation]
---
## Purpose

Give reviewers and documentation writers a concrete map of the documentation deliverables the EU AI Act requires, and how to structure them so a human or legal reviewer can verify them line by line. This is the skill the `eu-ai-act-documentation-writer` agent applies.

## When to use it

Whenever a system needs its compliance documentation produced or updated — after classification, alongside a high-risk or GPAI review, and whenever the system's design changes.

## The documentation set

### Annex IV — Technical documentation (high-risk providers)
The core evidence file for a high-risk system. Required contents:
- General description: intended purpose, provider identity, version, how the system interacts with hardware/software, the instructions for use.
- Detailed description of the system's elements and development process: architecture, design specifications, algorithms, data requirements, human-oversight measures, and the development lifecycle.
- Monitoring, functioning, and control: capabilities and limitations, expected accuracy/robustness/cybersecurity levels, foreseeable unintended outcomes, test procedures.
- Risk-management system: the risk-management file and the measures adopted.
- Changes made to the system and its documentation over its lifecycle.
- Any relevant harmonised standards or common specifications applied.

### EU declaration of conformity
A signed declaration stating the system meets the applicable requirements, referencing the conformity-assessment procedure used and any harmonised standards applied. Required before placing on the market.

### Risk-management file (Art 9)
The documented risk-management process: identified risks, their analysis and evaluation, the mitigation measures, and the testing that validates them. Maintained and updated across the lifecycle.

### Data-governance records (Art 10)
Documentation of training/validation/test data: design choices, data collection and origin (and, for personal data, the original purpose), data-preparation operations, assumptions about what the data measures, and an assessment of availability, quantity, and suitability. Include bias assessment where relevant.

### Record-keeping / logging evidence (Art 12)
Evidence that the system automatically records events enabling traceability and monitoring, with an appropriate retention period.

### GPAI training-data summary (Art 53)
For GPAI model providers: a publicly available summary of the content used for training, per the Commission template, alongside the technical documentation and copyright policy.

## How to structure a documentation draft

- **Ground every section in the real design** — read the code, data flows, and deployment config; don't write generic boilerplate.
- **Mark unverifiable facts as assumptions** — if a fact can't be confirmed from the repo, write `[ASSUMPTION: ...]` for human confirmation rather than inventing it.
- **Trace documentation to obligations** — annotate each section with the article it evidences (e.g. "evidences Art 10 data governance") so a reviewer can trace documentation back to the requirement.
- **Use headings, tables, and checklists** — structured documents a reviewer can verify line by line, not prose essays.
- **Keep it in sync** — if the design changes, the documentation changes in the same pass.

## Expected output

A documentation set (or a single structured draft) with each section annotated to the article it evidences, unverifiable facts marked as assumptions, and a cover note listing which obligations the set covers and what remains for human/legal review.
