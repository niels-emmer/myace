---
name: Model Routing Policy
description: Classify data by sensitivity, route each class to an appropriate model, and keep a zero-egress path for the most sensitive work.
version: "1.0.0"
priority: 55
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [governance, data-classification, model-routing, privacy, zero-egress]
---
## Purpose

Not all data may go to all models. This skill defines a small, enforceable
classification scheme and maps each class to a routing rule, so an agent can
decide where a request is allowed to go **before** it sends anything — and so
the most sensitive work always has a path that never leaves the boundary.

## When to use it

Before sending data to any model or external service: a prompt, a file, a log,
a database row, customer content, or a document. It applies equally to chat
turns, tool calls, embeddings, and summarisation.

## Data classes

| Class | Definition | Examples |
|---|---|---|
| **PUBLIC** | Already public or safe to publish | Open-source docs, public APIs, marketing copy, published standards |
| **INTERNAL** | Non-public but low harm if exposed | Internal design notes, non-sensitive metrics, internal code without secrets |
| **CONFIDENTIAL** | Harmful or disruptive if exposed | Customer PII, contracts, unreleased plans, proprietary source, incident details |
| **REGULATED** | Governed by law or contract | Health, financial, biometric, or government data; anything under a compliance regime |

When a piece of data is ambiguous, classify it as the **higher** class. A single
sensitive field raises the class of the whole payload unless it is removed.

## Routing rules

| Class | Allowed destination |
|---|---|
| **PUBLIC** | Any approved model, including third-party cloud |
| **INTERNAL** | An approved cloud model with enterprise or zero-retention terms, or a self-hosted model |
| **CONFIDENTIAL** | Self-hosted or otherwise in-boundary models only — no third-party cloud |
| **REGULATED** | In-boundary/on-premises models only, never any cloud, with access logged |

"Approved" means the route has been reviewed for the project; availability of a
provider is not the same as approval.

## The zero-egress path

Keep at least one inference route that makes no outbound network calls to a
third party — a model served on the same host or network boundary. Verify it
rather than assuming it:

- confirm the endpoint is internal;
- confirm the process has no fallback to an external API;
- test that an egress attempt from that path fails or is blocked;
- log which class each request was and which route served it.

If no zero-egress path exists, CONFIDENTIAL and REGULATED work must stop until
one does.

## Forbidden

- Sending REGULATED data to any cloud model, regardless of provider terms, without a documented and approved exception for a named route.
- Pasting secrets, credentials, tokens, or private keys into any prompt.
- Sending CONFIDENTIAL data to a third-party model without an explicit,
  documented exception.
- Treating "the provider says it is private" as a substitute for classification.
- De-identifying only some fields and calling the payload safe.

## Practical rules

- Classify before you compose the prompt, not after.
- Send the minimum data needed; prefer references over full records.
- Replace identifiers with placeholders when the task does not need them.
- Record the classification and the route in the work log.
- When a task cannot be completed within its class's allowed route, escalate —
  do not reclassify data to make it fit.

## Output format

```
## Routing decision
- Data class: PUBLIC / INTERNAL / CONFIDENTIAL / REGULATED
- Destination: <route> — allowed / requires exception / blocked
- Egress: none / third-party
- Redactions applied: <list or none>
- Justification: <one line>
```
