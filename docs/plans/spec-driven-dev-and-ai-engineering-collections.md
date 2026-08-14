# Plan: Spec-Driven Development & AI/LLM Engineering Starter Collections

## Status

**Complete — merged to `main` via [PR #101](https://github.com/niels-emmer/myace/pull/101)
on 2026-08-14.** Both new `additional/` starter collections and the one
base-collection cherry-pick described below are implemented, seeded,
tested, and live. Nothing from this plan was deferred.

## Why

MyACE's discoverability depends on the starter-pack content being
genuinely good, not just structurally correct (README: "battle-tested,
well working artefacts, curated perfectly into collections"). Before this
plan, the 13 starter collections (3 base + 10 additional) covered
role-based specializations well but had no coverage of two things the
wider open-source agentic-coding ecosystem had converged on: spec-driven
development workflows, and AI/LLM engineering practices — notable given
MyACE itself is a tool for managing agent configs.

## Research: sources evaluated

| Source | License | Verdict |
|---|---|---|
| [github/spec-kit](https://github.com/github/spec-kit) | MIT | **Used.** Official GitHub project. Commands are plain markdown prompt bodies — near-identical shape to MyACE's `workflow` artifact type. Adapted (rewritten in MyACE's own voice/format), not copied — spec-kit's commands assume its own CLI scaffolding, numbered feature directories, and extension-hook system that don't apply here. |
| [anthropics/skills](https://github.com/anthropics/skills) | Mixed — most skills Apache-2.0, but the document-handling skills (docx/pdf/pptx/xlsx) are explicitly "source-available, not open source" | Evaluated, not directly drawn from in this pass — the Apache-2.0 skills didn't have a clean gap to fill beyond what `ai-engineering` already covers. Worth revisiting for a future pass. |
| [humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents) | Apache-2.0 | **Used** as citable principles (not file-for-file — it's an essay collection, not agent config) for the `agent-design-principles` skill. |
| [wshobson/agents](https://github.com/wshobson/agents) (38.8k★) | MIT | **Used for gap analysis only.** Plugin dirs map directly onto MyACE's scanner format, which made it easy to cross-check that `debugger`, `prompt-engineer`, `ai-engineer`, and `context-manager` were real gaps (via its `debugging-toolkit`, `llm-application-dev`, and `context-management` plugins) before authoring original content for them. |
| [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) (24.3k★) | MIT | Secondary cross-reference only, to sanity-check naming/scope against wshobson. |
| [bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) (52k★) | MIT code, but `TRADEMARK.md` restricts use of the "BMad" name/branding | **Skipped.** Its agent files are a custom YAML+markdown hybrid tied to its own runtime, not portable markdown — reproducing the pattern would mean writing original content anyway, and the name can't be reused. Not worth the cost relative to spec-kit, which is cleaner and equally credible. |
| [contains-studio/agents](https://github.com/contains-studio/agents) (12.4k★) | **None — no LICENSE file anywhere in the repo**, all-rights-reserved by default | **Not used — cannot legally copy.** Its product/design/marketing persona structure is a real gap in MyACE's collection lineup (no product manager, UX researcher, or growth persona anywhere in `collections/`), but nothing in that repo can be reused without contacting the authors. Flagged here as a **future opportunity to build original content** covering the same ground, not an import source. |
| [ruvnet/ruflo (claude-flow)](https://github.com/ruvnet/ruflo) (67.8k★), [SuperClaude Framework](https://github.com/SuperClaude-Org/SuperClaude_Framework) (23.8k★) | MIT | **Not applicable.** Both are executable orchestration tools/CLIs with their own runtimes, not markdown config artifacts — nothing to port into MyACE's Canonical IR. |
| [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) (40.6k★) | CC0-1.0 | Skipped — largely superseded by the newer `.mdc` rule format and highly variable crowd-sourced quality. |
| awesome-mcp-servers lists | Varies | Out of scope — MCP server configs are a `model_config` artifact concern, not this pass's focus. |

## What was built

### `collections/additional/spec-driven-dev/`

`AGENTS.md` (2 rules) + 7 commands, all prefixed `sdd-` to avoid colliding
with `base/software-engineer/commands/plan.md` (an unprefixed `plan.md`
here would have been silently deduplicated away per
[AGENTS.md rule 29](../../AGENTS.md) — `compile_profile()` dedupes by name
across every collection in a profile):

`sdd-constitution`, `sdd-specify`, `sdd-clarify`, `sdd-plan`, `sdd-tasks`,
`sdd-analyze`, `sdd-implement`.

### `collections/additional/ai-engineering/`

`AGENTS.md` (3 rules) + 3 agents (`prompt-engineer`, `ai-engineer`,
`context-manager`) + 1 skill (`agent-design-principles`). No naming
collisions with existing content — checked against every artifact name in
`collections/` before authoring.

### `collections/base/software-engineer/agents/debugger.md`

A systematic root-cause debugging persona — no existing collection had one
(`quick-reviewer`/`code-reviewer` are review-focused, not
investigation-focused).

## Registration and doc updates made

- `backend/app/services/seed_collections.py` — added both new collections
  to `STARTER_COLLECTIONS["additional"]` (categories: "Process &
  Methodology" and "AI/LLM Engineering", both new categories).
- `README.md` — bumped starter-pack counts (13 → 15, 3 base + 10 → 3 base +
  12 specializations) in both places it's stated, and added a Credits
  subsection citing spec-kit, 12-factor-agents, wshobson/agents, and
  VoltAgent's subagent collection.
- No changes needed to `docs/data-model.md`, `docs/invariants.md`, or
  `docs/adapters-research.md` — this was content-only, not a schema or
  adapter change. Checked for stale collection-count/name references
  across `docs/` and found none beyond `README.md`.

## Verification performed

- `pytest` (backend): 202 passed, 0 failed.
- `ruff check` clean; `mypy` showed zero *new* errors (confirmed via a
  stash/diff comparison against the pre-existing 13 errors in
  `scanner.py`/`seed_collections.py`, all unrelated to this change).
- Dev backend auto-reloaded and seeded both new collections correctly (9
  and 7 artifacts respectively, matching `AGENTS.md`-rules + agents/skills/
  commands counts).
- Ran every new file through the scanner's actual parsers
  (`_parse_agent_file`, `_parse_command_file`, `_parse_skill_file`,
  `_parse_agents_md`) directly — all parsed cleanly with expected names/
  types.
- Compiled a real profile (`software-engineer` + `spec-driven-dev` +
  `ai-engineering`) through `compile_profile()` to **claude-code** and
  **opencode**: 26 output files each, all new agents/commands present, and
  — the specific risk this plan called out — `.claude/commands/plan.md`
  (software-engineer's) and `.claude/commands/sdd-plan.md`
  (spec-driven-dev's) both survived side by side. Namespacing worked.
- Grepped the full `collections/` tree for duplicate agent filenames,
  command filenames, and skill `name:` frontmatter values after authoring:
  zero collisions introduced.

## Explicitly not done (by design, not oversight)

- **A product/design/marketing collection** inspired by contains-studio's
  structure — blocked on licensing (see table above), not scope. Building
  *original* content covering that ground is a real opportunity for a
  future pass.
- **Anthropic's Apache-2.0 skills** were evaluated but not drawn from — no
  clean gap emerged once `ai-engineering` was scoped. Worth a second look
  independently of this plan.
- **BMAD-METHOD-style base collection** — deliberately skipped; see table
  above for the format-mismatch and trademark reasoning.
