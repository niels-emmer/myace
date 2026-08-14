# Adapter Targets

## Summary

MyACE ships 11 target adapters (`backend/app/adapters/`), each translating
the Canonical IR into a real, currently-supported file format for its
target framework. Every adapter's output has been verified directly
against that target's current live documentation (most recently in a
full pass in Aug 2026) — see each entry below for its confirmed format,
doc citation, and any open items.

To add a new adapter, see [extending.md](extending.md#adding-a-target-adapter)
for the checklist (including registering the new target in
`ProfileCompileRequest`'s `Literal`). See [Future Plans](#future-plans)
below for known candidates that aren't built yet.

---

## Fully built and verified adapters

### 1. Windsurf (Codeium)

`backend/app/adapters/windsurf.py`

| Property | Value |
|----------|-------|
| **Config format** | Markdown with YAML frontmatter (`.windsurf/rules/*.md`) |
| **Legacy format** | `.windsurfrules` (plain text, numbered rules) |
| **Global path** | `~/.codeium/windsurf/global_rules.md` |
| **Project path** | `.windsurf/rules/` (modern) or `.windsurfrules` (legacy) |
| **Rule triggers** | `always_on`, `manual`, `model_decision`, `glob` |
| **Docs** | https://docs.windsurf.com/ |

Translates Canonical IR `rule`/`skill` artifacts into `.windsurf/rules/*.md`
files with YAML frontmatter, using the `always_on`/`manual`/`model_decision`
trigger modes.

**Known limitations:** Windsurf was acquired by Cognition AI and rebranded
to **Devin Desktop** — `docs.windsurf.com` now redirects to
`docs.devin.ai`, and `.windsurf/` is documented as a legacy fallback behind
the now-preferred `.devin/` directory. The adapter still targets the legacy
path only, doesn't implement the `glob` trigger mode, and doesn't enforce
the real per-file character limits (12,000 for workspace rule files, 6,000
for the global rules file). See [Future Plans](#future-plans).

---

### 2. Continue.dev

`backend/app/adapters/continue_dev.py`

| Property | Value |
|----------|-------|
| **Config format** | YAML (`config.yaml` — `config.json` is deprecated), Markdown rules (`.continue/rules/*.md`) |
| **Global path** | `~/.continue/config.yaml` |
| **Project path** | `.continue/rules/`, `.continue/prompts/` |
| **Models** | Multiple model roles (chat, edit, autocomplete) |
| **Rules** | Markdown files with YAML frontmatter (`name`, `globs`, `description`, `alwaysApply`) in `.continue/rules/` |
| **Prompts** | Markdown+frontmatter files in `.continue/prompts/<name>.md`; `invokable: true` makes one a slash command |
| **Tools** | MCP server integration (`mcpServers` in `config.yaml`) |
| **Docs** | https://docs.continue.dev/ |

Writes rules to `.continue/rules/*.md` and prompts to
`.continue/prompts/<name>.md`, and can generate `config.yaml` model config
from `model_config` artifacts.

**Known limitations:** prompts aren't yet cross-referenced from a
`prompts:` list in `config.yaml` — the exact reference schema (a Continue
Hub `uses:` block vs. a plain local file path) hasn't been confirmed with
full confidence. See [Future Plans](#future-plans).

---

### 3. Aider

`backend/app/adapters/aider.py`

| Property | Value |
|----------|-------|
| **Config format** | YAML (`.aider.conf.yml`), Markdown (`CONVENTIONS.md`) |
| **Global path** | `~/.aider.conf.yml` |
| **Project path** | `.aider.conf.yml` + `CONVENTIONS.md` |
| **Conventions** | `CONVENTIONS.md` — plain Markdown coding guidelines, loaded via `.aider.conf.yml`'s `read:` key |
| **Models** | Any LLM provider, configured in YAML (`model:` key) |
| **Docs** | https://aider.chat/docs/usage/conventions.html |

Maps Canonical IR `rule` artifacts directly to `CONVENTIONS.md` and
`model_config` artifacts to `.aider.conf.yml`'s `model:` key. The simplest
adapter in the set, with no known open items.

---

### 4. Cline

`backend/app/adapters/cline.py`

| Property | Value |
|----------|-------|
| **Config format** | Markdown, no frontmatter |
| **Global path** | `~/.cline/rules/` |
| **Project path** | `.clinerules` (single file) or `.clinerules/` (directory) |
| **AGENTS.md fallback** | Yes — Cline reads AGENTS.md when no `.clinerules/` exists |
| **Docs** | https://docs.cline.bot/ |

Writes `.clinerules/*.md` files. Per
`docs.cline.bot/customization/cline-rules`, `paths` is the only real
recognized frontmatter field, and rules without frontmatter are always
active. Since Canonical IR has no per-artifact path/glob-scoping concept to
populate a real `paths` value with, the adapter emits no frontmatter at
all rather than guessed-at fields — the correct default for this
project's content anyway.

---

### 5. Goose

`backend/app/adapters/goose.py`

| Property | Value |
|----------|-------|
| **Config format** | Plain text/Markdown, single file |
| **Global path** | `~/.config/goose/.goosehints` |
| **Project path** | `.goosehints` (merged root-to-leaf with nested/global hints) |
| **Docs** | https://goose-docs.ai/docs/guides/context-engineering/using-goosehints/ |

Extremely simple format — one file, no frontmatter, no per-artifact-type
structure. Every Canonical IR artifact type except `model_config` (which
Goose configures via `~/.config/goose/config.yaml` on the host rather than
a repo file) folds into a headed section of a single `.goosehints`.

---

### 6. Amazon Q Developer

`backend/app/adapters/amazon_q.py`

| Property | Value |
|----------|-------|
| **Config format** | Plain Markdown, one file per rule |
| **Project path** | `{project-root}/.amazonq/rules/*.md` |
| **Docs** | https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/context-project-rules.html |

Writes plain Markdown files (no frontmatter) into a fixed directory,
auto-loaded as chat context. Simple, clearly documented format backed by
AWS's official docs with no ambiguity.

**Known limitations:** Amazon Q CLI has since added native custom agents
as **JSON** files at `.amazonq/cli-agents/{name}.json` (`tools`/permission/
`resources` fields) and MCP config at `.amazonq/mcp.json`, with rules now
loadable as "agent resources" referenced from that JSON. The adapter's
current `agent` → `.amazonq/rules/agent-{name}.md` fallback still works as
a plain rules file; emitting the more idiomatic native JSON format is an
open enhancement. See [Future Plans](#future-plans).

---

### 7. Claude Code

`backend/app/adapters/claude_code.py` — MyACE's own primary target.

| Property | Value |
|----------|-------|
| **Rules format** | Markdown sections merged into a root `CLAUDE.md` — auto-loaded at session start |
| **Subagents format** | Markdown with **required** YAML frontmatter (`name`, `description`) under `.claude/agents/*.md` — identity comes from the `name` field, not the filename |
| **Skills format** | Markdown with YAML frontmatter (`name`, `description`) under `.claude/skills/<name>/SKILL.md` — **loaded on demand**, not injected into context up front |
| **Commands format** | Markdown with frontmatter (`description`, optionally `argument-hint`/`allowed-tools`/`model`) under `.claude/commands/*.md` — legacy but still supported; commands were merged into skills, so `.claude/skills/` is the current recommended home for both |
| **Model config** | No repo-committed file — via `/model`, `--model`, the `ANTHROPIC_MODEL` env var, or the `model` field in `.claude/settings.json` |
| **Docs** | [sub-agents](https://code.claude.com/docs/en/sub-agents), [slash-commands](https://code.claude.com/docs/en/slash-commands), [model-config](https://code.claude.com/docs/en/model-config) |

Agents and skills get real `name`/`description` frontmatter; skills are
written to on-demand `.claude/skills/<name>/SKILL.md` rather than being
inlined into the always-loaded `CLAUDE.md`, which keeps sessions
token-efficient. Workflows go to the still-supported legacy
`.claude/commands/<name>.md`. There is no real `model_config` target in
Claude Code, so that artifact type isn't compiled for this adapter.

---

### 8. Cursor

`backend/app/adapters/cursor.py`

| Property | Value |
|----------|-------|
| **Config format** | Markdown with YAML frontmatter (`.mdc`) under `.cursor/rules/*.mdc` — the only current mechanism |
| **Frontmatter fields** | `description`, `globs`, `alwaysApply` — together these determine whether/when a rule loads: `alwaysApply: true` = Always; a `description` with `alwaysApply: false` = Agent Requested (the agent decides whether to pull it in); `globs` = Auto Attached (loads when a matching file is open) |
| **Docs** | [cursor.com/docs/rules](https://cursor.com/docs/rules) |

Every artifact type is written to a named file, `.cursor/rules/<name>.mdc`,
with real `description`/`globs`/`alwaysApply` frontmatter —
`alwaysApply: true` for `rule`-type artifacts, `false` (Agent Requested
mode) for skill/agent/workflow-type. The legacy `.cursorrules` format no
longer appears anywhere in current Cursor docs and is not written.

---

### 9. Codex CLI

`backend/app/adapters/codex_cli.py`

| Property | Value |
|----------|-------|
| **Rules format** | `AGENTS.md` at the project root |
| **Skills format** | Markdown with YAML frontmatter (`name`, `description`) under `.agents/skills/<name>/SKILL.md` — scanned from cwd up to the repo root |
| **Subagents format** | **TOML** files under `.codex/agents/<name>.toml` (project) or `~/.codex/agents/` (personal) — required fields `name`, `description`, `developer_instructions` |
| **Workflows** | No such concept exists in Codex CLI — skills + subagents + MCP are the only customization primitives |
| **Model/provider config** | `.codex/config.toml` — a top-level `model = "..."` string plus one `[model_providers.<id>]` table per provider (`name`, `base_url`, `env_key`, …); there is no `[models]` table |
| **Docs** | [agents-md](https://learn.chatgpt.com/docs/agents-md), [build-skills](https://learn.chatgpt.com/docs/build-skills), [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [config-reference](https://learn.chatgpt.com/docs/config-file/config-reference) |

Writes `AGENTS.md`, skills to `.agents/skills/<name>/SKILL.md`, and
subagents as real TOML at `.codex/agents/<name>.toml` (via a small
in-adapter string escaper, since no `toml` library is imported anywhere in
this codebase). Workflows are skipped entirely, since Codex CLI has no
equivalent concept. `config.toml` follows the real schema, picking the
first `model_config` artifact as the active `model`.

**Known limitation:** project-scoped `.codex/config.toml` cannot override
provider/auth/profile-selection config — that has to live in
`~/.codex/config.toml`, so some fields in a compiled project-local file
may not take effect regardless of what MyACE generates.

---

### 10. OpenCode

`backend/app/adapters/opencode.py` — MyACE's own reference target.

| Property | Value |
|----------|-------|
| **Rules format** | `AGENTS.md` at the project root |
| **Skills format** | Markdown with YAML frontmatter (`name`, `description`, optional `license`/`compatibility`/`metadata`) under `.opencode/skills/<name>/SKILL.md` |
| **Agents format** | Markdown with frontmatter (`description`, optional `mode`/`model`) under `.opencode/agents/*.md` |
| **Commands format** | Markdown with frontmatter (`description`) under `.opencode/commands/*.md` |
| **Model/MCP config** | Single merged root `opencode.json` — `provider.<name>.models` and `mcp` keys |
| **Docs** | [opencode.ai/docs](https://opencode.ai/docs) (skills, agents, commands, config) |

This is, not coincidentally, the format the starter collections in
`collections/` are natively authored in — the scanner's parsers and this
adapter's `translate()` are meant to round-trip cleanly against each
other. `metadata` is a genuinely free-form field in OpenCode's own skill
schema, which this adapter uses to stash `version`/`priority`/`tags`.

---

### 11. GitHub Copilot

`backend/app/adapters/copilot_cli.py` — target name `copilot-cli`.

| Property | Value |
|----------|-------|
| **Config format** | Markdown |
| **Project path** | `.github/copilot-instructions.md` (repo-wide), `.github/instructions/*.instructions.md` (path-scoped, frontmatter: `applyTo` glob, `excludeAgent`) |
| **Scope** | One repo-wide file plus one path-scoped file per skill/agent/workflow/model-config artifact |
| **Docs** | https://docs.github.com/en/copilot/ |

Writes the single project-wide `.github/copilot-instructions.md` file
(simple Markdown, no frontmatter) plus path-scoped
`.github/instructions/*.instructions.md` files for every other artifact
type. Copilot **CLI** (the terminal product this adapter targets) reads
the same file set as the IDE extension, by design — confirmed via
`docs.github.com/.../copilot-cli/customize-copilot/add-custom-instructions`.

---

## Future Plans

MyACE doesn't yet ship adapters for every AI coding tool. If you use a
framework not listed above, please open a PR, issue, or discussion — the
[adapter-adding checklist](extending.md#adding-a-target-adapter) walks
through what's involved, and a new adapter is usually a self-contained
addition: one file implementing `BaseAdapter`, registered in
`backend/app/adapters/__init__.py`, plus a `Literal` update in
`ProfileCompileRequest`.

**Known unbuilt-but-viable candidates:**

- **pi.dev** — reads `AGENTS.md` natively (like OpenCode); config lives in
  `settings.json` at `~/.pi/agent/settings.json` / `.pi/settings.json`;
  its skills system maps well to Canonical IR `skill` artifacts. Docs:
  [pi.dev/docs/latest](https://pi.dev/docs/latest)
- **Zed AI** — plain text rule files under `.zed/rules/`; the format is
  comparatively immature and worth re-checking against current docs
  before building. Docs: [zed.dev](https://zed.dev/)
- **CodeGPT** — uses the same `.cursorrules`-compatible format as Cursor,
  so it likely doesn't need a dedicated adapter — but this hasn't been
  re-verified against CodeGPT's current docs. Docs:
  [codegpt.co](https://codegpt.co/)

**Open items on existing adapters** — also good starting points for a
contribution:

- **Windsurf** rebranded to Devin Desktop; `windsurf.py` still targets the
  legacy `.windsurf/rules/` path rather than the now-preferred
  `.devin/rules/` — needs a naming decision before switching the primary
  target.
- **Continue.dev** prompts aren't yet cross-referenced from `config.yaml`'s
  `prompts:` list — the exact reference schema needs confirming.
- **Amazon Q Developer** could emit the newer native
  `.amazonq/cli-agents/*.json` agent format instead of falling back to a
  plain rules file.

---

## Key Insight: AGENTS.md as a Universal Format

Several targets (pi.dev, Cline) natively support `AGENTS.md` as a
configuration format. Since MyACE already compiles to `AGENTS.md` via the
OpenCode and Codex CLI adapters, these targets may already work partially
without a dedicated adapter. Adapter work for an `AGENTS.md`-native target
mostly comes down to:
- Target-specific file layouts (directory structures)
- Format-specific features (YAML frontmatter, trigger modes, conditional rules)
- Settings/config files (JSON/YAML configs beyond AGENTS.md)
