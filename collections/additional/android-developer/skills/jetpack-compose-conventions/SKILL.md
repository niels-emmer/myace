---
name: Jetpack Compose Conventions
description: State hoisting, remember/derivedStateOf patterns, modifier ordering, and preview annotations.
version: "1.0.0"
priority: 55
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [android, compose, ui]
---
## Purpose

Consistent Compose patterns — predictable state flow and composable structure.

## Checklist

- **State hoisting**: composables accept state as parameters and emit events as callbacks. No mutable state owned by a composable that affects siblings.
- **remember**: for derived state that shouldn't recompute on every recomposition. Use `remember { mutableStateOf(...) }` for local UI state.
- **derivedStateOf**: for state derived from other state that should only recompute when inputs change.
- **Modifier ordering**: order is semantic, each modifier wraps what follows it. Put `clickable` before `padding` when the padding should be part of the touch target; put `background`/`border` before or after `padding` depending on whether the padded area should be painted. Pick a consistent ordering per intent and keep it across the codebase.
- **Preview annotations**: every composable has `@Preview` annotations showing default, empty, and error states. Use `@Preview(showBackground = true)` for readability.
- **LazyColumn/LazyRow keys**: stable and unique keys for item composition — prevents unnecessary recomposition and animation glitches.

## Expected output

Compose UI with predictable state flow, consistent modifier ordering, and preview coverage for all states.
