> **Status: implemented** (phase 1 and phase 2) — see ADR-0019 and AGENTS.md rule 45. Kept as the design record.

# Plan: agent-level permissions (ADR-0019)

## Vocabulary

Five portable capabilities, each `allow | ask | deny`: `read`, `edit`,
`execute` (shell), `network` (web fetch/search), `delegate` (spawn
subagents). Unlisted capability = inherit the framework default.

```yaml
# agent frontmatter
permissions:
  edit: deny
  execute: ask
```

## Data model

- `artifacts.permissions` — nullable JSON text, **agents only**; `NULL` = not
  declared, `{}` = declared, nothing restricted (same convention as
  `handoff_to`, rule 34). Alembic migration with a working `downgrade()`.
- `ArtifactCreate/Update/Read` and `CanonicalArtifact`: `permissions:
  dict[Literal[capabilities], Literal["allow","ask","deny"]] | None`, so a bad
  key/value is a 422 (rule 10). Convert through `_artifact_to_read()` /
  `_db_to_canonical()` (rule 11).
- Alternative considered: encode as `perm:<cap>=<value>` tags like `mode:` /
  `model:` — zero migration, but untyped and unvalidated; rejected for
  governance data.

## Scanners and export (rule 8)

Parse `permissions:` in `_parse_agent_file` in **both**
`backend/app/services/scanner.py` and `cli/myace_cli/scanner.py`;
`github_export.artifacts_to_files()` writes it back. Add a round-trip test.

## Adapters

| Target | Compiles to |
|---|---|
| claude-code | `tools:` allow-list in the agent frontmatter, emitted only when something is denied; `deny` removes the mapped tools (`edit`→Edit/Write, `execute`→Bash, `network`→WebFetch/WebSearch, `delegate`→Task). `ask`/`allow` leave the tool in. |
| opencode | per-agent `permission:` frontmatter (`edit`/`bash`/`webfetch` → allow/ask/deny). Nothing added to `opencode.json`. |
| everything else | unchanged output + `permissions_not_enforced` warning naming the agent. |

Verify the exact Claude Code and OpenCode frontmatter keys against current
docs before coding — the mapping above is from memory.

## Starter packs

Add `permissions:` to read-only roles: orchestrator (`edit`, `execute` deny),
code-reviewer / security-auditor / quick-reviewer / model-reviewer (`edit`
deny), verifier (`edit` deny). Builders and primary build agents declare none.
Keep the prose "Permission posture" — it stays the human-readable version
(same split as `handoff_to`, rule 34).

## Tests and docs

Adapter output per target; absent/`{}`/denied cases; scanner round-trip
(CLI and backend); a 422 on a bad value; the warning on a non-enforcing
target; a starter-pack compile for claude-code showing the reviewer has no
Edit tool. Update `docs/data-model.md`, README tables, AGENTS.md (new rule),
`docs/extending.md`, CHANGELOG. Existing deployments need the migration and a
`reconcile_seeded_collections --apply --update-content` run (rule 25).

## Out of scope

Global rules (`git push`), settings-file merging, `myace pull
--apply-permissions`, allow-widening of any kind.
