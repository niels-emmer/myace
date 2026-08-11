# Frontend Specialist

An additional rule set for UI/frontend work, meant to sit on top of a base collection (vibecoder or software-engineer). It adds component conventions, accessibility discipline, and a hard requirement that UI changes actually get looked at before they're called done.

## Never Done Without Visual Verification

A UI change is not finished when the code compiles or the unit tests pass — it's finished when it's been seen. Before declaring any UI task done: load it in a real or preview browser, exercise the actual golden-path interaction (not just render it), check at least one edge case (empty state, long/overflowing content, or a narrow mobile width), and check the browser console for errors or warnings. If there's no way to run a browser in the current environment, say so explicitly and flag the change as unverified rather than silently skipping the check. "It should work" is not a substitute for "I looked at it."

## Small Composable Components

Prefer several small components with clear responsibilities over one large component doing everything. If a component's render function needs scrolling past one screen to read, or it's juggling more than a couple of unrelated concerns, look for a natural seam to split it. That said, don't extract a component used in exactly one place just for the sake of a smaller file — an early split you have to immediately thread props through is premature abstraction, not composability. Extract when a piece is reused, when it has a distinct testable behavior, or when splitting it makes the parent genuinely easier to read — not on a line-count reflex.

## Accessibility Is Not Optional

Treat accessibility as a correctness requirement, not a nice-to-have to revisit later. At minimum: use semantic HTML elements (`button`, `nav`, `label`, headings in order) before reaching for ARIA roles, and only add ARIA when semantic HTML genuinely can't express the pattern. Every interactive element must be reachable and operable by keyboard alone, with a visible focus state. Text and meaningful UI elements need sufficient color contrast against their background. Images that convey information need real `alt` text; purely decorative images get `alt=""`. Anything that appears dynamically and steals attention — a modal, a toast, a dialog — needs to manage focus explicitly (move focus into it on open, return focus to the trigger on close) rather than leaving keyboard/screen-reader users stranded.

## Handle Loading, Empty, And Error States Explicitly

Every piece of UI that depends on async data has at least three states beyond "happy path with data": loading, empty (zero results, not an error), and error (the request failed). Design and implement all three intentionally instead of letting a blank screen or a raw stack trace stand in for whichever one the developer didn't think about. A loading state should say something is happening; an empty state should say there's genuinely nothing there (and what to do about it, if relevant); an error state should say what went wrong and, where possible, offer a way to retry.

## Keep State As Local As Possible

Default to keeping state as close as possible to the component that uses it. Only lift state up when two or more components genuinely need to read or change the same value — not preemptively "in case a sibling needs it later." Global state (context, stores) is for state that's actually global in scope (auth, theme, current user) or shared across a wide, unpredictable set of consumers — not a shortcut to avoid passing a couple of props down two levels. When you do lift state, lift it only as far up the tree as the nearest common ancestor that actually needs it, not all the way to the root by default.
