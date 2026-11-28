---
name: WCAG 2.2 AA Checklist
description: Review checklist for WCAG 2.2 level AA with the criteria added in 2.2 called out. Use when reviewing a page, component or flow for accessibility.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [accessibility, wcag, review]
---
## Purpose

Give a reviewer a short, ordered list that covers the most common WCAG 2.2 AA failures, including the new criteria.

## When to use it

When reviewing UI changes, preparing for an accessibility audit, or checking a flow against the European Accessibility Act or procurement requirements.

## Checklist

- **Perceivable**: text alternatives; captions for prerecorded video; semantic structure; 4.5:1 text contrast and 3:1 for UI components; reflow at 320px; text spacing; no colour-only meaning.
- **Operable**: full keyboard access; no keyboard trap; skip link; visible focus; **2.4.11 Focus Not Obscured (Minimum)**; **2.5.7 Dragging Movements** has a single-pointer alternative; **2.5.8 Target Size (Minimum)** 24 by 24 CSS pixels; no time limits without control.
- **Understandable**: page language set; consistent navigation; **3.2.6 Consistent Help**; error identification and suggestions; **3.3.7 Redundant Entry**; **3.3.8 Accessible Authentication (Minimum)**.
- **Robust**: valid names, roles and values; status messages announced. Note that 4.1.1 Parsing was removed in WCAG 2.2.
- **Context**: WCAG 2.2 became a W3C Recommendation in October 2023; the European Accessibility Act applies to covered products and services from 28 June 2025 and points to EN 301 549. Whether a given product is in scope is a question for the owner's compliance lead.

## Expected output

A list of failures mapped to success criteria with severity and concrete fixes, plus a statement of what was and was not checked.
