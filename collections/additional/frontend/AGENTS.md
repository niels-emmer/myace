# Frontend Specialist

## Never Done Without Visual Verification

Load UI changes in a real or preview browser. Exercise the golden-path interaction, check one edge case (empty state, long content, or mobile width), and verify the console is clean. If no browser is available, flag the change as unverified.

## Small Composable Components

Prefer small components with clear responsibilities. Don't extract single-use components prematurely. Extract when reused, when it has distinct testable behavior, or when it measurably simplifies the parent.

## Accessibility Is Not Optional

Use semantic HTML before ARIA. Every interactive element must be keyboard-reachable with visible focus. Meet contrast minimums. Meaningful images need `alt` text; decorative images get `alt=""`. Modals, toasts, and dialogs must capture focus on open and restore it on close.

## Handle Loading, Empty, And Error States Explicitly

Every async-data UI needs loading, empty, and error states — not just the happy path. Loading says something is happening; empty says there's nothing (and what to do); error says what went wrong with a retry option.

## Keep State As Local As Possible

Default to component-local state. Lift only when multiple components genuinely share the value, and only to the nearest common ancestor. Use global state only for app-wide data (auth, theme).
