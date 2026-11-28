# ADR-0019: Agent-level permissions, compiled into agent files only

**Status:** Accepted (phase 1 and phase 2 implemented)

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
  Adopted as phase 2: global pack rules ship as a sidecar the framework never
  loads.
- **CLI-only tracked additive merge (`myace pull --apply-permissions`).**
  Adopted as phase 2, the only code path that writes user config: diffed,
  confirmed, additive, restrict-only, strict-JSON-only, recorded under
  `.myace/` and reversible (`myace permissions-remove`).
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

## Phase 2 (implemented)

- Global rules live in a pack's `permissions.json` -> `model_config`
  `permissions:default`; `translate_artifacts()` splits it off before any
  adapter runs and the adapter writes only a sidecar.
- Rules are `ask`/`deny` only; a `match` pattern is allowed for `execute`
  alone (e.g. `git push *`). `allow` and malformed entries are dropped at scan
  and again at compile.
- The merge keeps a user's own entries and values, never writes `allow`, skips
  a rule the user explicitly allows, and refuses a config with comments.
- Known limits: OpenCode v2's `permissions` array is not targeted; `ask` is
  not expressible per agent in Claude Code; frameworks without a permission
  config only get the warning.
