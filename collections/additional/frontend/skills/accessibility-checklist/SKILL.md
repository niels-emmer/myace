---
name: Accessibility Checklist
description: A concrete, checklist-driven pass for semantic HTML, ARIA, keyboard navigation, contrast, alt text, and focus management.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [frontend, accessibility, a11y]
---
## Purpose

Turn "make it accessible" into a concrete, checkable set of steps instead of a vague aspiration applied inconsistently. Use this on any UI that a real user will interact with — accessibility isn't a separate pass reserved for "important" screens.

## When to use it

While building any new interactive UI, and as a review pass on any UI diff before it's called done — especially anything with custom widgets (dropdowns, modals, tabs, tooltips), forms, or dynamically appearing content.

## Checklist

**Semantic HTML first**
- Use `button` for anything clickable that performs an action, `a`/`Link` for anything that navigates — not a `div` with an `onClick`.
- Use real form elements (`label`, `input`, `select`, `fieldset`) with `label` correctly associated to its control (via `for`/`id` or wrapping).
- Use heading elements (`h1`–`h6`) in a logical, non-skipping order to convey document structure, not just for font size.
- Reach for ARIA roles/attributes only when semantic HTML genuinely can't express the pattern (e.g. a custom combobox) — an ARIA role bolted onto a `div` is a fallback, not a first choice.

**Keyboard navigation**
- Every interactive element (buttons, links, form controls, custom widgets) must be reachable via Tab and operable via Enter/Space (or arrow keys, for things like tabs/menus, per the expected pattern for that widget).
- Tab order should follow visual/logical order — don't let a positioning trick silently reorder focus.
- Nothing should trap keyboard focus except a modal while it's open (and even then, Escape or an explicit close control should release it).
- Every focusable element needs a visible focus indicator — don't strip `outline` without providing a replacement.

**Color and contrast**
- Body text and meaningful UI text should meet at least a 4.5:1 contrast ratio against its background; large text (roughly 18pt+/bold 14pt+) can go as low as 3:1.
- Don't use color alone to convey meaning (e.g. a red border as the only signal of a form error) — pair it with an icon, text, or both.

**Images and media**
- Meaningful images (photos, diagrams, icons that convey information) need descriptive `alt` text.
- Purely decorative images get `alt=""` so screen readers skip them, not a missing `alt` attribute.

**Dynamic content and focus management**
- When a modal, dialog, or drawer opens, move focus into it (typically to its heading or first control); when it closes, return focus to whatever triggered it.
- When a toast/notification appears without user-initiated focus change, announce it to assistive tech (e.g. an `aria-live` region) rather than relying on a sighted user noticing it.
- When content is inserted, removed, or replaced dynamically (e.g. a list filtering as you type), make sure the change is perceivable to a screen reader user, not just visually.

## Expected output

A UI change that passes this checklist item by item — not just "looks accessible" on a glance. Where an item genuinely doesn't apply, that's fine; note it as not applicable rather than silently skipping it.
