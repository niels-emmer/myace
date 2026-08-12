---
name: Component Conventions
description: Guidance on composing, naming, and sizing components, designing their props, and keeping their state as local as possible.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [frontend, components, architecture]
---
## Purpose

Consistent component sizing, naming, and structure across the codebase.

## When to use it

Adding a new component, deciding whether to split one, or deciding where state should live.

## Composition

- Default to small components with one clear job. Signal of too-big: mixes data fetching + layout + business logic + presentation.
- Don't extract single-use components prematurely — splitting adds indirection without benefit.
- Extract when: reused in >1 place, represents a distinct nameable concept, or measurably simplifies the parent.

## Naming

- Name for what the component represents (`UserAvatar`, not `RoundImageWithBorder`).
- Match the project's existing casing and file-naming convention.
- Keep file name and exported name in sync.

## Prop design

- Pass only what the component needs — avoid passing entire data objects when two fields suffice.
- Prefer explicit typed props over a generic `data`/`config` blob.
- Use `variant`/`size` enums over piles of independent booleans.

## State locality

- Keep state in the component that owns it.
- Lift only to the nearest common ancestor when multiple components genuinely share the value.
- Use global state only for app-wide data (auth, theme).

## Expected output

A component with one clear responsibility, purpose-based name, minimal typed props, and state as local as sharing requirements allow.
