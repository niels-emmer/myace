---
description: Turn a clarified spec into a concrete technical plan — architecture, data model, and interfaces — before any task breakdown or code.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
---
1. Read `docs/specs/<slug>/spec.md`. If it still has unresolved `[NEEDS CLARIFICATION]` markers, stop and run `sdd-clarify` first — planning against an ambiguous spec just moves the ambiguity into the code.
2. Resolve open technical unknowns explicitly before designing around them: which library, which existing service boundary, which of two viable data shapes. Where the codebase already has an established pattern for something similar, follow it rather than introducing a second way to do the same thing.
3. If the `architecture-review` skill is available (from the Software Engineer collection), use its design-note discipline for this step — a new data model, service boundary, or auth-relevant change is exactly the kind of decision that skill exists to force onto paper before code.
4. Write `docs/specs/<slug>/plan.md` covering: the chosen approach and why alternatives were rejected, the data model (new/changed entities and their relationships), the interfaces being added or changed (API endpoints, function signatures, event shapes), and how this plan satisfies every functional requirement and edge case listed in the spec.
5. Cross-check against `docs/constitution.md` if it exists — a plan that violates a stated principle needs either a redesign or an explicit, justified exception noted in the plan, not a silent violation.
6. Do not write task lists or code here — that's `sdd-tasks` and `sdd-implement`. This step produces the design that both build on.
7. Report the plan's location and flag anything you're genuinely uncertain about rather than presenting a guess as a settled decision.
