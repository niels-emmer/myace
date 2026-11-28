# Android Developer

## Jetpack Compose-First

Build UI with Jetpack Compose by default. Use XML layouts only when Compose doesn't support the required pattern (complex custom views, map integration, WebView). Keep composables small, and prefer stateless composables that take their state as parameters.

## State Hoisting

State is hoisted to the lowest common ancestor that needs it. Composables accept state as parameters and emit events as callbacks — they never own mutable state that affects other composables. Use `remember`/`derivedStateOf` for local derived state, a `StateFlow` in the ViewModel for screen-level state, collected with `collectAsStateWithLifecycle()`.

## Play Store Readiness Gate

Before submission: app signing configured, keystore secured, API level targeting current requirements, privacy policy published, content rating completed, in-app review guidelines checked. See the `play-store-readiness` skill for the full checklist.

## Lifecycle Awareness

Every coroutine launched in a ViewModel is scoped to `viewModelScope`. Every composable that collects a `Flow`/`StateFlow` uses `collectAsStateWithLifecycle()` to respect the UI lifecycle (a `LiveData` is observed with `observeAsState()`). Never launch coroutines in composables — use `LaunchedEffect` for one-shot operations and `rememberCoroutineScope` for user-initiated ones.

## Android Offline-First

Design for offline as the default state. Use Room for local persistence, WorkManager for background sync, and `NetworkBoundResource` or equivalent pattern for cache-then-network reads. Show cached data immediately, update when network responds.
