---
name: iOS Testing
description: XCTest unit tests, XCUITest UI tests, snapshot testing, and performance baselines for iOS apps.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [ios, testing, xctest]
---
## Purpose

Test iOS apps at the right level — fast unit tests for logic, UI tests for critical flows.

## Checklist

- **Unit tests (XCTest)**: test view models, networking layer, data transformation logic. Fast — no UI dependency.
- **UI tests (XCUITest)**: test critical user journeys (login, purchase, settings navigation). Slow — use sparingly.
- **Snapshot tests**: use `swift-snapshot-testing` or equivalent for view rendering. Cover default, empty, and error states.
- **Performance baselines**: set `measure()` blocks for critical code paths (data parsing, image processing, database queries).
- **Test independence**: each test sets up its own state and tears down after. No shared mutable state between tests.
- **CI integration**: tests run on every PR. UI tests run on a physical device or simulator matrix covering target OS versions.

## Expected output

A test suite where unit tests cover business logic, snapshot tests cover UI rendering, and UI tests cover only critical user journeys.
