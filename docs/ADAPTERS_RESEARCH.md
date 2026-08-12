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
built directly from their own official docs: Goose (`goose.py`),
Sourcegraph Cody (`cody.py`), and Amazon Q Developer (`amazon_q.py`).
**Cody caveat:** Sourcegraph's current public docs don't list a dedicated
"rules"/`.rule.md` capability matching the `.sourcegraph/*.rule.md` format
this adapter targets — see `cody.py`'s module docstring before relying on
it in production. **Roo Code was deliberately not built**, despite being
researched below and originally ranked priority #6: its extension was shut
down and its GitHub repo (`RooCodeInc/Roo-Code`) archived on 2026-05-15,
confirmed directly on GitHub. Its research entry is kept below, marked
discontinued, in case a community fork (e.g. ZooCode) later warrants
revisiting it. pi.dev and Zed AI remain the best-researched unbuilt,
still-viable candidates (see
[extending.md](extending.md#adding-a-target-adapter) for the current
adapter-adding checklist, including a step this research predates:
registering the new target in `ProfileCompileRequest`'s `Literal`).

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

---

### 12. Amazon Q Developer — BUILT (`backend/app/adapters/amazon_q.py`, not in original 9)

| Property | Value |
|----------|-------|
| **Config format** | Plain Markdown, one file per rule |
| **Project path** | `{project-root}/.amazonq/rules/*.md` |
| **Docs** | https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/context-project-rules.html |

**Adapter viability: HIGH.** Simple, clearly documented format: plain Markdown files (no frontmatter) in a fixed directory, auto-loaded as chat context. Backed by AWS's official docs with no ambiguity.

---

### 7. GitHub Copilot — BUILT (`backend/app/adapters/copilot_cli.py`, as `copilot-cli`)

| Property | Value |
|----------|-------|
| **Config format** | Markdown |
| **Project path** | `.github/copilot-instructions.md` |
| **Scope** | Single file, project-wide |
| **Docs** | https://docs.github.com/en/copilot/ |

**Adapter viability: MEDIUM.** Very simple format — a single Markdown file with instructions. Limited configuration surface compared to other targets. However, with 20M+ users, it's the most widely used AI coding tool. The adapter would be simple to implement but limited in what it can express.

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

*(Codex CLI, Goose, Sourcegraph Cody, and Amazon Q Developer were also
built — `backend/app/adapters/{codex_cli,goose,cody,amazon_q}.py` —
despite not appearing in this research's original 9 investigated targets.)*

---

## Key Insight: AGENTS.md as Universal Format

Several targets (pi.dev, Cline, Roo Code) natively support `AGENTS.md` as a configuration format. Since MyACE already compiles to `AGENTS.md` via the OpenCode adapter, many of these targets may already work partially without a dedicated adapter. The adapter work would focus on:
- Target-specific file layouts (directory structures)
- Format-specific features (YAML frontmatter, trigger modes, conditional rules)
- Settings/config files (JSON/YAML configs beyond AGENTS.md)
