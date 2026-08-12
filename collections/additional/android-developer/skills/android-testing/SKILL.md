---
name: Android Testing
description: JUnit + Robolectric unit tests, Compose UI tests, screenshot tests, and Espresso for legacy views.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [android, testing, junit]
---
## Purpose

Test Android apps at the right level — fast unit tests for ViewModels, UI tests for critical flows.

## Checklist

- **Unit tests (JUnit + Robolectric)**: test ViewModels, repositories, and data transformation logic. Robolectric simulates the Android framework for fast test execution.
- **Compose UI tests**: use `ComposeTestRule` to test composable rendering and interaction. Cover default, empty, and error states.
- **Screenshot tests**: use `papaya` or equivalent for Compose screenshot testing. Catch visual regressions.
- **Espresso tests**: for legacy XML-based UI. Don't use for new Compose UI.
- **Room DAO tests**: use an in-memory Room database instance. Test queries, migrations, and type converters.
- **Test independence**: each test sets up its own state. Use `TestCoroutineDispatcher` for coroutine-based code.

## Expected output

A test suite where ViewModels are unit-tested with Robolectric, Compose UI is screenshot-tested, and Room DAOs are integration-tested against an in-memory database.
