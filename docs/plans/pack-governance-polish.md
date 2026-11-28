# Plan: pack governance polish (items 7, 8, 10, 11, 12, 13)

> **Status: implemented** on branches B and C. Decisions taken while running it
> (ambiguity rule: safest default, logged):
> - **Item 11:** Security By Design (Software Engineer) and DevSecOps By Default
>   (DevOps) are different rules, not copies, so only Testing Discipline (with a
>   DevOps variant), the memory rule and skill, and the plan-tracking skill were
>   shared. The memory/plan skills were byte-identical, so they need no variants.
> - **Item 10:** the compile-count change also applies to compile's own
>   `artifact_count` and the MCP `item_count`.
> - The new agents are not given elevated tools: `architect` and
>   `data-privacy-reviewer` can edit nothing.

Written to run unattended, start to finish; every open question was settled
with the owner on 2026-11-28 and is recorded here. Each branch ends as a local
commit; the owner presses Create PR and merges. On any ambiguity: take the
safest, most reversible option and log it in the final report.

## Branches (stack in this order; CHANGELOG will conflict trivially — keep both entries)

- **A `audit-by-claude-release-2-2`** — release 2.2.0 prep (versions, changelog)
  and the install-preview hint for permission files. *Done.*
- **B `audit-by-claude-perms-ui-counts`** — items 7 and 8.
- **C `audit-by-claude-pack-content`** — items 10, 11, 12, 13.

## B — items 7 and 8

**7. Inline editor for agent permissions (owner page only).** On an agent row in
`CollectionDetail.tsx`, five rows (read, edit, execute, network, delegate), each
Inherit / Ask first / Block, saved with the validate-on-blur pattern of rule 41
(`collectionsApi.updateArtifact` with `{permissions}`; Inherit omits the key; all
Inherit sends `{}`). Restrict-only: there is no "allow" option. Failures show
inline and keep the draft. The public pack page stays read-only.

**8. Exclude permission policies from item counts, in the backend.** A
`permissions:*` `model_config` is not counted in `Collection.artifact_count`
(invariant 20: every route that creates/deletes/imports/forks artifacts, plus
seeding and `seed_reconcile`). A shared `counts_toward_total()` predicate keeps
the rule in one place. The item stays visible and downloadable; only the number
changes. Existing deployments fix stored counts with the reconcile command.

## C — items 10, 11, 12, 13

**10. Per-rule priority and tags.** An optional metadata comment directly under a
`## Rule` heading: `<!-- myace: priority=90 tags=security,git -->`. Both scanners
(rule 8) parse it, `github_export` writes it back, and `scripts/sync_shared_core.py`
carries it through. Tiering (compile sorts highest first): safety/security 90,
change control and testing 70, process and style 50. Unknown keys are ignored;
the comment never appears in a rule body.

**11. Move duplicated Software Engineer / DevOps content into the shared source**
(self-contained output, per-pack variants where wording differs): the Memory
System rule and skill, the Plan Tracking skill, and the Testing Discipline and
Security By Design rules. `packs.json` gains an `include` list per pack and a
`skills` section (generated `skills/<slug>/SKILL.md`). The agents and workflows
stay hand-written (not selected).

**12. No-subagent fallback wording** in the orchestrators, `verify`/`plan`
workflows and handoff sections of Software Engineer and DevOps: where the tool
has no subagents, perform each stage yourself in order, and do not skip a stage
because it is "not delegated".

**13. Fill content gaps** (each written to the depth of the existing items):
a light testing rule for Vibecoder; a read-only security-and-privacy review agent
for Data Scientist wired into its handoffs; a dependency/supply-chain rule for
Software Engineer; an architect agent (owning the Architecture Review skill) and an
observability baseline rule for Software Engineer.

## Verification for every branch

Backend `pytest` + `ruff`, CLI `pytest` + `ruff`, frontend `tsc -b` +
`eslint` + `vitest` + `build`, `python scripts/sync_shared_core.py --check`.
After merge: deploy, `alembic upgrade head` (none planned), reconcile dry run then
apply, and check a live MCP download.
