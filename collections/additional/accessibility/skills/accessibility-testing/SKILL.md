---
name: Accessibility Testing
description: Procedure combining automated checks, keyboard testing and screen-reader passes. Use when verifying accessibility of a change or setting up CI checks.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [accessibility, testing, ci]
---
## Purpose

Test accessibility with a mix of tools and manual checks, since automation covers only part of WCAG.

## When to use it

When verifying a UI change, adding accessibility checks to CI, or triaging a reported barrier.

## Checklist

- **Automated**: run an engine such as axe through the unit, component or browser test suite and fail the build on violations; keep an allow-list with reasons, not a blanket disable.
- **Keyboard**: tab through the flow, check order, visible focus, no traps, and that Escape and Enter behave.
- **Screen reader**: check the changed flow with one screen reader and browser pair the audience uses (for example NVDA with Firefox or Chrome, VoiceOver with Safari); record the pair.
- **Visual**: 200% zoom, 320px reflow, forced-colours mode, reduced motion, and a contrast check on new colours.
- **Report honestly**: state what was run, what was not, and that automated results are partial.
- **Regressions**: add a test for each fixed barrier.

## Expected output

A test record showing which checks ran, what failed, what was fixed, and what remains unverified.
