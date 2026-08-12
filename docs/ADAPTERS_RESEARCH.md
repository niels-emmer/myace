# Additional Adapters Research Report

## Summary

Nine potential adapter targets were investigated. Seven are viable for MyACE adapter development. Two are lower priority due to format overlap or limited configuration surface.

**Status update:** Windsurf, Cline, and GitHub Copilot (built as `copilot-cli`,
targeting the Copilot CLI rather than just the editor's
`.github/copilot-instructions.md` file, though it produces that file too)
have since been built — see `backend/app/adapters/`. A fourth adapter,
Codex CLI (`codex_cli.py`), was also built but doesn't appear anywhere in
this research's 9 investigated targets. pi.dev, Continue.dev, Aider, and
Roo Code remain unbuilt and are still the best-researched next candidates
(see [extending.md](extending.md#adding-a-target-adapter) for the
current adapter-adding checklist, including a step this research predates:
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

### 3. Continue.dev

| Property | Value |
|----------|-------|
| **Config format** | YAML (`config.yaml`), Markdown rules (`.continue/rules/*.md`) |
| **Global path** | `~/.continue/config.yaml` |
| **Project path** | `.continue/rules/` |
| **Models** | Multiple model roles (chat, edit, autocomplete) |
| **Rules** | Plain Markdown files in `.continue/rules/` directory |
| **Tools** | MCP server integration |
| **Docs** | https://docs.continue.dev/ |

**Adapter viability: HIGH.** Continue has a rich configuration surface with models, rules, and MCP tools. The rules system (Markdown files in `.continue/rules/`) maps cleanly to Canonical IR artifacts. The YAML config could be generated from `model_config` artifacts. Growing adoption in the VS Code ecosystem.

---

### 4. Aider

| Property | Value |
|----------|-------|
| **Config format** | YAML (`.aider.conf.yml`), Markdown (`CONVENTIONS.md`) |
| **Global path** | `~/.aider.conf.yml` |
| **Project path** | `.aider.conf.yml` + `CONVENTIONS.md` |
| **Conventions** | `CONVENTIONS.md` — plain Markdown coding guidelines |
| **Models** | Any LLM provider, configured in YAML |
| **Docs** | https://aider.chat/docs/ |

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

### 6. Roo Code

| Property | Value |
|----------|-------|
| **Config format** | Markdown rules, YAML/JSON custom modes |
| **Global path** | `~/.roo/rules/`, `~/.roo/rules-{mode}/` |
| **Project path** | `.roo/rules/`, `.roo/rules-{mode}/` |
| **Custom modes** | YAML/JSON config (`.roomodes` or `~/.roo/custom_modes.yaml`) |
| **AGENTS.md support** | Yes |
| **Docs** | https://docs.roocode.com/ |

**Adapter viability: HIGH.** Roo Code is a fork of Cline with additional mode system. The mode-specific rule directories (`rules-code/`, `rules-architect/`, etc.) add complexity but are well-documented. The custom modes feature (YAML/JSON) maps well to MyACE's `workflow` and `agent` artifacts. Growing rapidly (22K+ stars).

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
| 3 | **Continue.dev** | Rich config surface, VS Code native, growing enterprise adoption |
| 4 | **Aider** | Simplest to implement; terminal-native, complements CLI workflow |
| 5 | **pi.dev** | Native AGENTS.md support; skills system maps well to Canonical IR |
| 6 | **Roo Code** | More complex due to mode system; fork of Cline with additional features |
| 7 | **GitHub Copilot** — ✅ built (as `copilot-cli`) | Largest user base but simplest format; quick win for visibility |
| 8 | **Zed AI** | Monitor for maturity |
| 9 | **CodeGPT** | Already covered by Cursor adapter |

*(Codex CLI was also built — `backend/app/adapters/codex_cli.py` — despite
not appearing in this research.)*

---

## Key Insight: AGENTS.md as Universal Format

Several targets (pi.dev, Cline, Roo Code) natively support `AGENTS.md` as a configuration format. Since MyACE already compiles to `AGENTS.md` via the OpenCode adapter, many of these targets may already work partially without a dedicated adapter. The adapter work would focus on:
- Target-specific file layouts (directory structures)
- Format-specific features (YAML frontmatter, trigger modes, conditional rules)
- Settings/config files (JSON/YAML configs beyond AGENTS.md)
