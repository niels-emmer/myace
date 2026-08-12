---
name: Visual Verification Workflow
description: The procedure for actually confirming a UI change in a real or preview browser — golden path, an edge case, console errors, and responsive/dark-mode checks — before calling it done.
version: "1.0.0"
priority: 60
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [frontend, verification, testing, browser]
---
## Purpose

Reading a diff and believing it's correct is not the same as confirming it's correct. This skill is the concrete procedure for actually looking at a UI change running in a browser before reporting the task as finished — it's what backs the "never done without visual verification" rule.

## When to use it

After any change that touches rendered UI: a new component, a style change, a layout change, new interactive behavior, or a fix to a visual bug. Skip it only for changes with no rendered surface at all (e.g. a pure backend/API change with no UI-visible effect).

## Steps

1. **Get it running.** Start (or reuse) the dev server / preview environment for the app. If no browser or preview tool is available in the current environment, stop here and say so explicitly in your report — do not report the change as verified.

2. **Check the golden path.** Navigate to the actual screen/component affected and exercise the primary interaction the change was meant to support — click the button, submit the form, open the panel — not just a glance at the initial render. Confirm it behaves as intended, not merely that it renders without crashing.

3. **Check at least one edge case.** Pick whichever is most relevant to the change:
   - **Empty state** — what does it look like with zero data/items?
   - **Long content** — what happens with an unusually long string, a long list, or a large number where the design assumed something shorter?
   - **Mobile width** — resize (or use device emulation) to a narrow viewport (roughly 375px) and confirm the layout still works: nothing overlaps, nothing is cut off, touch targets are still reasonably sized.

4. **Check the console.** Look at the browser console for errors or new warnings introduced by the change. A UI that looks fine but is quietly throwing errors is not done.

5. **Check responsive and theme behavior where relevant.** If the app supports multiple breakpoints, confirm the change holds up at both a narrow and a wide viewport. If the app supports light/dark mode, check the change in both — a common failure is text or borders that vanish in one theme because a color was hardcoded instead of using the theme's tokens.

6. **Report what you actually checked.** When declaring the task done, state plainly what was verified: which golden path, which edge case, and that the console was clean — not just "looks good." If a step couldn't be done (no browser, no way to simulate the edge case), name that gap instead of silently omitting it.

## Expected output

A short, specific verification note alongside the change: golden path confirmed, edge case checked (name which one), console clean, responsive/dark-mode checked if applicable — or an explicit statement of what couldn't be verified and why.
