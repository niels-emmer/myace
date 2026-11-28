# Accessibility

Accessibility conventions for web UI, targeting WCAG 2.2 level AA. This collection layers on a base
collection and complements `frontend` and `fullstack`; it adds an accessibility review layer rather
than component conventions. Automated checks catch only part of the problems, so the rules below
require keyboard and screen-reader checks as well.

## Semantic HTML Before ARIA

<!-- myace: priority=70 tags=accessibility,html -->

Use the native element that matches the job (`button`, `a`, `label`, `nav`, `main`, headings in order, lists, tables with headers) before reaching for ARIA. ARIA changes only what assistive technology is told, not behaviour, so a `div role=button` needs focus, key handling and state you must add yourself. See the `accessible-components` skill.

## Everything Works From The Keyboard

<!-- myace: priority=90 tags=accessibility,keyboard -->

Every interactive element is reachable and operable with the keyboard in a logical order, with a visible focus indicator that is not hidden by sticky headers or overlays (WCAG 2.2 Focus Not Obscured). Provide a way to skip repeated blocks, never trap focus except inside a modal that restores it on close, and provide a single-pointer alternative to any drag interaction.

## Name, Role And Value Are Programmatic

<!-- myace: priority=70 tags=accessibility,aria -->

Every control has an accessible name (a visible label or `aria-label`), form errors are associated with their fields and announced, status messages use a live region, and images have meaningful `alt` text (empty for decorative ones). Do not rely on placeholder text as a label.

## Colour, Size And Motion

<!-- myace: priority=70 tags=accessibility,visual -->

Text contrast is at least 4.5:1 (3:1 for large text and for UI component boundaries and focus indicators); information is never conveyed by colour alone; pointer targets are at least 24 by 24 CSS pixels unless an exception applies; content reflows at 320 CSS pixels wide and supports 200% text zoom; respect `prefers-reduced-motion` and avoid flashing.

## Accessible Authentication And Forms

<!-- myace: priority=70 tags=accessibility,forms -->

Do not require a cognitive function test (memorising or transcribing) to log in without an alternative: allow password managers and paste, and support copy-from-email codes. Do not ask users to re-enter information already provided in the same process, and keep help links in a consistent place.

## Accessibility Is Tested, Not Assumed

<!-- myace: priority=70 tags=accessibility,testing -->

Run an automated checker in CI and fix what it finds, then check keyboard-only use, a screen reader pass on the changed flow, zoom and reflow, and high-contrast or forced-colours mode. Automated tools find only a minority of WCAG issues, so a green scan is not a pass. See the `accessibility-testing` skill.
