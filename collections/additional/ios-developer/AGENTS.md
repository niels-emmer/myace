# iOS Developer

## SwiftUI-First

Build UI with SwiftUI by default. Use UIKit only when SwiftUI doesn't support the required pattern (collection view layouts, complex animations, camera/ARKit integration). Prefer `@ViewBuilder` composition over inheritance.

## State Management Patterns

Use `@State` for local view state, `@Binding` for child-to-parent communication, `@ObservedObject`/`@StateObject` for reference-type model data, and `@EnvironmentObject` for app-wide dependencies. Never put business logic in views — extract into `ObservableObject` view models.

## App Store Readiness

Before submission: privacy manifest complete, code signing valid, all required capabilities declared, screenshot automation covers all device sizes, no hardcoded App Store review credentials. See the `app-store-readiness` skill for the full checklist.

## iOS Offline-First

Design for offline as the default state, not an edge case. Cache network responses locally (CoreData, SwiftData, or file-based). Show stale data with a "last updated" indicator rather than a blank loading state. Queue writes made offline and sync when connectivity returns.

## Platform Review Gates

Every change that touches the App Store review boundary (new capability, new entitlement, privacy-impacting feature, payment/in-app purchase) gets a pre-submission review pass against current App Store guidelines. Don't assume a feature that passed review six months ago still passes today.
