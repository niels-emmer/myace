---
name: SwiftUI Conventions
description: @State/@Binding/@ObservedObject usage, view composition, preview-driven development.
version: "1.0.0"
priority: 55
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [ios, swiftui, ui]
---
## Purpose

Consistent SwiftUI patterns across the codebase — predictable state management and view composition.

## Checklist

- **@State**: for simple value-type state owned by a single view (toggles, text field values, expand/collapse).
- **@Binding**: for child views that need to read/write a parent's state. Prefer binding to a specific field, not the entire model.
- **@StateObject**: for reference-type view models owned by this view. The view that creates the model owns it with `@StateObject`.
- **@ObservedObject**: for view models passed in from a parent. Never use `@ObservedObject` to create a model — that's `@StateObject`'s job.
- **@EnvironmentObject**: for app-wide dependencies (auth state, theme, data store). Use sparingly — prefer explicit passing for most cases.
- **View composition**: extract reusable subviews into computed properties or small `View` structs. Use `@ViewBuilder` for conditional content.
- **Previews**: every view has a preview provider showing default state, empty state, and error state.

## Expected output

SwiftUI views with predictable state management, no business logic in views, and preview coverage for all states.
