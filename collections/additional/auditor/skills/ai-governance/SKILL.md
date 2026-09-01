---
name: AI Governance
description: Data classification, model selection by sensitivity, audit trail, dependency compliance, and environment isolation for agentic coding in enterprise or internet-facing work.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [governance, security, compliance, data-classification]
---
## Purpose

Agentic coding in an enterprise or internet-facing context needs guardrails that a solo hobby project doesn't. This skill sets the rules for what data can go where, which models may see it, and how to keep an audit trail — so AI-assisted work doesn't become a compliance or data-exposure liability. It's the governance layer on top of `data-classification-guide`: that skill classifies a single piece of data; this one sets the standing rules for the whole session.

## When to use it

At the start of any enterprise or internet-facing session, and whenever a task involves data that might be sensitive, regulated, or customer-owned.

## Data classification

Classify data before sending it to any cloud-hosted model:

| Class | Definition | Permitted models |
|-------|------------|------------------|
| PUBLIC | Open-source code, public docs, no sensitive context | Any model |
| INTERNAL | Proprietary business logic, internal APIs, non-public architecture | Zero-retention cloud models approved for internal data |
| CONFIDENTIAL | PII, customer data, credentials, trade secrets, unreleased strategy | Local models only — never a cloud API |
| REGULATED | HIPAA, GDPR, SOC2-scoped data, financial/health records | Local models only, no exceptions |

When in doubt, treat as CONFIDENTIAL. Never paste customer PII, credentials, or production secrets into AI prompts.

## Model selection by sensitivity

- PUBLIC → any model.
- INTERNAL → zero-retention cloud models only; avoid free-tier or third-party models that may retain data for improvement.
- CONFIDENTIAL/REGULATED → local models only (Ollama, llama.cpp). If you can't keep it local, delegate the work to a local-only agent.

## Audit trail

Record AI-driven changes: what changed, why, and whether it was AI-authored or human-authored. Use a decision log for architecture decisions. Prefix enterprise-affecting AI-authored commits with `[ai]` in the body.

## Dependency compliance

Before adding a dependency, verify: OSI-approved license (MIT, Apache 2.0, BSD, LGPL — not AGPL or unlicensed), actively maintained, no critical CVEs, pinned to a specific version, from a trusted registry. Prefer the standard library over a new dependency for a single utility function.

## Environment isolation

Never mix personal and enterprise credentials, tokens, or accounts in the same session. Flag any detected cross-contamination.

## Expected output

A session where every piece of data was classified before it touched a model, only permitted models saw it, AI-driven changes are attributable, and no dependency or credential crossed a boundary it shouldn't have.
