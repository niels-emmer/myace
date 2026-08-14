# Additional Adapters Research Report

## Summary

Nine potential adapter targets were investigated. Seven are viable for MyACE adapter development. Two are lower priority due to format overlap or limited configuration surface.

**Status update:** Windsurf, Cline, and GitHub Copilot (built as `copilot-cli`,
targeting the Copilot CLI rather than just the editor's
`.github/copilot-instructions.md` file, though it produces that file too)
have since been built — see `backend/app/adapters/`. A fourth adapter,
Codex CLI (`codex_cli.py`), was also built but doesn't appear anywhere in
this research's 9 investigated targets. Continue.dev and Aider (below) have
since been built too — see `backend/app/adapters/continue_dev.py`,
`aider.py`. Three more adapters not covered by this research were also
built directly from their own official docs: Goose (`goose.py`) and Amazon Q
Developer (`amazon_q.py`). A fourth, Sourcegraph Cody (`cody.py`), was also
built this way but **later retired (Aug 2026)** — see the retirement note
under item 11 below. **Roo Code was deliberately not built**, despite being
researched below and originally ranked priority #6: its extension was shut
down and its GitHub repo (`RooCodeInc/Roo-Code`) archived on 2026-05-15,
confirmed directly on GitHub. Its research entry is kept below, marked
discontinued, in case a community fork (e.g. ZooCode) later warrants
revisiting it. pi.dev and Zed AI remain the best-researched unbuilt,
still-viable candidates (see
[extending.md](extending.md#adding-a-target-adapter) for the current
adapter-adding checklist, including a step this research predates:
registering the new target in `ProfileCompileRequest`'s `Literal`).

**Aug 2026 documentation audit:** every shipped adapter's output was
re-verified against each target's current live docs (not just checked once
at build time), triggered by a "the compiled output doesn't look right"
concern. Result: **6 of 11 shipped adapters had drifted from or never
matched their target's real format** — `claude_code.py` (agents had no
frontmatter and likely weren't registering as valid subagents at all),
`cursor.py` (wrong frontmatter fields, rules risked not loading at all),
`codex_cli.py` (agents/workflows/config schema all wrong), `cline.py`
(none of its frontmatter fields matched Cline's real schema), and
`continue_dev.py`/`goose.py` (one stale path each) — all fixed; see each
adapter's "Update (Aug 2026 audit)" note below, and items 13–16 for the
three original built-in targets (Claude Code, Cursor, OpenCode) plus
Codex CLI, which never had dedicated research entries before this audit.
`windsurf.py` has a confirmed-stale finding (the tool rebranded to Devin
Desktop) not yet fixed, pending a naming decision — see
`docs/plans/starter-collections-improvements.md` for the full findings,
fix log, and open items.

---

## Viable Targets (high priority)

### 1. pi.dev (Pi Coding Agent)

| Property | Value |
|----------|-------|
| **Config format** | JSON (`settings.json`), Markdown (`AGENTS.md`, `SYSTEM.md`) |
| **Global path** | `~/.pi/agent/settings.json` |
| **Project path** | `.pi/settings.json` |
| **Instructions** | `AGENTS.md` (native support), `SYSTEM.md` (system prompt override) |
| **Skills** | Custom capability packages with instructions and tools |
| **Extensions** | TypeScript/JS extensions for custom behavior |
| **Docs** | https://pi.dev/docs/latest |

**Adapter viability: HIGH.** Pi reads `AGENTS.md` natively (same as OpenCode), so the adapter could focus on translating skills → Pi skills format, extensions → Pi extensions, and settings → `settings.json`. The skills system maps well to MyACE's Canonical IR `skill` artifacts.

---

### 2. Windsurf (Codeium) — BUILT (`backend/app/adapters/windsurf.py`)

| Property | Value |
|----------|-------|
| **Config format** | Markdown with YAML frontmatter (`.windsurf/rules/*.md`) |
| **Legacy format** | `.windsurfrules` (plain text, numbered rules) |
| **Global path** | `~/.codeium/windsurf/global_rules.md` |
| **Project path** | `.windsurf/rules/` (modern) or `.windsurfrules` (legacy) |
| **Rule triggers** | `always_on`, `manual`, `model_decision`, `glob` |
| **Docs** | https://docs.windsurf.com/ |

**Adapter viability: HIGH.** The modern `.windsurf/rules/*.md` format with YAML frontmatter is very similar to Cursor's `.cursor/rules/*.mdc`. The adapter could translate Canonical IR `rule`/`skill` artifacts into Windsurf rule files with appropriate trigger modes. The legacy `.windsurfrules` format is simpler but being phased out.

**Update (Aug 2026 audit):** Windsurf was acquired by Cognition AI and rebranded to **Devin Desktop** in June 2026 — `docs.windsurf.com` now redirects to `docs.devin.ai`, and `.windsurf/` is documented as a **legacy fallback** behind the now-preferred `.devin/` directory (`docs.devin.ai/desktop/cascade/memories`). The `glob` trigger value in the table above was already correctly researched, but the shipped adapter never implemented it (only `always_on`/`manual`/`model_decision`). Also newly confirmed: real per-file character limits — 12,000 for workspace rule files, 6,000 for the global rules file — which the adapter doesn't check. None of this has been fixed in `windsurf.py` yet; it's pending a decision on whether to add `devin-desktop`/`.devin/rules/` as the primary target (see `docs/plans/starter-collections-improvements.md`).

---

### 3. Continue.dev — BUILT (`backend/app/adapters/continue_dev.py`)

| Property | Value |
|----------|-------|
| **Config format** | YAML (`config.yaml` — `config.json` is deprecated), Markdown rules (`.continue/rules/*.md`), legacy `.prompt` files |
| **Global path** | `~/.continue/config.yaml` |
| **Project path** | `.continue/rules/`, `.continue/prompts/` |
| **Models** | Multiple model roles (chat, edit, autocomplete) |
| **Rules** | Markdown files with YAML frontmatter (`name`, `globs`, `description`, `alwaysApply`) in `.continue/rules/` |
| **Tools** | MCP server integration (`mcpServers` in `config.yaml`) |
| **Docs** | https://docs.continue.dev/ |

**Adapter viability: HIGH.** Continue has a rich configuration surface with models, rules, and MCP tools. The rules system (Markdown files in `.continue/rules/`) maps cleanly to Canonical IR artifacts. The YAML config could be generated from `model_config` artifacts. Growing adoption in the VS Code ecosystem.

**Update (Aug 2026 audit):** the "legacy `.prompt` files" format above is now stale — current Continue docs (`docs.continue.dev/customize/deep-dives/prompts`) show no standalone `.prompt` file extension. Prompts are Markdown+frontmatter files (an `invokable: true` frontmatter field makes one a slash command) referenced from a `prompts:` list in `config.yaml`. The adapter has been updated to write `.continue/prompts/<name>.md` (not `.prompt`) with `invokable: true`, but does **not** yet add the corresponding `prompts:` entry to `config.yaml` — the exact reference schema (a Continue Hub `uses:` block reference vs. a plain local file path) wasn't confirmed with full confidence during the audit, so it was left as a documented follow-up rather than guessed at.

---

### 4. Aider — BUILT (`backend/app/adapters/aider.py`)

| Property | Value |
|----------|-------|
| **Config format** | YAML (`.aider.conf.yml`), Markdown (`CONVENTIONS.md`) |
| **Global path** | `~/.aider.conf.yml` |
| **Project path** | `.aider.conf.yml` + `CONVENTIONS.md` |
| **Conventions** | `CONVENTIONS.md` — plain Markdown coding guidelines, loaded via `.aider.conf.yml`'s `read:` key |
| **Models** | Any LLM provider, configured in YAML (`model:` key) |
| **Docs** | https://aider.chat/docs/usage/conventions.html |

**Adapter viability: HIGH.** Aider's configuration is simple and well-defined. `CONVENTIONS.md` maps directly to Canonical IR `rule` artifacts. `.aider.conf.yml` maps to `model_config` artifacts. The adapter would be straightforward to implement.

---

### 5. Cline — BUILT (`backend/app/adapters/cline.py`)

| Property | Value |
|----------|-------|
| **Config format** | Markdown with optional YAML frontmatter |
| **Global path** | `~/.cline/rules/` |
| **Project path** | `.clinerules` (single file) or `.clinerules/` (directory) |
| **Conditional rules** | YAML frontmatter with `paths` glob patterns |
| **AGENTS.md fallback** | Yes — reads AGENTS.md when no `.clinerules/` exists |
| **Docs** | https://docs.cline.bot/ |

**Adapter viability: HIGH.** Cline's `.clinerules/` directory format is very similar to Cursor's `.cursor/rules/*.mdc`. The YAML frontmatter with glob-based conditional rules maps well to Canonical IR. Cline also supports AGENTS.md as a fallback, which MyACE already handles. Open-source with 1.2M+ MAU.

**Update (Aug 2026 audit):** this research was correct about `paths` being the real (and only) recognized frontmatter field, but the adapter as originally shipped had drifted from its own research — it emitted `title`/`description`/`type`/`priority`/`tags`/`globs`, none of which match. Since Canonical IR has no natural per-artifact path/glob-scoping concept to populate a real `paths` value with, the adapter now emits **no frontmatter at all** rather than guessed-at fields — confirmed via `docs.cline.bot/customization/cline-rules` that "rules without frontmatter are always active," which is the correct default for this project's content anyway.

---

### 6. Roo Code — DISCONTINUED, NOT BUILT

| Property | Value |
|----------|-------|
| **Config format** | Markdown rules, JSON custom modes |
| **Global path** | `~/.roo/rules/`, `~/.roo/rules-{mode}/` |
| **Project path** | `.roo/rules/`, `.roo/rules-{mode}/` |
| **Custom modes** | JSON config (`.roomodes`) — schema: `customModes[]` with required `slug`, `name`, `roleDefinition`, `groups`, optional `whenToUse`, `description`, `customInstructions`, `source` |
| **AGENTS.md support** | Yes |
| **Docs** | https://docs.roocode.com/ (dead — see below) |

**Adapter viability: N/A — the product is discontinued.** The Roo Code extension was shut down and its GitHub repo (`RooCodeInc/Roo-Code`) archived on 2026-05-15, confirmed directly on GitHub (24.4k stars, "Public archive", disclaimer: "The Roo Code Extension was shut down on May 15th... check out ZooCode ... and Cline"); `docs.roocode.com` no longer resolves. The config schema above was pulled from the archived repo's still-readable `schemas/roomodes.json` and kept here for reference, but a dedicated adapter was deliberately **not** built — building and maintaining an adapter for a dead product isn't worth the ongoing cost. If a community fork (ZooCode is the one the shutdown notice itself points to) gains real adoption and keeps this same config format, revisit building an adapter targeting the fork by name instead.

---

### 10. Goose — BUILT (`backend/app/adapters/goose.py`, not in original 9)

| Property | Value |
|----------|-------|
| **Config format** | Plain text/Markdown, single file |
| **Global path** | `~/.config/goose/.goosehints` |
| **Project path** | `.goosehints` (merged root-to-leaf with nested/global hints) |
| **Docs** | https://goose-docs.ai/docs/guides/context-engineering/using-goosehints/ |

**Adapter viability: MEDIUM-HIGH.** Extremely simple format — one file, no frontmatter, no per-artifact-type structure. All Canonical IR artifact types (except `model_config`, which Goose configures via `~/.config/goose/config.yaml` on the host rather than a repo file) fold into headed sections of a single `.goosehints`.

---

### 11. Sourcegraph Cody — BUILT (`backend/app/adapters/cody.py`, not in original 9)

| Property | Value |
|----------|-------|
| **Config format** | Markdown rule files, requested as `.sourcegraph/*.rule.md` |
| **Docs** | https://sourcegraph.com/docs/cody |

**Adapter viability: UNCERTAIN — verify before relying on this.** As of this research, Cody's live docs (and the public `sourcegraph/docs` GitHub repo) list chat, edit modes, auto-edit, the prompt library, MCP support, debug assistance, and context filters as documented capabilities — no dedicated "rules" page matching `.sourcegraph/*.rule.md` currently appears in the docs' capability index. The adapter was built to the requested spec with a conservative, minimal frontmatter (`description` only) rather than left unbuilt, but this is the one adapter in the whole set built without a docs page confirming the exact format. See `cody.py`'s module docstring.

**RETIRED (Aug 2026).** The verify-before-relying-on-this caveat above resolved to "don't." A follow-up documentation audit (see [`docs/plans/starter-collections-improvements.md`](plans/starter-collections-improvements.md)) confirmed `.sourcegraph/*.rule.md` was never a real Cody capability — the closest analog, the Prompt Library, is server-side/Enterprise-instance-hosted, not a git-committed file format at all — and separately that Cody Free/Pro were discontinued July 23, 2025, leaving only Cody Enterprise. `cody.py` was deleted and deregistered from `backend/app/adapters/__init__.py` rather than fixed, since there's no real target format to fix it toward and most `cody`-target users could no longer use Cody anyway.

---

### 12. Amazon Q Developer — BUILT (`backend/app/adapters/amazon_q.py`, not in original 9)

| Property | Value |
|----------|-------|
| **Config format** | Plain Markdown, one file per rule |
| **Project path** | `{project-root}/.amazonq/rules/*.md` |
| **Docs** | https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/context-project-rules.html |

**Adapter viability: HIGH.** Simple, clearly documented format: plain Markdown files (no frontmatter) in a fixed directory, auto-loaded as chat context. Backed by AWS's official docs with no ambiguity.

**Update (Aug 2026 audit):** still confirmed correct as shipped. Newly noted: Amazon Q CLI has since added native custom agents as **JSON** files at `.amazonq/cli-agents/{name}.json` (`tools`/permission/`resources` fields) and MCP config at `.amazonq/mcp.json`; rules are now loaded as "agent resources" referenced from that JSON rather than the only mechanism. The adapter's current `agent` → `.amazonq/rules/agent-{name}.md` fallback still works as a plain rules file — this is an enhancement opportunity (emit the more idiomatic native format), not a bug, and hasn't been implemented.

---

### 13. Claude Code — BUILT (`backend/app/adapters/claude_code.py`, MyACE's own primary target; not in original 9)

| Property | Value |
|----------|-------|
| **Rules format** | Markdown sections merged into a root `CLAUDE.md` — auto-loaded at session start |
| **Subagents format** | Markdown with **required** YAML frontmatter (`name`, `description`) under `.claude/agents/*.md` — identity comes from the `name` field, not the filename; a file with no frontmatter is not a valid subagent definition |
| **Skills format** | Markdown with YAML frontmatter (`name`, `description`) under `.claude/skills/<name>/SKILL.md` — **loaded on demand**, not injected into context up front |
| **Commands format** | Markdown with frontmatter (`description`, optionally `argument-hint`/`allowed-tools`/`model`) under `.claude/commands/*.md` — legacy but still supported; commands were merged into skills, so `.claude/skills/` is the current recommended home for both | 
| **Model config** | No repo-committed file — via `/model`, `--model`, the `ANTHROPIC_MODEL` env var, or the `model` field in `.claude/settings.json` |
| **Docs** | code.claude.com/docs/en/sub-agents, /slash-commands, /model-config |

**Adapter viability: was BROKEN, now FIXED (Aug 2026 audit).** As originally shipped, `_format_agent()` emitted a bare `# Name\n\nDescription\n\nBody` with **no frontmatter whatsoever** — since identity comes from the `name:` frontmatter field, agents likely didn't register as usable subagents at all. `.claude/workflows/*.md` and `.claude/models/*.md` were both invented paths that don't exist in Claude Code. Fixed: agents/skills now get real `name`/`description` frontmatter (via `yaml.safe_dump`); skills moved to on-demand `.claude/skills/<name>/SKILL.md` instead of being inlined into always-loaded `CLAUDE.md` (this also fixes a token-efficiency issue — real Claude Code skills are meant to be loaded only when relevant, not carried in every session's context); workflows moved to the still-supported legacy `.claude/commands/<name>.md`; `model_config` support dropped (no real target exists). This repo's own `CLAUDE.md`, which had asserted the wrong `.claude/workflows/` path as fact, was corrected in the same pass.

---

### 14. Cursor — BUILT (`backend/app/adapters/cursor.py`, not in original 9)

| Property | Value |
|----------|-------|
| **Config format** | Markdown with YAML frontmatter (`.mdc`) under `.cursor/rules/*.mdc` — the only current mechanism |
| **Frontmatter fields** | `description`, `globs`, `alwaysApply` — these three together determine whether/when a rule loads: `alwaysApply: true` = Always; a `description` with `alwaysApply: false` = Agent Requested (the agent decides whether to pull it in); `globs` = Auto Attached (loads when a matching file is open) |
| **Legacy format** | `.cursorrules` — no longer appears anywhere in current docs (likely fully dropped, not just deprecated) |
| **Docs** | cursor.com/docs/rules |

**Adapter viability: was BROKEN, now FIXED (Aug 2026 audit).** The adapter emitted `title`/`type`/`priority` frontmatter fields, none of which Cursor recognizes — a rule missing the real `description`/`globs`/`alwaysApply` fields risked not being loaded into context at all, not just being cosmetically wrong. It also still wrote the legacy `.cursorrules` file, and invented `.cursor/workflows/*.mdc`/`.cursor/models/*.mdc` paths that don't exist (Cursor has no documented workflow or model-config file concept). It also wrote skill/agent output to sequentially numbered files (`rule_000.mdc`, `rule_001.mdc`, …) instead of named ones, so every recompile could reshuffle unrelated files. Fixed: every artifact type now writes `.cursor/rules/<name>.mdc` (named, not numbered) with real `description`/`alwaysApply` frontmatter — `alwaysApply: true` for `rule`-type artifacts, `false` (Agent Requested mode) for skill/agent/workflow-type, which is a good semantic fit for on-demand capabilities. `.cursorrules` is no longer written; the invented workflow/model paths are gone.

---

### 15. Codex CLI — BUILT (`backend/app/adapters/codex_cli.py`, not in original 9)

| Property | Value |
|----------|-------|
| **Rules format** | `AGENTS.md` at the project root |
| **Skills format** | Markdown with YAML frontmatter (`name`, `description`) under `.agents/skills/<name>/SKILL.md` — scanned from cwd up to the repo root |
| **Subagents format** | **TOML** files under `.codex/agents/<name>.toml` (project) or `~/.codex/agents/` (personal) — required fields `name`, `description`, `developer_instructions` |
| **Workflows** | No such concept exists — skills + subagents + MCP are the only customization primitives |
| **Model/provider config** | `.codex/config.toml` — a top-level `model = "..."` string plus one `[model_providers.<id>]` table per provider (`name`, `base_url`, `env_key`, …); there is no `[models]` table |
| **Docs** | learn.chatgpt.com/docs/agents-md, /build-skills, /agent-configuration/subagents, /config-file/config-reference |

**Adapter viability: was BROKEN on 2 of 3 artifact types plus the config schema, now FIXED (Aug 2026 audit).** `AGENTS.md` and skills were already correct. Agents were wrong — Markdown at an invented `.agents/agents/*.md` path instead of real TOML at `.codex/agents/*.toml`. Workflows were wrong — written to an invented `.agents/workflows/*.md` path despite no such concept existing in Codex CLI at all. `config.toml` used an invented flat `[models]` table instead of the real `model =` + `[model_providers.<id>]` shape. Fixed: agents now render real TOML (with a small in-adapter string escaper, since no `toml` library is imported anywhere in this codebase); workflows are now skipped entirely with a code comment explaining why; `config.toml` now uses the real schema, picking the first `model_config` artifact as the active `model` (real config.toml has no equivalent of a model *list*). Separately-noted platform constraint, not fixed by the schema correction: project-scoped `.codex/config.toml` cannot override provider/auth/profile-selection config — that has to live in `~/.codex/config.toml`, so some fields in a compiled project-local file may not take effect regardless.

---

### 16. OpenCode — BUILT (`backend/app/adapters/opencode.py`, MyACE's own reference target; not in original 9)

| Property | Value |
|----------|-------|
| **Rules format** | `AGENTS.md` at the project root |
| **Skills format** | Markdown with YAML frontmatter (`name`, `description`, optional `license`/`compatibility`/`metadata`) under `.opencode/skills/<name>/SKILL.md` |
| **Agents format** | Markdown with frontmatter (`description`, optional `mode`/`model`) under `.opencode/agents/*.md` |
| **Commands format** | Markdown with frontmatter (`description`) under `.opencode/commands/*.md` |
| **Model/MCP config** | Single merged root `opencode.json` — `provider.<name>.models` and `mcp` keys |
| **Docs** | opencode.ai/docs (skills, agents, commands, config) |

**Adapter viability: confirmed correct, no changes needed (Aug 2026 audit).** Every frontmatter field re-verified against current docs, including that `metadata` is genuinely a free-form field (validating this adapter's use of it to stash `version`/`priority`/`tags`, which aren't part of OpenCode's own skill schema). This is also, not coincidentally, the format the starter collections in `collections/` are natively authored in — the scanner's parsers and this adapter's `translate()` are meant to round-trip cleanly against each other.

---

### 7. GitHub Copilot — BUILT (`backend/app/adapters/copilot_cli.py`, as `copilot-cli`)

| Property | Value |
|----------|-------|
| **Config format** | Markdown |
| **Project path** | `.github/copilot-instructions.md` |
| **Scope** | Single file, project-wide |
| **Docs** | https://docs.github.com/en/copilot/ |

**Adapter viability: MEDIUM.** Very simple format — a single Markdown file with instructions. Limited configuration surface compared to other targets. However, with 20M+ users, it's the most widely used AI coding tool. The adapter would be simple to implement but limited in what it can express.

**Update (Aug 2026 audit):** confirmed correct as shipped, and the configuration surface is larger than this original entry suggests — the adapter also writes path-scoped `.github/instructions/*.instructions.md` files (frontmatter: `applyTo` glob, `excludeAgent`) for skill/agent/workflow/model-config artifacts, not just the single repo-wide file. Separately, a hypothesis raised during the audit — that "Copilot **CLI**" (the terminal product this adapter is named for) might read a different file set than the IDE extension — was explicitly checked and refuted: `docs.github.com/.../copilot-cli/customize-copilot/add-custom-instructions` confirms the CLI reads the same files as the IDE, by design.

---

## Lower Priority Targets

### 8. Zed AI

| Property | Value |
|----------|-------|
| **Config format** | Text files |
| **Project path** | `.zed/rules/` |
| **Scope** | Directory of rule files |
| **Docs** | https://zed.dev/ |

**Adapter viability: MEDIUM.** Zed is a fast-growing editor written in Rust, but its AI features and rule format are less mature than the targets above. Worth monitoring but lower priority for adapter development.

### 9. CodeGPT

| Property | Value |
|----------|-------|
| **Config format** | Compatible with Cursor's `.cursorrules` |
| **Docs** | https://codegpt.co/ |

**Adapter viability: LOW.** CodeGPT uses the same format as Cursor, which MyACE already supports via the Cursor adapter. No separate adapter needed.

---

## Recommended Priority Order for Adapter Development

| Priority | Target | Rationale |
|----------|--------|-----------|
| 1 | **Windsurf** — ✅ built | Most similar to existing Cursor adapter; large and growing user base |
| 2 | **Cline** — ✅ built | Open-source, 1.2M+ MAU, `.clinerules/` format similar to Cursor |
| 3 | **Continue.dev** — ✅ built | Rich config surface, VS Code native, growing enterprise adoption |
| 4 | **Aider** — ✅ built | Simplest to implement; terminal-native, complements CLI workflow |
| 5 | **pi.dev** | Native AGENTS.md support; skills system maps well to Canonical IR |
| 6 | **Roo Code** — ❌ discontinued, not built | Product shut down 2026-05-15; no longer worth building for |
| 7 | **GitHub Copilot** — ✅ built (as `copilot-cli`) | Largest user base but simplest format; quick win for visibility |
| 8 | **Zed AI** | Monitor for maturity |
| 9 | **CodeGPT** | Already covered by Cursor adapter |

*(Codex CLI, Goose, and Amazon Q Developer were also built —
`backend/app/adapters/{codex_cli,goose,amazon_q}.py` — despite not
appearing in this research's original 9 investigated targets. A fourth,
Sourcegraph Cody, was built the same way and later retired — see item 11
above.)*

---

## Key Insight: AGENTS.md as Universal Format

Several targets (pi.dev, Cline, Roo Code) natively support `AGENTS.md` as a configuration format. Since MyACE already compiles to `AGENTS.md` via the OpenCode adapter, many of these targets may already work partially without a dedicated adapter. The adapter work would focus on:
- Target-specific file layouts (directory structures)
- Format-specific features (YAML frontmatter, trigger modes, conditional rules)
- Settings/config files (JSON/YAML configs beyond AGENTS.md)
