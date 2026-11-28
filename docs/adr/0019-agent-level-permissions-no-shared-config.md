# ADR-0019: Agent-level permissions, compiled into agent files only

**Status:** Proposed

## Context

Every starter-pack agent describes its authority in prose ("Permission
posture: do freely / pause and confirm / never do"). It is the most valuable
governance content in the base packs, and it is advisory: no adapter turns it
into anything a framework enforces, so a "read-only" reviewer can still edit
files.

Two frameworks MyACE compiles for have real per-agent controls: Claude Code
(`tools:` in `.claude/agents/*.md`) and OpenCode (`permission:` in agent
frontmatter). The obvious way to use framework permissions is a global config
file (`.claude/settings.json`, the `permission` block of `opencode.json`). But
a compiled download is meant to be unpacked into a user's home or project
folder, and those files hold the user's *own* setup: writing them can overwrite
it, and merging into them is only safe from a tool that can read the existing
file (the CLI), never from a zip.

## Decision

Compile structured permissions into **each agent's own frontmatter and
nowhere else**. No adapter emits a shared config file (`settings.json`,
`opencode.json` permission block, or a sidecar); a zip can therefore never
overwrite anything the pack did not itself create.

Permissions are **tighten-only by construction**: the vocabulary can restrict a
capability (`deny`, `ask`) and nothing can grant beyond the framework default.
Absent means "inherit", and an adapter emits a restriction only when one is
declared.

## Alternatives considered

- **Emit/merge a global settings file.** Rejected: clobbers or collides with
  user config, breaks "unzip and go", and lets a pack widen someone's
  permissions.
- **Opt-in sidecar file (`myace.permissions.json`) the user merges by hand.**
  Deferred, not rejected: safe but manual; revisit if agent-level scoping
  proves too coarse.
- **CLI-only tracked additive merge (`myace pull --apply-permissions`).**
  Deferred: safe if diffed and recorded in the `.myace/` manifest (ADR-0009),
  but a separate feature with its own trust model.
- **Leave permissions as prose.** Rejected as the end state: it is the status
  quo this ADR exists to improve.

## Consequences

- Role scoping becomes enforceable where the framework supports it (a
  reviewer that cannot edit, an orchestrator that cannot run shell).
- Global rules such as "never `git push`" stay prose. That is a deliberate
  loss, not an oversight.
- Frameworks with no per-agent permission system (Cursor, Windsurf, Copilot,
  Aider, ...) keep the prose and receive a `permissions_not_enforced` compile
  warning (rule 32's plumbing) rather than a silent downgrade.
- `ask` has no per-agent form in Claude Code: it compiles to "tool available"
  and the user's own permission mode still prompts. Documented, not hidden.
- A new nullable column and a scanner/export/adapter change (see the plan).
