# Spec-Driven Development

## When To Use The `sdd-*` Pipeline Instead Of The Base `plan` Command

The base `plan` command (from the Software Engineer collection, if composed
alongside this one) is for a single task that's already scoped — write a
short checklist, then build. The `sdd-*` commands are for the step before
that: turning an underspecified feature request into a spec worth planning
against. Use `sdd-specify` when the request is a sentence or two of intent
("add SSO login", "let users export their data") rather than an
already-scoped task, and let the pipeline (`sdd-specify` →
`sdd-clarify` → `sdd-plan` → `sdd-tasks` → `sdd-analyze` →
`sdd-implement`) produce the task list that the base `plan`/`verify`
commands then execute and check. For a one-line bug fix or a change with no
real ambiguity, skip straight to `plan` — running the full pipeline on
something that doesn't need it is process for its own sake.

## The Constitution Is A Living Document, Not A One-Time Setup Step

`sdd-constitution` writes `docs/constitution.md` — the small set of
non-negotiable principles a spec, plan, or implementation must never
violate (e.g. "never break the public API without a version bump," "all
user data exports must be encrypted at rest"). It is distinct from
`AGENTS.md`, which governs how an agent *behaves* while working in the
repo; the constitution governs what the *product* is allowed to do. Revisit
it deliberately — via `sdd-constitution` again, not a direct edit — whenever
a new principle emerges from a real decision, so `sdd-analyze` always
checks specs against the current, not stale, set of rules.

---

This collection adapts the spec → clarify → plan → tasks → analyze →
implement workflow popularized by
[GitHub's spec-kit](https://github.com/github/spec-kit) (MIT licensed) to
MyACE's plain-markdown command format — without spec-kit's own CLI
scaffolding, numbered feature directories, or extension-hook system, since
those assume its dedicated `specify` tool rather than a general-purpose
coding agent.
