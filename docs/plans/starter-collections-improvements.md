# Plan: Starter Collections — Follow-Up Improvements

## Status

**Partially complete — merged to `main` via [PR #95](https://github.com/niels-emmer/myace/pull/95)
on 2026-08-14.** Everything marked ✅ below is done and live on `main`.
Still open: `windsurf.py` (blocked on a naming decision), `amazon_q.py`'s
native custom-agent enhancement, and items 1/2/4/5 from the "Proposed
approach" list (YAML-error strictness, a regression test suite for the
collision class of bug, description/Purpose redundancy in skills, and
`target_compatibility`'s fate) — none of those four have been started.

Written up after a full content review of all 13 starter
collections (`collections/base/`, `collections/additional/`) and a same-day
fix pass that resolved the review's concrete findings (factual error, three
cross-collection name collisions, a stale model reference, a missing
compatibility target, a silently-swallowed YAML parse error, and an
`N-A`/`N/A` inconsistency — see `git log` for that commit and
[`AGENTS.md`](../../AGENTS.md) rule 29 / [`docs/debugging.md`](../debugging.md)
for the collision mechanism those fixes address).

This plan captures what's left: structural improvements that are bigger than
a same-session fix, plus a completed real-docs audit (item 3 below) of
whether the compile adapters (`backend/app/adapters/*.py`) actually produce
what each target framework expects. Short version: **9 of 12 adapters
needed code changes** — 3 (`claude_code.py`, `cursor.py`, `codex_cli.py`)
were outright broken (real content likely failed to load in the target tool
at all), `windsurf.py` targets a rebranded/legacy product path, `cline.py`
and `cody.py` emitted fields/formats the target doesn't recognize, and
`continue_dev.py`/`goose.py` have one stale path each. Only `copilot_cli.py`,
`aider.py`, and `opencode.py` were confirmed fully correct as shipped.

