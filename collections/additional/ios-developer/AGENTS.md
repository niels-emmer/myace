# iOS Developer

## SwiftUI-First

<!-- myace: priority=50 tags=ios,ui -->

Build UI with SwiftUI by default. Use UIKit only when SwiftUI doesn't support the required pattern (collection view layouts, complex animations, camera/ARKit integration). Prefer `@ViewBuilder` composition over inheritance.

## State Management Patterns

<!-- myace: priority=50 tags=ios,state -->

Use `@State` for local view state and `@Binding` for child-to-parent communication. For reference-type model data, prefer the Observation framework (`@Observable` classes, iOS 17+) held with `@State`/`@Bindable` and shared via `@Environment`; on an older deployment target use `ObservableObject` with `@StateObject`/`@ObservedObject`/`@EnvironmentObject`. Never put business logic in views — extract it into a view model.

## App Store Readiness Gate

<!-- myace: priority=70 tags=ios,release -->

Before submission: privacy manifest complete, code signing valid, all required capabilities declared, screenshot automation covers all device sizes, no hardcoded App Store review credentials. See the `app-store-readiness` skill for the full checklist.

## iOS Offline-First

<!-- myace: priority=50 tags=ios,architecture -->

Design for offline as the default state, not an edge case. Cache network responses locally (CoreData, SwiftData, or file-based). Show stale data with a "last updated" indicator rather than a blank loading state. Queue writes made offline and sync when connectivity returns.

## Platform Review Gates

<!-- myace: priority=70 tags=ios,release -->

Every change that touches the App Store review boundary (new capability, new entitlement, privacy-impacting feature, payment/in-app purchase) gets a pre-submission review pass against current App Store guidelines. Don't assume a feature that passed review six months ago still passes today.
