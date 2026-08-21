---
name: EU AI Act High-Risk Obligations
description: PASS/FAIL/N/A checklist for the high-risk AI obligations under Articles 8-15 of the EU AI Act, plus the quality management system, conformity assessment, registration, post-market monitoring, and incident reporting.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [compliance, eu-ai-act, high-risk, checklist]
---
## Purpose

Give reviewers a concrete, article-by-article checklist for the obligations on providers of high-risk AI systems under Regulation (EU) 2024/1689. Use it to review a system against the requirements and to produce PASS/FAIL/N/A findings with evidence.

## When to use it

Whenever a system has been classified high-risk (Annex I or Annex III) and needs to be reviewed against its obligations, or when drafting the documentation that evidences those obligations. Pair with `eu-ai-act-risk-classification` (confirm the tier first) and `eu-ai-act-documentation` (produce the evidence).

## The obligations

### Art 8 — Compliance with requirements
The system must comply with Arts 9-15, taking into account its intended purpose and the state of the art, proportionately to the risk-management system.

### Art 9 — Risk management system
A documented, iterative risk-management process across the lifecycle: identify and analyse known and foreseeable risks to health, safety, and fundamental rights; estimate and evaluate risk; adopt risk-management measures; test the system against those measures. Must be maintained and updated as the system evolves.

### Art 10 — Data governance
Training, validation, and testing datasets must be relevant, sufficiently representative, and free of errors and bias, appropriate to the intended purpose. Document: design choices, data collection and origin (and, for personal data, the original purpose), data-preparation operations (annotation, labelling, cleaning, enrichment, aggregation), assumptions about what the data measures, and an assessment of availability, quantity, and suitability. Special attention to bias and to special-category personal data.

### Art 11 — Technical documentation
Draw up technical documentation before placing on the market, kept up to date, demonstrating compliance and enabling a competent authority to assess it. See Annex IV for the required contents (covered by the `eu-ai-act-documentation` skill).

### Art 12 — Record-keeping / automatic logging
The system must automatically record events over its lifetime, enabling traceability of its operation and monitoring for risks. Logs must be sufficient to interpret the system's output and identify situations that may lead to risk or substantial modification. Retention period must be appropriate to the intended purpose and applicable law.

### Art 13 — Transparency and information to deployers
The system must be designed so deployers can interpret its output and use it appropriately. Provide instructions for use covering: the provider's identity and contact, the system's characteristics/capabilities/limitations, intended purpose, level of accuracy/robustness/cybersecurity, known foreseeable risks, human-oversight measures, and expected lifetime and maintenance.

### Art 14 — Human oversight
The system must be designed for effective oversight by natural persons during use. Oversight measures must enable the human to understand the system's capabilities and limits, remain aware of automation bias, correctly interpret output, decide not to use it, and override or abort it. The human must be assigned, trained, and empowered — a checkbox is not oversight.

### Art 15 — Accuracy, robustness, and cybersecurity
The system must achieve an appropriate level of accuracy, robustness, and cybersecurity, consistent with its intended purpose and stated in the instructions for use. It must be resilient to errors, faults, and inconsistencies, and to attempts by third parties to alter its use or performance (including model poisoning, adversarial examples, and data-injection attacks).

### Art 17 — Quality management system
Providers must implement a documented QMS covering: regulatory-compliance strategy, design/design-control procedures, development and quality-assurance procedures, examination/test/validation procedures, technical specifications and standards, data-management systems, the risk-management system (Art 9), post-market monitoring (Art 72), incident reporting (Art 73), communication with authorities, record-keeping, resource management, and an accountability framework.

### Art 43 — Conformity assessment
Before placing on the market, the provider must carry out the applicable conformity assessment (internal control for most Annex III systems; third-party assessment for Annex I products and certain biometric systems), draw up the EU declaration of conformity, and affix the CE marking.

### Art 49 — Registration in the EU database
High-risk systems must be registered in the EU database before placing on the market or putting into service (applies from 2 Aug 2026).

### Art 72 — Post-market monitoring
Providers must establish and document a post-market monitoring system that actively and systematically collects and analyses data on the system's performance across its lifetime, feeding back into the risk-management system.

### Art 73 — Serious-incident reporting
Providers must report serious incidents (death, serious harm to health, serious disruption to critical infrastructure, or serious fundamental-rights violations) to the relevant authorities without undue delay.

### Art 26 — Deployer obligations (where the org is a deployer)
Use the system per the provider's instructions; ensure human oversight by competent, trained personnel; monitor operation and inform the provider of serious incidents; keep logs; inform workers and their representatives that a high-risk system is being used; and, where applicable, conduct a Fundamental Rights Impact Assessment before first use.

## Review format

Record PASS/FAIL/N/A per article with file, line, and evidence. Every FAIL needs a concrete failure scenario. Where an obligation is met by documentation rather than code, cite the document. Where an obligation doesn't apply (e.g. deployer obligations for a pure provider), mark N/A with a one-line reason.

## Expected output

```
Art 9 Risk management: PASS — risk register in docs/risk-management.md, updated per release
Art 10 Data governance: FAIL — training data origin undocumented; no bias assessment for the hiring model
Art 12 Logging: FAIL — no automatic event logging; outputs not traceable to inputs
Art 14 Human oversight: FAIL — no named, trained human assigned; no override/abort path
...
```
