# ADR-0010: A `handoff_to` field on agent artifacts, not a new join table

**Status:** Accepted

## Context

The multi-agent pipeline pattern already exists in this repo's own starter
content — `collections/base/software-engineer/agents/orchestrator.md`
routes work through `builder` → `verifier` → `security-auditor`
(conditionally) → `code-reviewer` → `docs-writer`, and every one of those
subagents documents its own next step in a prose "## Handoff" section.
That routing is real and already followed by hand-written agents, but it
exists only as free text — nothing in the Canonical IR, the compiler, or
the frontend can answer "which agents does this one hand off to" without a
human reading the prose. That blocks two things this phase wants to build:
an Orchestration Gallery that visualizes an existing pipeline as a diagram,
and a wizard that composes a new pipeline and needs to *generate* frontmatter
that means the same thing the hand-written prose does.

The field only makes sense on `agent` artifacts — rules, skills, workflows,
and model configs don't hand off to anything — and only some agents (an
orchestrator's `mode: primary` agents, mainly) will ever populate it. Most
existing agent rows, and probably most future ones, will never set it.

## Decision

Add `handoff_to: list[str] | None` to the Canonical IR as a new optional
field on agent artifacts, stored the same way `tags`/`target_compatibility`
already are: a nullable `Text` column on `artifacts`
(`backend/alembic/versions/d1e2f3a4b5c6_add_handoff_to_artifacts.py`),
JSON-encoded, decoded through the existing `_artifact_to_read()`/
`_db_to_canonical()` conversion choke points (AGENTS.md rule 11) rather
than a new mechanism. Unlike `tags`/`target_compatibility` (which default
to `"[]"`), the column defaults to `NULL` — `None` on the wire means "not
declared" and is kept distinct from `[]` ("declared, but terminal — never
hands off"), since most rows will never touch this field at all and a
default empty list would blur that.

The value is a flat list of agent *names* (strings), not artifact IDs and
not foreign keys. `_parse_agent_file` (both the backend and CLI scanners,
kept in sync per AGENTS.md rule 8) reads it from an optional `handoff_to:`
frontmatter key, mirroring how `mode`/`model` are already read. The prose
"## Handoff" section stays in every hand-written agent body as the
human-readable version of the same fact — the frontmatter is the
machine-readable version, and the two are expected to stay consistent by
convention, not by any enforced coupling.

`compile_profile()` gets one new whole-profile validation pass, added
*after* the existing per-collection dedup loop rather than inside it (a
`handoff_to` target may live in any collection composed into the profile,
so it can only be checked once the final deduplicated artifact set is
known): every referenced name is checked against that set, and an
unresolved reference produces a `dangling_handoff` `ValidationIssue` —
reusing the exact `warnings` plumbing Phase 1 built for `name_collision`
(AGENTS.md rule 32) rather than inventing a second mechanism.

## Alternatives considered

- **A new `agent_handoffs` join table** (`from_artifact_id`,
  `to_artifact_id`, both FKs into `artifacts`) — rejected. This is the
  "correct" relational shape and would get real referential integrity for
  free, but it breaks the moment a `handoff_to` target lives in a
  different collection that hasn't been created yet, or is composed into a
  profile later — the whole point of the field is to describe routing
  *before* a specific profile's composition is known, the same way
  `Profile.additional_collection_ids` is already a JSON list of IDs rather
  than a join table (see [data-model.md](../data-model.md)) for exactly
  this reason. A join table would also need a migration path for every
  future scanner/import source that produces agent artifacts, where a
  plain string list round-trips through frontmatter, `ArtifactCreate`, and
  GitHub export with no special handling.
- **Reference by artifact ID instead of name** — rejected. IDs aren't
  known at authoring time (a hand-written `orchestrator.md` in
  `collections/` has no artifact row yet — one is only created when a
  collection is seeded/scanned/imported), and names are already the
  effective identity of an artifact throughout this codebase: dedup in
  `compile_profile()` is by name (rule 29), not ID. Using name keeps
  `handoff_to` consistent with how the rest of the system already treats
  artifact identity.
- **Enforce referential integrity at write time** (reject a `handoff_to`
  entry that doesn't resolve, at scan/import/create time) — rejected. At
  the point an agent is scanned or created, the target of its `handoff_to`
  may legitimately not exist yet in that same request (it could be in a
  collection not yet imported, or a sibling agent file processed in a
  different order), and profile composition — the only point at which the
  *full* available agent set is actually known — happens later and
  separately. Validating at compile time (via `dangling_handoff`, same
  timing and shape as `name_collision`) is the only point where "does this
  resolve" is actually answerable, so that's where the check lives.

## Consequences

- `handoff_to` is advisory metadata, not enforced routing. Nothing stops
  an agent's `handoff_to` from drifting out of sync with its own prose
  "## Handoff" section — Epic 3.2's starter-pack update keeps them
  consistent by hand, and there's no automated check that they stay that
  way. A future enhancement could lint for this (e.g. flag when an agent's
  `handoff_to` list and the agent names mentioned in its own body diverge)
  but that's not implemented here.
- No adapter's `translate()` reads `handoff_to` — it doesn't change a
  single compiled file's content for any existing target framework. It's
  consumed entirely by new frontend surfaces (the Orchestration Gallery's
  diagram, the pipeline wizard's generated frontmatter) added in this same
  phase.
- A `handoff_to` reference is only ever checked against a specific
  profile's fully-composed artifact set, never in isolation. The same
  agent, with the same `handoff_to` list, can be "clean" in one profile
  and produce a `dangling_handoff` warning in another, depending on which
  collections that profile happens to include — this is inherent to
  referencing by name across collection boundaries (see the rejected
  join-table alternative above) rather than a bug in the check itself.
- Like `name_collision`, `dangling_handoff` never blocks compilation —
  it's a `level: "warning"` `ValidationIssue`, surfaced the same way
  (CLI `pull` output, the zip's `_myace_warnings.txt`,
  `TargetExporter.tsx`'s warnings panel) with no code changes needed at
  any of those call sites, since they already render whatever's in the
  `warnings` list generically rather than special-casing `name_collision`.
