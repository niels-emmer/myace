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
- Known limits: `ask` is not expressible per agent in Claude Code; frameworks
  without a permission config only get the warning.

## Per-framework status (2026-11-28)

"Verified" means run against the real tool; "docs" means vendor documentation
only. Re-check both before editing an adapter — these formats move.

| Target | Per-agent restriction | Global rules | Evidence |
|---|---|---|---|
| Claude Code | `disallowedTools` (deny only) | sidecar + CLI merge | docs; **not run** (no usable auth in the test environment) |
| OpenCode (v1 and 2.x) | `permission:` frontmatter | sidecar + CLI merge into v1 `permission` *or* v2 `permissions` | **verified** on OpenCode 2.3.2: it translates v1 frontmatter and config (deprecated but supported); a v2-style config gets v2 rules prepended so the user's own rules win |
| Codex CLI | impossible — subagents inherit the parent's sandbox and approvals | real `.codex/rules/myace.rules` (a new file; Codex applies the most restrictive matching rule, so it can only tighten) | docs; **not run** (the locally installed binary is broken). Only shell rules with a trailing `*` map; the rest is warned |
| Cursor | Native subagents (`.cursor/agents/*.md`) have `readonly: true` (no edits, no state-changing shell). **Our adapter emits agents as `.mdc` rules, not subagents**, so there is nothing to attach it to. | `.cursor/cli.json` `permissions.deny` (`Shell(cmd)`) exists but is Cursor-CLI-only, user-owned, and forum reports disagree on whether a project file merges with or replaces the global one | docs + forum reports; not run |
| Copilot CLI | Native agents (`.github/agents/*.agent.md`) take a `tools` allow-list (aliases `execute`, `read`, `edit`, `search`, `agent`, `web`). **Our adapter emits agents as instruction files**, so no. | None possible as a file: persistent deny lives only in session flags (`--deny-tool`), admin managed settings, or `deniedUrls`; `permissions-config.json` stores approvals only | docs; not run |
| Kiro / Amazon Q CLI | JSON agents in `.kiro/agents/`; the schema is versioned (2.x `allowedTools`/`toolsSettings` vs v3 `permissions`, which needs `/upgrade-agent`). **Our Amazon Q adapter targets IDE rules**, not CLI agents. | none | docs; not run |
| Windsurf | none (rules only) | Allow/deny command lists are editor *user settings* (`windsurf.cascadeCommandsDenyList`), and a deny entry means "ask", not "block" | docs; not run |
| Cline | none | Per-category auto-approve is UI state; `.clineignore` is enforced only via a hook; rules are instructions, not permissions | docs; not run |
| Continue | none | Ask / Automatic / Excluded per tool is local UI state; no `config.yaml` key found | docs; not run |
| Goose | none | One user-level `permission.yaml`, not per agent, with an unofficial report that a corrupt file once meant allow-all | docs (partly unofficial) |
| Aider | none | Aider has no permission system (only `read:` read-only files, `yes-always`, `suggest-shell-commands`) | docs |
| Pi | none | Core Pi has none; third-party extensions add allow/deny/ask with their own files (`.pi/permissions.json` etc.) | third-party docs |

Two conclusions. First, **a file-based, restrict-only form exists for exactly the
targets already built** (Claude Code, OpenCode, Codex rules). Everywhere else
the control is user-level UI state, session flags or admin policy — a pack
cannot ship it without writing a user's own settings, which this ADR rules out.
Second, **Cursor and Copilot CLI would gain a real per-agent restriction only
if their adapters emitted native agent files** (`readonly`, `tools`) instead of
rule/instruction files. That changes what those downloads contain, so it is a
product decision, not a permissions tweak, and is deliberately not done here.

`permissions_not_enforced` names exactly what a target could not express, per
agent and per global rule.
