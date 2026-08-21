---
name: EU AI Act Transparency
description: Checklist for the Article 50 transparency obligations — chatbot AI disclosure, machine-readable marking of synthetic content, emotion-recognition/biometric-categorisation notice, and deepfake/public-interest-text labelling.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [compliance, eu-ai-act, transparency, deepfake, chatbot]
---
## Purpose

Give reviewers a concrete checklist for the Article 50 transparency obligations under Regulation (EU) 2024/1689. These apply to limited-risk systems too — not just high-risk ones — and are enforceable from 2 Aug 2026. This is the skill the `eu-ai-act-compliance-reviewer` agent applies to transparency.

## When to use it

Whenever a system interacts with people (chatbot/virtual assistant), generates or manipulates synthetic content (image, audio, video, text), recognises emotion, or categorises people biometrically. Also when reviewing a deployer's handling of AI-generated content.

## The four obligations

### Art 50(1) — AI interaction disclosure (chatbots and virtual assistants)
Providers must ensure that systems intended to interact directly with natural persons are designed so the person is informed that they are interacting with an AI system, unless this is obvious from the circumstances. Applies at the time of first interaction, in a manner that meets accessibility requirements. A site-wide footer disclaimer is not sufficient — the disclosure must be at the point of interaction.

### Art 50(2) — Machine-readable marking of synthetic content
Providers of generative AI systems (including GPAI) must ensure outputs are marked in a machine-readable format and detectable as artificially generated or manipulated. This covers all modalities — audio, image, video, text. Implement via C2PA content credentials, invisible watermarking, or provenance metadata in API responses. The marking must survive the distribution pipeline. (Generative systems placed on the market before 2 Aug 2026 have until 2 Dec 2026 to meet this duty.)

### Art 50(3) — Emotion recognition / biometric categorisation notice
Deployers of emotion-recognition or biometric-categorisation systems must inform the natural persons exposed to them. First screen the use case against the Art 5 prohibition (emotion recognition in workplaces/education is banned); for permitted uses, design a clear, distinguishable notice mechanism.

### Art 50(4) — Deepfake and public-interest text labelling
Deployers of generative systems must disclose that content is artificially generated or manipulated where it constitutes a deepfake (image, audio, or video that appears authentic but is not) or AI-generated text published with the purpose of informing the public on matters of public interest. The disclosure must be clear and distinguishable, at the point of consumption — an adjacent label, overlay, caption, or equivalent a reasonable person would notice. A narrow exception applies to evidently artistic, satirical, creative, or fictional works (disclosure in an appropriate manner that doesn't hamper enjoyment). Commercial marketing content does not qualify for the artistic exception.

## Who does what

- **Provider** — Art 50(1) chatbot disclosure and Art 50(2) machine-readable marking (including downstream providers building on a GPAI model).
- **Deployer** — Art 50(3) emotion-recognition notice and Art 50(4) deepfake/public-interest-text labelling, to the extent the use case triggers them.

## Review checklist

1. Inventory every AI-powered touchpoint that interacts with people or generates content.
2. For each chatbot/virtual assistant: confirm a clear AI-disclosure at first interaction, accessible and not buried.
3. For each synthetic-content generator: confirm machine-readable marking (C2PA/watermark/metadata) is embedded and survives distribution.
4. For each emotion-recognition/biometric-categorisation use: screen against Art 5 prohibition first, then confirm the notice mechanism.
5. For each deepfake-capable or public-interest-text use: confirm visible labelling at the point of consumption.
6. If using a third-party GPAI model, verify the provider offers marking features (C2PA, provenance metadata, configurable disclosure); if not, flag that supplementary measures are needed.

## Expected output

```
Art 50(1) chatbot disclosure: PASS — "You are chatting with an AI assistant" at first interaction
Art 50(2) machine-readable marking: FAIL — image outputs have no C2PA credentials or watermark; marking does not survive the CDN pipeline
Art 50(4) deepfake labelling: N/A — no deepfake-capable or public-interest text use cases
```
