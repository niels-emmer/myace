---
name: Component Conventions
description: Guidance on composing, naming, and sizing components, designing their props, and keeping their state as local as possible.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor]
tags: [frontend, components, architecture]
---
## Purpose

Give a consistent default for how components get sized, named, and structured, so a codebase built by many hands (or many agent sessions) doesn't drift into a mix of giant do-everything components and over-fragmented one-line wrappers.

## When to use it

Any time you're adding a new component, deciding whether to split an existing one, or deciding where a piece of state should live.

## Composition over size

Default to small components with one clear job — a piece of UI, a section of a form, a single card — composed together rather than one large component that renders an entire page inline. A good signal you've gone too big: the component mixes unrelated concerns (data fetching + layout + business logic + presentation all in one function), or you can't describe what it does in a single sentence.

Don't over-correct into fragmentation, though. If a piece of markup is used in exactly one place, isn't independently testable, and doesn't make the parent easier to read once extracted, leave it inline. Splitting it out just to keep files short adds an indirection (and props to thread through) without a real benefit. Extract when:
- It's reused in more than one place, or clearly will be soon (not "might be someday").
- It represents a distinct, nameable concept (e.g. `PriceBadge`, not `ThingAtTopRight`).
- Extracting it measurably simplifies the parent's logic, not just its line count.

## Naming

Name components for what they represent, not how they're implemented — `UserAvatar`, not `RoundImageWithBorder`. Match the project's existing casing and file-naming convention (check a few neighboring files rather than assuming). Keep a component's file name and its exported name in sync so it's grep-able.

## Prop design

Keep prop lists focused on what the component actually needs to do its job — avoid passing an entire data object down when the component only reads two fields off it (this couples the component to a shape it doesn't need and makes it harder to reuse). Prefer explicit, typed props over a generic `data`/`config` blob. For a component with many optional visual variants, consider a small `variant`/`size` enum prop over a pile of independent booleans that can combine into invalid states.

## State locality

Keep state in the component that owns it. Only lift state to a shared ancestor when two or more components genuinely need to read or change the same value — and lift it only as far as the nearest common ancestor, not reflexively to the top of the tree or into global state. If you find yourself passing a prop through two or three components that don't use it themselves just to reach a distant child, that's a sign the state either needs a narrower home (co-locate it closer to where it's used) or a purpose-built sharing mechanism (context, a store) — not that every intermediate component should quietly know about it.

## Expected output

A new or modified component that: has one clear responsibility, is named for its purpose, exposes a minimal typed prop interface, and keeps its state as close to itself as the actual sharing requirements allow.
