# ADR-0001: Canonical IR as Markdown with YAML frontmatter

**Status:** Accepted

## Context

MyACE needs one storage format that every supported framework's rules/
skills/agents/workflows can be losslessly translated to and from. The
frameworks themselves disagree on format: OpenCode uses JSON skill/agent
files plus an `AGENTS.md`, Claude Code uses `CLAUDE.md` plus
`.claude/agents/*.md`, Cursor uses `.cursorrules` plus `.mdc` files. All of
them, however, ultimately carry the same two things: a small amount of
structured metadata (name, priority, tags, compatibility) and a body of
free-form instruction text.

## Decision

Store every artifact as Markdown with YAML frontmatter — structured metadata
in the frontmatter block, instruction content as the Markdown body. This is
the `CanonicalArtifact` shape used everywhere in the compilation pipeline.

## Alternatives considered

- **A structured format with no free text (pure JSON/YAML)** — rejected
  because the actual payload (the instruction content itself) is
  prose/code, not structured data; forcing it into a JSON string field loses
  readability and diffability for zero benefit.
- **Framework-native storage, translate on write instead of on read** —
  rejected because it means N storage formats instead of one, and every new
  framework would require a *migration* of existing data instead of just a
  new adapter.
- **A database-only representation with no file-based canonical form** —
  rejected because Markdown+frontmatter is itself directly usable and
  human-editable outside the app (it's what the scanner reads from a local
  directory in the first place) — the DB representation is a denormalization
  of this format, not the other way around.

## Consequences

- Every adapter's job is reduced to "canonical artifacts in, framework files
  out" — a pure function with no other state, which is what makes adapters
  easy to add and test in isolation.
- Import and export are naturally symmetric: the scanner parses this exact
  shape, and GitHub export re-emits it.
- The database has to denormalize `tags`/`target_compatibility` into
  JSON-as-text columns rather than proper relational columns, since the
  canonical shape is list-valued and the schema wasn't built to query inside
  those lists — see [data-model.md](../data-model.md#why-json-as-text-instead-of-proper-junction-tables)
  for the trade-off and when to revisit it.
- A field every framework doesn't need is still carried by every artifact
  (e.g. `priority` doesn't mean anything to a framework with no notion of
  rule ordering) — adapters just ignore what they don't use.
