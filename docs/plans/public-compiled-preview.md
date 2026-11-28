# Plan: Compiled-Output Preview on the Public Pack Page

Status: **Planned — not started.** This finishes the unbuilt "Phase 1.5" of
[agent-install-url.md](agent-install-url.md) and answers a gap seen on the live
pack page (2026-11-28): an anonymous visitor cannot see what a pack compiles
to. The landing demo takes only pasted `##` rules, and real output is reachable
only through the MCP or by signing up.

## Problem

"Install into 12 frameworks" is the product's promise, but the public pack page
shows item names and nothing of the result. The backend already serves it:
`GET /api/v1/collections/community/{id}/install.md?target=…&format=md|json|zip`
(anonymous, rate-limited by `storefront_limiter`, size-capped). The UI never
calls it.

## Goals

1. A **Preview install** tab on `/packs/:id`, for everyone, that shows the files
   a pack compiles to for a chosen framework, plus any compile warnings.
2. The pieces an agent user needs: the MCP command, the pack's install URL, a
   zip download. (This is the old `AgentInstallPanel`.)

Non-goals: writing files anywhere (the MCP and this page are read-only by
design, ADR-0018); previewing a *setup* (needs auth, different surface);
previewing private packs (the authenticated twin in the agent-install-url doc).

## Design

No backend change expected. Reuse:
- `GET /api/v1/frameworks` (public) for the target list.
- `install.md?format=json` for `{files, warnings, compiled_hash}`;
  `format=zip` for the download link.

Frontend:
- New `PackPreviewPanel` in `components/`, lazy-loaded when the tab is opened
  (a compile is not free). Target select defaults to the first framework the
  pack declares; file tree on the left, content on the right, copy button,
  warnings list reusing the amber pattern from `TargetExporter`.
- Query key `['pack-preview', id, target]` (rule 12); `staleTime` of minutes
  and no refetch on focus, since output is a pure function of pack + target.
- Render file contents as plain text in a `<pre>`; never as HTML or markdown.
  Pack text is untrusted (rule 43).
- Show the response's `compiled_hash` and the size; surface the 413 from the
  size cap as "too large to preview, download the zip".
- Agent block: `claude mcp add --transport http myace <origin>/mcp`, the
  install URL for this pack and target, and one line that the agent proposes
  and the human applies. Origin from `window.location.origin` like
  `UserSettings.tsx`; never hard-code a host.
- Owned/moderator view of unpublished packs stays on the existing authenticated
  flows; the tab is hidden for packs the public route would 404.

## Tests

- Vitest: tab lazy-loads; target change refetches; 429 and 413 render messages;
  file content is escaped (a body containing `<script>` shows as text).
- a11y: tree and viewer are keyboard operable and labelled (see the
  `accessibility` pack's checklist).

## Risks

- Compile cost per hit on a public route. Mitigated by the existing limiter and
  caching; watch the logs after release before adding a server-side cache
  (ADR-0009 already names that as the future fix).
- A big pack on a small target is fine; Cursor emits ~13 files for 11 items, so
  the viewer must handle many files.

## Open questions

- Also upgrade the landing demo to accept a starter pack as input? Separate
  decision.