**⏱ 2026-08 progress update (session ran across a token-budget reset —
resume here):** **6 of the 9 adapters that needed fixes are now done**:
`claude_code.py`, `cursor.py`, `cline.py`, `continue_dev.py`, `goose.py`,
and `codex_cli.py` are all fixed and verified (logic-traced against
expected output shapes — see item 3's per-adapter sections below, each
marked ✅ DONE; backend test suite updated to match throughout). `cody.py`
is fully retired — deleted, deregistered from `backend/app/adapters/
__init__.py`, removed from `profile.py`'s target `Literal`, removed from
all 81 starter-collection `compatibility` lists, and
`README.md`/`docs/architecture.md`/`docs/ADAPTERS_RESEARCH.md` updated to
match throughout (not just for `cody` — the `README.md` adapter table was
kept in sync with each adapter fix as it landed). This repo's own
`CLAUDE.md` (the wrong `.claude/workflows/*.md` claim) is also corrected.
**Still open**: `windsurf.py` (needs a product-naming judgment call before
fixing — see its section below and the Open Questions) and `amazon_q.py`'s
native custom-agent enhancement (not a bug, an improvement). **Also still
fully open**: items 1, 2, 4, 5 from this plan (YAML-error strictness, the
regression test suite, description/Purpose redundancy trim,
`target_compatibility`'s fate) — none of those have been started.
**Important caveat that applies to every "FIXED" adapter above**: none of
this was verified against the real backend test suite (`pytest`) — this
environment doesn't have `sqlmodel`/`pydantic`/the rest of the backend's
dependencies installed, so every fix was verified by hand-syntax-checking
(`python3 -m py_compile`) and logic-tracing the exact `translate()` logic
in a standalone reimplementation asserted against expected output. That's
good evidence but not the same as a green `pytest` run — **run the real
suite (`cd backend && pytest tests/test_adapters.py -v`) before trusting
this as fully verified**, and fix anything that surfaces.

## Problem

The fix pass closed the specific issues found by manual review, but three
of them point at systemic gaps rather than one-off content bugs:

1. **Silent failure modes.** The YAML bug in `swiftui-conventions/SKILL.md`
   degraded silently — wrong name, wrong priority, narrowed compatibility,
   empty description — with no error anywhere. `_parse_yaml_frontmatter()`
   swallows `yaml.YAMLError` unconditionally. Nothing catches the next one.
2. **No regression protection.** The collision-detection and
   parse-validation checks that caught this round of bugs were ad hoc shell
   scripts and a throwaway Python reimplementation, run once, by hand. They
   aren't part of the test suite, so nothing stops the same class of bug
   from being reintroduced.
3. **Unverified compile output.** `backend/app/adapters/*.py` are hardcoded
   translators from Canonical IR to each target framework's on-disk format.
   Some already carry "Verified against `<docs URL>`" docstrings from a
   prior pass (`aider.py`, `goose.py`, `cody.py` — though `cody.py` explicitly
   flags its own uncertainty, `amazon_q.py`, `continue_dev.py`, `opencode.py`);
   others (`claude_code.py`, `cursor.py`, `windsurf.py`, `cline.py`,
   `codex_cli.py`, `copilot_cli.py`) have no such citation. `app/adapters/
   __init__.py`'s module docstring already flags this as a "KNOWN GAP":
   adapters are hardcoded and don't consume the `doc_verifier`/
   `DocCacheEntry` mechanism that periodically fetches real framework docs.

## Goals

- Close the silent-failure gap so a broken artifact fails loudly (CI or
  seed-time), not invisibly.
- Turn today's manual verification scripts into a real, repeatable test.
- Get a docs-backed answer on which adapters' output actually matches their
  target framework's real, current format — and fix the ones that don't.
- Reduce content redundancy and dead metadata so compiled profiles carry
  less unnecessary token weight per session.

## Non-goals

- Rewriting the adapter architecture (rule 3's stateless-adapter design is
  fine as-is) — this is about correctness of existing adapters' output, not
  changing how adapters are registered or invoked.
- Wiring adapters to consume `DocCacheEntry` dynamically (the `__init__.py`
  docstring's suggested future enhancement) — worth doing eventually, but
  out of scope here; this plan is about getting today's hardcoded output
  correct first.

## Proposed approach

### 1. Stop silently swallowing YAML frontmatter errors

`_parse_yaml_frontmatter()` in `backend/app/services/scanner.py` (and its
CLI twin in `cli/myace_cli/scanner.py` — keep them in sync per rule 8)
currently does:

```python
try:
    frontmatter = yaml.safe_load(match.group(1)) or {}
except yaml.YAMLError:
    frontmatter = {}
```

For the starter-pack seeding path specifically (`_scan_starter_collection`
in `backend/app/services/seed_collections.py`, whose inputs are trusted,
hardcoded, first-party content — not arbitrary user uploads), a parse
failure should be loud: log an error with the file path at minimum, and
consider raising so a broken starter file fails backend startup / CI rather
than seeding silently-degraded content. The general-purpose scanner path
(used for arbitrary user-scanned directories via the API/CLI) should stay
lenient — a user's real-world project shouldn't 500 because one file has
imperfect frontmatter — but should at least log a warning so it's
discoverable instead of invisible.

### 2. Add `tests/test_starter_collections.py` to the backend suite

Turn the throwaway verification script from the fix pass into a real,
repeatable test, exercising the actual `_scan_starter_collection()` /
`compile_profile()` code paths (not a reimplementation, so it can't drift
from what production actually does):

- Every `collections/{base,additional}/*/` directory parses with zero YAML
  errors and produces a non-empty artifact list.
- Every artifact name (skill `name:` field, agent/workflow file stem, rule
  `##` heading) is unique **across every collection**, not just within one
  — this is what directly catches a repeat of the `security-auditor` /
  `docs-writer` / `Security Checklist` class of bug before merge.
- Every directory in `collections/{base,additional}/` has a matching entry
  in `seed_collections.py`'s `STARTER_COLLECTIONS`, and vice versa (catches
  the registry/disk drift class of bug, even though today they match).
- Every `compatibility` list is well-formed and (if the field stays —
  see item 5) contains every currently-registered adapter target.

### 3. Adapter format audit against real framework docs

**Complete** — three parallel research passes against each framework's live,
current documentation (Aug 2026), cross-checked against the ground truth
extracted directly from `backend/app/adapters/*.py` source. Verdict per
adapter, most-broken first:

| Adapter | Verdict | Real, current format |
|---|---|---|
| `claude_code.py` | ✅ **FIXED** (was broken — 3 issues) | See below |
| `cursor.py` | ✅ **FIXED** (was broken — 3 issues) | See below |
| `windsurf.py` | **Stale** — tool rebranded (still open — see below) | See below |
| `cline.py` | ✅ **FIXED** (was: wrong fields) | See below |
| `codex_cli.py` | ✅ **FIXED** (was: broken — 2 of 3 artifact types + config schema wrong) | See below |
| `cody.py` | ✅ **RETIRED** (was: fictional format + product mostly discontinued) | See below |
| `continue_dev.py` | ✅ **FIXED** (was: one stale path) | See below |
| `goose.py` | ✅ **FIXED** (was: one real gap) | See below |
| `amazon_q.py` | Correct, missing a newer native format | See below |
| `copilot_cli.py` | **Confirmed correct** | No changes needed |
| `aider.py` | **Confirmed correct** | No changes needed |
| `opencode.py` | **Confirmed correct** | No changes needed |

#### `claude_code.py` — ✅ FIXED (was broken, highest priority — this is MyACE's own tool)

**Done:** `backend/app/adapters/claude_code.py` rewritten. Agents now emit
`name`+`description` YAML frontmatter (via `yaml.safe_dump`, not raw
f-string interpolation, so a colon in a description can't break the
frontmatter). Skills now write `.claude/skills/<name>/SKILL.md`
(on-demand-loaded, no longer inlined into `CLAUDE.md` — this also closes
the token-efficiency gap from the original review). Workflows now write
`.claude/commands/<name>.md` (the legacy-but-still-working slash command
path). `model_config` is now skipped, matching the `amazon_q.py`/`goose.py`
precedent, with the reasoning in the module docstring. `backend/tests/
test_adapters.py`'s `TestClaudeCodeAdapter` updated to match (skill file
location + frontmatter, agent frontmatter, workflow path, model_config
skip) and logic-traced against expected output (couldn't run real pytest —
`sqlmodel`/`pydantic` aren't installed in this environment — so this was
verified by re-implementing the exact `translate()` logic standalone and
asserting against it; **run the real test suite once dependencies are
available to be certain**). This repo's own `CLAUDE.md` corrected too (see
item 4 in the original list below, now resolved).

