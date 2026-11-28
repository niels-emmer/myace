---
name: Accessible Components
description: Patterns for accessible dialogs, menus, tabs, forms, tables and custom controls. Use when building or fixing an interactive component.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [accessibility, components, aria]
---
## Purpose

Build common interactive components so they work with keyboard and assistive technology without surprises.

## When to use it

When creating a custom component, replacing a native element, or fixing an accessibility defect in an existing one.

## Checklist

- **Prefer native**: `button`, `a`, `input`, `select`, `dialog` and `details` give behaviour for free.
- **Dialog**: label it, move focus in, trap it inside, close on Escape, and return focus to the trigger.
- **Menus, tabs, comboboxes**: follow the ARIA Authoring Practices keyboard model for the exact pattern; do not invent one.
- **Forms**: visible `label` for every field, errors linked with `aria-describedby`, an error summary that takes focus on submit, and `autocomplete` tokens for known fields.
- **Tables**: real `th` with scope, a caption, and no layout tables.
- **Dynamic content**: announce updates with `aria-live` regions sparingly; move focus after route changes in single-page apps.
- **Icons and images**: an accessible name for icon-only buttons; empty `alt` for decoration.

## Expected output

A component that is fully operable by keyboard, announced correctly by a screen reader, and uses native elements wherever possible.
