---
name: EU AI Act Risk Classification
description: Decision tree for classifying an AI system into the EU AI Act risk tier (unacceptable/high/limited/minimal) and identifying the actor role (provider/deployer/importer/distributor).
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [compliance, eu-ai-act, risk-classification, governance]
---
## Purpose

Give reviewers a single, repeatable way to classify an AI system under Regulation (EU) 2024/1689 before any compliance work. Obligations attach to the risk tier and the actor role, so a wrong classification cascades into wrong (or missing) obligations. This skill is the decision tree the `eu-ai-act-classifier` agent applies.

## When to use it

Whenever a compliance review needs to answer "which EU AI Act obligations apply to this system?" — before reviewing against obligations, before drafting documentation, and whenever a system's intended purpose or deployment changes.

## The four risk tiers

**Unacceptable risk (prohibited, Art 5)** — practices banned outright since 2 Feb 2025: social scoring; manipulative or deceptive techniques causing harm; exploiting vulnerabilities of a person or group; untargeted scraping of facial images; emotion recognition in workplaces and education; biometric categorisation inferring sensitive attributes; real-time remote biometric identification in publicly accessible spaces (with narrow law-enforcement exceptions). A prohibited practice is a hard stop — not a gap to document.

**High risk (Annex I or Annex III)** — the most demanding tier. Annex I: AI embedded in regulated products (medical devices, machinery, toys, vehicles, aviation, marine) that must undergo third-party conformity assessment. Annex III: stand-alone use cases in eight domains — biometric identification/categorisation, critical infrastructure, education/vocational training, employment/worker management, essential private and public services (credit scoring, insurance, access to healthcare), law enforcement, migration/asylum/border control, and administration of justice. Art 6(3) provides a narrow exemption where the system is purely a minor auxiliary function and does not pose a significant risk of harm — apply it only with documented reasoning.

**Limited risk (transparency, Art 50)** — chatbots and virtual assistants, synthetic-content generators, emotion-recognition and biometric-categorisation systems, and deepfake tools. Subject to transparency obligations only, enforceable from 2 Aug 2026.

**Minimal risk** — everything else. Largely unregulated, though the Act encourages voluntary codes of conduct.

## The actor roles

- **Provider** — the entity that develops an AI system or GPAI model and places it on the market or puts it into service. Carries the bulk of the obligations (Arts 8-15, 17, 43, 49, 72, 73 for high-risk; Arts 53-55 for GPAI).
- **Deployer** — the entity that uses the system in the course of its activities. Obligations under Art 26: follow provider instructions, monitor, report incidents, inform workers, and (where applicable) conduct a Fundamental Rights Impact Assessment.
- **Importer / distributor** — entities in the supply chain that place or make available a system in the EU; verification duties before market placement.

## Steps for a classification

1. **Describe the intended purpose** — what the system is designed to do, from the provider's instructions for use, not what it could hypothetically do.
2. **Check Art 5 prohibitions first.** Any prohibited practice → stop, flag as a hard stop, no further classification needed.
3. **Check Annex I** — is the AI embedded in a regulated product subject to third-party conformity assessment? If yes → high risk.
4. **Check Annex III** — does the intended purpose fall in one of the eight domains? If yes → high risk, unless the Art 6(3) exemption clearly applies (document the reasoning).
5. **Check Art 50** — does it interact with people (chatbot), generate synthetic content, recognise emotion, or categorise biometrically? If yes → at least limited risk (transparency).
6. **Otherwise** → minimal risk.
7. **Identify the role** — provider, deployer, importer, or distributor — for the entity being reviewed.
8. **Record** the tier, role, reasoning, and any assumptions. Flag borderline cases for human/legal review.

## Timeline awareness

- **2 Feb 2025** — Art 5 prohibitions in force.
- **2 Aug 2025** — GPAI obligations (Arts 53, 55) and governance infrastructure in force.
- **2 Aug 2026** — general application; Art 50 transparency enforceable; Art 49 registration applies.
- **2 Dec 2027** — high-risk Annex III stand-alone obligations (deferred from Aug 2026 by the 2026 Omnibus).
- **2 Aug 2028** — high-risk Annex I product obligations (deferred from Aug 2027).

## Expected output

A short classification block feeding into the compliance output:

```
Intended purpose: resume screening for hiring
Art 5 prohibitions: none
Annex I: no (not a regulated product)
Annex III: yes — employment/worker management (recruitment)
Art 6(3) exemption: not applicable (core function, significant harm risk)
Tier: HIGH RISK
Role: provider (if we build it) / deployer (if we use a vendor system)
Obligations: Arts 8-15, 17, 43, 49, 72, 73; deployer Art 26
Timeline: Annex III obligations apply from 2 Dec 2027
```
