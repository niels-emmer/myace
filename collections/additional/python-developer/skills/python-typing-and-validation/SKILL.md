---
name: Python Typing And Validation
description: Typing and boundary-validation checklist for Python. Use when adding a public function, a data model or a type-checker configuration.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [python, typing, validation]
---
## Purpose

Keep types honest and validate data where it enters the program, so the rest of the code can trust its inputs.

## When to use it

When adding or changing a public signature, defining a data shape, or when the type checker reports errors you are tempted to silence.

## Checklist

- **Signatures**: annotate parameters and returns; use `X | None` rather than `Optional[X]` on current Python versions.
- **Shapes**: dataclasses or Pydantic/attrs models for records, `TypedDict` for dict-shaped JSON, `Protocol` for duck typing; avoid bare `dict`/`list` without parameters.
- **Boundaries**: parse and validate once at the edge (request body, config file, queue message, LLM output) into a typed object; do not pass raw dicts inward.
- **Ignores**: every `# type: ignore[code]` carries a reason; an ignore with no code is a defect.
- **Config**: enable the checker's strict flags for new code even if legacy modules are exempt; ratchet, do not loosen.
- **Generics**: use `TypeVar`/PEP 695 syntax where the project's minimum Python version supports it; otherwise `TypeVar`.

## Expected output

Code whose public surface is annotated, whose external data is parsed into typed objects at the boundary, and whose type checker run is clean.
