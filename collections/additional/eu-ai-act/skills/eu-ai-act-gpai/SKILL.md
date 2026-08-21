---
name: EU AI Act General-Purpose AI
description: Checklist for the general-purpose AI (GPAI) obligations under Articles 51-55 — technical documentation, copyright policy, training-data summary, and systemic-risk obligations (evaluation, adversarial testing, incident reporting, cybersecurity).
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [compliance, eu-ai-act, gpai, foundation-model]
---
## Purpose

Give reviewers a concrete checklist for the obligations on providers of general-purpose AI (GPAI) models under Regulation (EU) 2024/1689, Articles 51-55. GPAI obligations entered into application on 2 Aug 2025. This is the skill the `eu-ai-act-compliance-reviewer` agent applies to GPAI.

## When to use it

Whenever the org is a provider of a GPAI model (a foundation model / large language model placed on the market), or a downstream provider building an AI system on a GPAI model and needing to understand what flows down from the upstream provider.

## The obligations

### Art 51 — Classification of GPAI models with systemic risk
A GPAI model is presumed to have systemic risk if it has high-impact capabilities (cumulative training compute above a threshold, ~10^25 FLOPs). The provider must notify the AI Office if the model meets the threshold or is designated as having systemic risk.

### Art 53 — Obligations for all GPAI model providers
- **Technical documentation** — draw up and keep up to date, including training approach, data sources, capabilities and limitations, and evaluation results, sufficient for the AI Office and downstream providers to understand the model.
- **Copyright policy** — put in place a policy to comply with Union copyright law, in particular to identify and respect reservations of rights (opt-outs) expressed under the DSM Directive.
- **Training-data summary** — make publicly available a sufficiently detailed summary of the content used for training, per the Commission template.

### Art 54 — Authorised representatives
Non-EU GPAI providers must appoint an authorised representative established in the Union before placing the model on the market.

### Art 55 — Obligations for GPAI models with systemic risk
In addition to Art 53:
- **Model evaluation** — perform and document model evaluations, including adversarial testing, to identify and mitigate systemic risks.
- **Risk assessment and mitigation** — assess and mitigate systemic risks at Union level, including through model alignment, and report serious incidents to the AI Office.
- **Cybersecurity** — ensure an adequate level of cybersecurity protection for the model and its physical infrastructure.

## Downstream flowdown (for deployers / downstream providers)

If the org builds an AI system on a third-party GPAI model (e.g. GPT, Claude, Gemini, Llama, Mistral), the org is usually not a GPAI provider and has no direct Art 53 duty — but it does have direct Art 50 transparency duties (see `eu-ai-act-transparency`) and, if the system is high-risk, the Art 8-15 obligations (see `eu-ai-act-high-risk-obligations`). Verify the upstream provider offers: machine-readable marking (C2PA/watermark/metadata), provenance metadata in API responses, and configurable disclosure for interactive use. If not, flag that supplementary measures are needed.

## Review checklist

1. Is the org a GPAI model provider, or a downstream provider/deployer? (Determines which obligations apply.)
2. If a provider: confirm technical documentation exists and is current.
3. If a provider: confirm a copyright policy that respects opt-outs/reservations of rights.
4. If a provider: confirm a training-data summary is published per the Commission template.
5. If a provider: confirm whether the model meets the systemic-risk threshold; if so, confirm evaluation, adversarial testing, incident reporting, and cybersecurity obligations are met.
6. If a downstream provider/deployer: confirm the upstream provider's marking/documentation features are available and passed through.

## Expected output

```
Art 53 technical documentation: PASS — model card + training-data summary published
Art 53 copyright policy: FAIL — no documented policy for respecting opt-outs/reservations of rights
Art 55 systemic risk: N/A — model below the compute threshold, not designated systemic
```