Original findings, for reference:

1. **Agents likely don't register at all.** Real subagents
   (`docs: code.claude.com/docs/en/sub-agents`) require YAML frontmatter —
   identity comes from the `name:` field, not the filename, and `name` +
   `description` are both required. `_format_agent()` currently emits a
   bare `# Name\n\nDescription\n\nBody` with **no frontmatter whatsoever**.
   Fix: add a frontmatter block with at least `name` and `description`.
2. **`.claude/workflows/*.md` doesn't exist.** Claude Code merged commands
   into skills (`docs: code.claude.com/docs/en/slash-commands`): "Custom
   commands have been merged into skills... Your existing `.claude/commands/`
   files keep working" but the current recommended shape for both what this
   project calls `skill` *and* `workflow` is `.claude/skills/<name>/SKILL.md`,
   loaded on demand rather than always-in-context. Fix: retarget `workflow`
   output to `.claude/skills/<name>/SKILL.md` (or, minimally, the still-working
   legacy `.claude/commands/<name>.md`), and reconsider whether `skill`
   artifacts should move there too instead of being inlined into `CLAUDE.md`
   — real Claude Code Skills are on-demand-loaded, which would also resolve
   the token-efficiency concern from the original starter-collections review
   (skills currently cost context on every session regardless of whether
   they're used).
3. **`.claude/models/*.md` is fictional.** Real model configuration is via
   `/model`, `--model`, the `ANTHROPIC_MODEL` env var, or the `model` field
   in `.claude/settings.json` (`docs: code.claude.com/docs/en/model-config`).
   Fix: either drop `model_config` support for this target (matching the
   precedent set by `amazon_q.py`/`goose.py`/`cody.py`) or merge it into a
   `.claude/settings.json` `model` field.
4. **This repo's own [`CLAUDE.md`](../../CLAUDE.md)** asserts
   `.claude/agents/*.md` + `.claude/workflows/*.md` as fact in its own
   "Claude Code" section — needs correcting alongside the adapter, not just
   the adapter's docstring.

#### `cursor.py` — ✅ FIXED (was broken, second priority)

**Done:** `backend/app/adapters/cursor.py` rewritten. Every artifact type
now writes `.cursor/rules/<name>.mdc` (named after `artifact.name`, not
numbered) with real frontmatter: `description` + `alwaysApply` (`true` for
`rule`-type, `false` for everything else — putting skill/agent/workflow
content into Cursor's "Agent Requested" mode, where the agent decides
whether to pull it in based on the description, which is a good semantic
fit for on-demand capabilities). `.cursorrules` is no longer written. No
`globs` field is emitted (optional in Cursor's schema; there's no natural
Canonical-IR concept to map to it, so omitting is more honest than the
old adapters' `target_compatibility`-as-fake-file-glob pattern used
elsewhere). `.cursor/workflows/`/`.cursor/models/` no longer written.
`TestCursorAdapter` updated to match and logic-traced the same way as
`claude_code.py` above — **run the real test suite once available.**

Original findings, for reference:

1. **Frontmatter fields are wrong.** Real MDC frontmatter
   (`docs: cursor.com/docs/rules`) is `description`, `globs`, `alwaysApply`
   — these three fields together determine whether/when a rule is even
   loaded. The adapter emits `title`, `type`, `priority` instead, none of
   which are recognized; a rule missing real `description`/`globs`/
   `alwaysApply` risks not being included in context at all.
2. **`.cursorrules` appears to be fully dropped from current docs** (not
   just marked deprecated — absent entirely). The adapter still writes it
   for `rule`-type artifacts as if it were current.
3. **`.cursor/workflows/*.mdc` and `.cursor/models/*.mdc` are fictional** —
   docs mention only Project Rules (`.cursor/rules/*.mdc`) and `AGENTS.md`
   as repo-level mechanisms; no workflow or model-config file concept exists.
4. **Numbered filenames** (`rule_000.mdc`, `rule_001.mdc`, …) for skill/agent
   output aren't wrong per se, but should be `artifact.name`-derived —
   numbering makes every recompile potentially reshuffle unrelated files
   with no way to tell what a given `.mdc` is without opening it.

Fix: rebuild `translate()` around real `description`/`globs`/`alwaysApply`
frontmatter, drop the `.cursorrules` path, name files after `artifact.name`,
and either drop `workflow`/`model_config` support for this target or fold
them into `.cursor/rules/*.mdc` like everything else.

#### `windsurf.py` — stale, tool rebranded (⏸ still open — blocked on a naming decision)

**Not started.** Unlike the other five, this one wasn't touched this
session — it needs a product-naming call (see Open Questions) before the
directory-target part can be fixed, and the two small parts that don't need
a decision (`glob` trigger value, the 12k/6k character limits) don't have a
real per-artifact data source to populate the trigger value from and
`translate()` has no warning/side-channel mechanism to report an oversized
file through (a pure `dict[str, str]` return, same constraint noted for
`windsurf.py`/`cline.py`'s silent `model_config` drop below) — fixing that
properly would mean changing the `BaseAdapter.translate()` contract for
every adapter, which is bigger than a single-adapter fix and wasn't
attempted here.

Windsurf was acquired by Cognition AI and rebranded to **Devin Desktop** as
of June 2026 (`docs.windsurf.com` now redirects to `docs.devin.ai`).
`.windsurf/` still works as a **legacy fallback** behind the now-preferred
`.devin/` directory. Additional, smaller issues: the adapter's `trigger`
values (`always_on`/`model_decision`/`manual`) are missing a real fourth
value, `glob`; the emitted `type` field isn't real/recognized; and real
character limits (12,000/workspace rule file, 6,000/global rules file) are
enforced by the tool but not checked by the adapter, so an oversized
compiled rule would silently fail or get truncated by Windsurf/Devin rather
than by MyACE with a clear signal.

Fix: decide whether to rename this adapter's primary target to
`devin-desktop`/`.devin/rules/` (keeping `windsurf`/`.windsurf/rules/` as a
legacy-compatible secondary target) or leave it as-is on the reasoning that
the fallback still works — either way, add the missing `glob` trigger value
and a length check with a warning rather than silent truncation.

#### `cline.py` — ✅ FIXED (frontmatter parsing was real, fields were not)

**Done:** `backend/app/adapters/cline.py` rewritten to emit **no
frontmatter at all**, rather than trying to salvage the wrong fields —
Canonical IR has no real per-artifact glob/path-scoping concept to map onto
Cline's one real field (`paths`), and Cline's documented default (no
frontmatter = always active) is exactly the behavior this project's rules
need. Output is now a plain `# Name (Kind)` heading + description + body,
same pattern as the already-correct `goose.py`. File paths/prefixes
(`skill-`, `agent-`, `workflow-`) unchanged — those were always just this
adapter's own organizational choice, not a Cline-recognized concept.
`TestClineAdapter` updated (dropped the `"type: skill"` assertion, added a
no-frontmatter assertion) and logic-traced.

Original finding, for reference: Cline does parse YAML frontmatter
(`docs.cline.bot/customization/cline-rules`; fails open to raw content if
parsing breaks), so the adapter's basic premise held. But the *only*
documented recognized field is `paths` — the adapter emitted `title`,
`description`, `type`, `priority`, `tags`, `globs`, none of which matched.

#### `codex_cli.py` — ✅ FIXED (was broken on 2 of 3 artifact types plus config schema)

**Done:** `backend/app/adapters/codex_cli.py` rewritten. Agents now write
real TOML to `.codex/agents/<name>.toml` (`name`, `description`,
`developer_instructions` — the body wrapped in a `"""`-delimited multi-line
string, name/description through a small TOML-string escaper since no
`toml` library is imported anywhere in this codebase, matching this
adapter's existing self-contained-string-building style). `workflow`
artifacts are now skipped entirely with a code comment explaining why (no
real target exists). `.codex/config.toml` now renders the real schema — a
top-level `model = "..."` selector (first `model_config` artifact wins,
since real config.toml has no equivalent of a model *list*) plus one
`[model_providers.<id>]` table per distinct provider, built the same
`entry.update(extra_fields)` way `continue_dev.py` already merges extra
model-config body fields. Skills/rules unchanged (already confirmed
correct). `TestCodexCliAdapter` updated (new TOML-shape assertions, a
workflow-is-skipped test, a `[model_providers.openai]`-shape test replacing
the old `[models]` one) and logic-traced, including the TOML string
escaper.

Original findings, for reference:

1. `AGENTS.md` at root: **confirmed correct.**
2. `.agents/skills/{name}/SKILL.md`: **confirmed correct**
   (`docs: learn.chatgpt.com/docs/build-skills`); the adapter's extra
   `priority` frontmatter field is undocumented but harmless.
3. **`.agents/agents/{name}.md` is wrong.** Real custom subagents
   (`docs: learn.chatgpt.com/docs/agent-configuration/subagents`) are
   **TOML** files under `~/.codex/agents/` (personal) or `.codex/agents/`
   (project) — required fields `name`, `description`, `developer_instructions`.
   Not Markdown, not under `.agents/agents/`.
4. **`.agents/workflows/{name}.md` is wrong** — no "workflow" concept
   exists anywhere in Codex CLI (skills + subagents + MCP are the only
   customization primitives). This path is invented.
5. **`.codex/config.toml`'s `[models]` table is wrong.** Real schema
   (`docs: learn.chatgpt.com/docs/config-file/config-reference`) is a
   top-level `model = "..."` string plus `[model_providers.<id>]` tables
   (`name`, `base_url`, `env_key`, …) — there is no `[models]` table.
   Also worth noting: project-scoped `.codex/config.toml` cannot override
   provider/auth/profile-selection config — that has to live in
   `~/.codex/config.toml`, so a compiled project-local file may silently
   not take effect for those fields even with the corrected schema — this
   is a real platform constraint, not something the adapter fix resolves.

1. `AGENTS.md` at root: **confirmed correct.**
2. `.agents/skills/{name}/SKILL.md`: **confirmed correct**
   (`docs: learn.chatgpt.com/docs/build-skills`); the adapter's extra
   `priority` frontmatter field is undocumented but harmless.
3. **`.agents/agents/{name}.md` is wrong.** Real custom subagents
   (`docs: learn.chatgpt.com/docs/agent-configuration/subagents`) are
   **TOML** files under `~/.codex/agents/` (personal) or `.codex/agents/`
   (project) — required fields `name`, `description`, `developer_instructions`.
   Not Markdown, not under `.agents/agents/`.
4. **`.agents/workflows/{name}.md` is wrong** — no "workflow" concept
   exists anywhere in Codex CLI (skills + subagents + MCP are the only
   customization primitives). This path is invented.
5. **`.codex/config.toml`'s `[models]` table is wrong.** Real schema
   (`docs: learn.chatgpt.com/docs/config-file/config-reference`) is a
   top-level `model = "..."` string plus `[model_providers.<id>]` tables
   (`name`, `base_url`, `env_key`, …) — there is no `[models]` table.
   Also worth noting: project-scoped `.codex/config.toml` cannot override
   provider/auth/profile-selection config — that has to live in
   `~/.codex/config.toml`, so a compiled project-local file may silently
   not take effect for those fields even once the schema is fixed.

Fix: rewrite `_format_agent`/`_parse_model_config`/`_render_toml` against
the real TOML subagent format and `model_providers` schema; drop or
repoint `workflow` output since no real target exists for it.

#### `cody.py` — ✅ RETIRED (was: fictional format, and the product itself has mostly gone away)

**Done:** `backend/app/adapters/cody.py` deleted entirely (not just
deregistered — there was no real target format to keep it pointed at).
Removed from `backend/app/adapters/__init__.py` (import + registration),
`backend/app/models/profile.py`'s `ProfileCompileRequest.target` `Literal`,
and all 81 starter-collection `compatibility` frontmatter lists (bulk sed,
same mechanism used to add `copilot-cli` earlier). `backend/tests/
test_adapters.py`'s `TestCodyAdapter` class removed along with the
registry-list assertion. `README.md` (adapter table + file-tree comment,
12→11), `docs/architecture.md` (12→11), and `docs/ADAPTERS_RESEARCH.md`
(retirement note added under the original research entry, preserving the
historical record rather than deleting it) all updated.

Original reasoning, for reference: `.sourcegraph/*.rule.md` is confirmed
fictional — no "rules" capability exists in current Cody docs; the closest
analog is the **Prompt Library**, which is server-side/Enterprise-instance-
hosted, not a git-committed file format at all. Separately: Cody Free and
Pro were discontinued July 23, 2025 — only Cody Enterprise ($59/user/mo)
still exists. This adapter's own docstring caveat ("re-verify against
Cody's docs before relying on this in production") was correct to flag
doubt, and the doubt resolved to "this doesn't work and most users of the
`cody` target can't use Cody at all anymore."

#### `continue_dev.py` — ✅ FIXED (was: one stale path, otherwise solid)

**Done:** `backend/app/adapters/continue_dev.py`'s `workflow` output moved
from `.continue/prompts/<name>.prompt` to `.continue/prompts/<name>.md`,
with `invokable: true` added to its frontmatter. **Partial/honest fix**:
the module docstring explicitly flags that the other half of the real
mechanism — registering the prompt file via a `prompts:` list in
`config.yaml` — was *not* added, because the research summary wasn't fully
confident on the exact reference schema (`uses:`-style Continue Hub block
reference vs. a plain local file path). Rather than guess and ship a
second wrong schema, this was left as a documented follow-up. `TestContinueAdapter`
updated to check the new `.md` path and `invokable: true`, and logic-traced
via the syntax/compile check (didn't need a standalone re-implementation —
the change was small enough to review directly against the diff).

Original finding, for reference: rules (`.continue/rules/*.md`, frontmatter
`name`/`globs`/`description`/`alwaysApply`) and the `config.yaml`
`mcpServers` key were confirmed current. `.continue/prompts/*.prompt` was
stale — current Continue docs show no standalone `.prompt` file mechanism.

#### `goose.py` — ✅ FIXED (was: one real, fixable gap)

**Done:** `backend/app/adapters/goose.py` now emits `AGENTS.md` instead of
`.goosehints`. Considered emitting both (the plan's original "or both, for
maximum compatibility" suggestion) but decided against it: it's unconfirmed
whether Goose *merges* content from both files when present or picks one —
if it merges, duplicating identical content into both would double-load
every rule/skill, wasting context rather than protecting compatibility. The
single-file `AGENTS.md`-only choice is documented in the module docstring
with this reasoning. `model_config` skip and the no-frontmatter format are
unchanged (already correct). `TestGooseAdapter` updated (file path
assertions, renamed test method) and logic-traced.

Original finding, for reference: the `.goosehints` format itself and the
`goose-docs.ai` docstring citation were both still accurate (the docs did
migrate to that exact domain, so the citation was right, if only by
coincidence of timing) — but Goose's actual context-file search order is
`["AGENTS.md", ".goosehints"]`, checked in that order, making `AGENTS.md`
effectively primary. Separately, Goose has since added a **Recipes** system
(YAML files bundling instructions/prompt/extensions/sub-agents) that could
map naturally to this project's `agent`/`workflow` artifact types instead of
folding everything into one hints file — worth a follow-up enhancement, not
a correctness fix.

#### `amazon_q.py` — correct, missing the newer native format

`.amazonq/rules/*.md` plain Markdown is still confirmed correct. New since
the original citation: Amazon Q CLI now has native custom agents as **JSON**
files at `.amazonq/cli-agents/{name}.json` (with `tools`/permission/
`resources` fields) and MCP config at `.amazonq/mcp.json`; rules are now
loaded as "agent resources" referenced from that JSON rather than being
the only mechanism. The adapter's current `agent` → `.amazonq/rules/agent-
{name}.md` fallback still works as a plain rules file, so this is an
enhancement opportunity, not a bug — worth a follow-up to emit the more
idiomatic native format.

#### Confirmed correct as-is: `copilot_cli.py`, `aider.py`, `opencode.py`

- `copilot_cli.py`: the suspected product-scope mismatch (IDE vs. CLI) does
  **not** hold — `docs.github.com/.../copilot-cli/customize-copilot/
  add-custom-instructions` explicitly documents the CLI reading the same
  `.github/copilot-instructions.md` and `.github/instructions/*.instructions.md`
  files as the IDE extension, by design. Only nit: `applyTo`/`excludeAgent`
  are the real frontmatter fields; the adapter's extra `title`/`type`/
  `priority` are non-standard but harmless (unrecognized keys ignored).
- `aider.py`: `CONVENTIONS.md`, `.aider.conf.yml`'s `read:` and `model:`
  keys all reconfirmed against current docs.
- `opencode.py`: every frontmatter field (skills: `name`/`description`/
  `license`/`compatibility`/`metadata`; agents: `description`/`mode`/
  `model`; commands: `description`) and the `opencode.json` `provider.
  <name>.models`/`mcp` shape reconfirmed against current opencode.ai/docs.

#### Also worth fixing regardless of the above

- `windsurf.py` and `cline.py` silently drop `model_config` artifacts with
  no code branch and no explanatory comment, unlike `amazon_q.py`/
  `goose.py`/`cody.py`, which document *why* the drop is intentional. Even
  if dropping remains the right call for both, it should say so.

### 4. Trim description/Purpose redundancy in skills

Across most `SKILL.md` files, the frontmatter `description` and the body's
`## Purpose` paragraph restate the same point, and both land in every
adapter's compiled output verbatim (e.g. `claude_code.py`'s `_format_skill`
concatenates `description` then `body` directly). A pass to make
`description` a genuinely different, shorter one-liner (what a
picker/catalog UI shows) and `## Purpose` add context the description
didn't already cover would shrink every compiled profile's context
footprint without losing information.

### 5. Decide the fate of `target_compatibility`

Confirmed during the fix pass: `compile_profile()` never filters by this
field, and no adapter's `translate()` emits it into compiled output — it's
metadata that's now accurate (all 81 instances include every registered
adapter target as of the fix pass) but still functionally inert. Either:

- **Wire it up**: warn (in the compile API response, or the frontend) when
  a profile's target isn't in a given artifact's `target_compatibility`
  list, giving the field an actual purpose, or
- **Drop it**: remove from the Canonical IR schema and all starter content,
  removing ~80 lines of now-pointless-but-accurate boilerplate and the
  obligation to keep it in sync with the adapter registry going forward.

Recommend deciding this before the next adapter is added (rule 21 notes new
adapters default to "enabled" with no extra step needed — same should be
decided for whether they need adding to every artifact's compatibility
list, or whether that list should stop existing).

## Open questions

- Should the starter-pack seed-time YAML strictness (item 1) also apply
  retroactively as a startup check — i.e. should `seed_starter_collections()`
  refuse to start the backend if a starter file fails to parse, or just log
  loudly and skip that one artifact? The existing precedent
  (`seed_starter_collections()`'s current try/except around the whole
  seeding call, per rule 25) is "never block app startup" — item 1 needs to
  decide whether a single bad *file* should be held to the same standard as
  a failure of the whole seeding *process*, or whether file-level failures
  are a different category worth being stricter about.
- Item 3's audit is done and found 9 of 12 adapters need code changes —
  this plan doesn't yet size or sequence that work. Suggest treating
  `claude_code.py` (this project's own primary tool, confirmed broken on
  agents) and `cursor.py` (confirmed broken on frontmatter, likely
  under-loading rules) as the first two to actually fix, since both are
  high-usage targets with concrete, well-sourced, low-ambiguity corrections
  — the rest can follow once those two are done and the pattern (add a
  focused adapter test per target, fix, verify) is established.
- ~~Whether to retire `cody.py` outright~~ — **resolved: retired.** Deleted
  and fully deregistered (see item 3's `cody.py` section above) rather than
  fixed, since the audit found both that its target format is fictional
  *and* that the product itself (Cody Free/Pro) was discontinued — a
  different and stronger reason to drop a target than usual "docs moved"
  staleness.
- Whether `target_compatibility` should be resolved (item 5) before or
  after the adapter fixes — now that the audit shows several adapters
  don't support every artifact type at all regardless of documentation
  (e.g. Cursor/Codex CLI have no real "workflow" concept, several drop
  `model_config` entirely), that's a truer signal for what
  `target_compatibility` should reflect than the current "every artifact
  claims every target" state — consider deriving it from what each
  adapter's `translate()` actually handles, rather than hand-maintaining
  it per artifact.
