---
name: TypeScript Config And Types
description: tsconfig, module-system and type-design checklist. Use when creating a TypeScript project or changing compiler options or core types.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [typescript, typing, config]
---
## Purpose

Keep the compiler configuration strict and the type design honest so the compiler catches real defects.

## When to use it

When creating a project, changing `tsconfig`, designing shared types, or when type errors tempt a cast.

## Checklist

- **Strict**: `strict: true`; add `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` for new code where the team can absorb them.
- **Modules**: choose ESM or CommonJS deliberately, set `module`/`moduleResolution` to match the runtime, and use `verbatimModuleSyntax` so type-only imports are explicit.
- **Targets**: set `target`/`lib` to what the minimum Node version supports; do not transpile what the runtime already runs.
- **Design**: model states with discriminated unions rather than optional-field bags; use `readonly` for data that should not change; avoid enums where a union of literals works.
- **Narrowing**: prefer type guards and schema parsing over assertions.
- **Checks in CI**: `tsc --noEmit` (or the project's build) is a separate gate from lint and tests.

## Expected output

A compiler configuration the team can defend, and types that make invalid states hard to represent.
