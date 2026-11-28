# Plan: Pack Discovery Beyond One Flat List

Status: **Phases 1 and 2 built; Phase 3 partly** (branch `feat/pack-page-and-discovery`, 2026-11-28). Found on the live `/packs` page
(2026-11-28): 36 packs in one list, nine coarse categories, no stack facet.

## Problems seen

1. **Search placeholder over-promises.** It says "Search packs, tags,
   categories", but the client filter (`PacksLibrary.tsx`) matches only name,
   description and category. Packs have no tags (rule 18), so "tags" matches
   nothing.
2. **"Backend" is a grab-bag.** It now holds Python, TypeScript/Node, Go, Rust,
   Java/Spring, Backend and Database. There is no way to ask for "Go".
3. **Hard ceiling.** The library fetches `limit: 100` once. Past 100 community
   packs it silently shows the first 100.
4. **Filter state is local.** Not verified whether filters are in the URL;
   if not, a filtered view cannot be shared or restored with Back.

## Goals

A visitor can find "the Go pack", "everything for Kubernetes" or "security"
without reading 36 descriptions, and the list keeps working at 100+ packs.

## Design (smallest first)

### Phase 1 — no backend, no migration
- Fix the placeholder to match behaviour, or make it true by also searching the
  items' tags (needs the next phase's data).
- Move the language and platform add-ons to a new category **"Languages &
  Platforms"** (Python, TypeScript / Node, Go, Rust, Java / Spring, iOS,
  Android). `category` is free text, so this is a registry edit. It reaches an
  existing deployment only with the reconcile metadata option, so do that first.
- Put the active category/facet/sort/search in the URL (`useSearchParams`).

### Phase 2 — derived topics, still no migration
- The community list response gains `topics: string[]`, computed server-side
  as the most common item tags of the pack (top N, tags on a small allow-list
  so noise like "build" does not become a facet). Works for user-published
  packs too and needs no column. Cache per request set.
- UI: a "Topic" chip row under categories, and search matches `topics`.
- If the derived set is too noisy, fall back to curated `topics` in the registry
  stored in a nullable JSON column (a migration; rule 2) — the same column the
  pack-relationships plan adds can carry it.

### Phase 3 — scale
- Server-side `limit`/`offset`/`q`/`category`/`topic` on `GET /community`
  (the route already takes `q` for the MCP, ADR-0018). Library switches to
  pagination or "load more" and stops fetching everything up front.
- Keep `download_count` unranked (rule 42).

## Tests

- Search and facet filtering (pure functions in `lib/packs.ts`, unit tested).
- URL round-trip of filters.
- Backend: `topics` excludes unpublished packs' items; stable ordering.
- A seeded 150-pack fixture shows nothing is truncated once Phase 3 lands.

## Open questions

- Is "Languages & Platforms" the right split, or separate "Languages" and
  "Platforms" (iOS, Android)? Start with one.
- Curate topics or derive them? Try derived first.

## As built

- **Phase 1:** placeholder now says "topics" and search matches them; filters
  (search, facet, category, topic, sort) live in the URL and a pasted `facet=mine`
  degrades to "All" when signed out; the seven language and platform add-ons
  moved to the category **Languages & Platforms** in the registry.
  Existing deployments get the new category with
  `reconcile_seeded_collections --apply --update-metadata`.
- **Phase 2:** `GET /collections/community/topics` (anonymous, rate-limited,
  public packs only) maps pack id to up to three derived topics (item tags,
  minus a stoplist, each on at least two items; `services/pack_topics.py`).
  The library fetches it separately so signed-in and signed-out views share it,
  shows topic chips for topics on two or more packs, and works without them if
  the request fails. Derived topics were good enough that no `topics` column was
  added.
- **Phase 3, the part that mattered:** the anonymous library now pages through
  `GET /community` until it has every pack instead of taking the first 100.
  **Not built:** server-side `topic` and `category` filtering and pagination in
  the UI. Filtering stays client-side, which is fine for hundreds of packs; add
  the server side when a library is big enough to be slow.
