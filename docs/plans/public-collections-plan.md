# Feature: Public, Private and Shared Collections

## Overview

Collections are the heart of how people share, find, learn about and use the
building blocks making up their Agentic Coding "profiles". This feature adds:

1. A `collections/` folder in the repo with `base/` and `additional/` subfolders
   as the canonical store for community-contributed collections.
2. A publish flow that validates a user's collection and submits it to the
   community store via a GitHub PR.
3. A community collections browser showing top downloaded collections and
   browse-by-category.
4. Import functionality to bring a community collection into a user's workspace.

## Architecture

### Data model changes (Collection table)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `download_count` | int | 0 | Number of times this collection has been imported |
| `published` | bool | False | Whether this collection has been published to the community |
| `category` | str \| None | None | Category for browsing (e.g. "python", "iac", "frontend") |

### New API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/collections/{id}/publish` | Publish collection to community (exports to MyACE repo, creates PR) |
| `GET` | `/api/v1/collections/community` | List all published community collections |
| `GET` | `/api/v1/collections/community/top` | Top 10 most downloaded community collections |
| `GET` | `/api/v1/collections/community/categories` | List available categories |
| `POST` | `/api/v1/collections/{id}/import` | Import a community collection into user's workspace |

### Folder structure

```
collections/
├── base/           # Base collections (standard packs)
│   └── .gitkeep
└── additional/     # Additional collections (smaller slices)
    └── .gitkeep
```

**Update (starter packs):** this folder now serves two purposes, not just one.
It's still the publish target described below, but as of the starter-packs
feature it's also the **install-time seed source** —
`backend/app/services/seed_collections.py` walks every subdirectory here on
every backend startup and creates a `Collection`/`Artifact` row set for it
(owned by a dedicated system account, published + public immediately) if one
doesn't already exist. The two flows compose: any community collection
merged into `collections/base/` or `collections/additional/` via the publish
PR flow becomes automatically seedable on the next deploy, with no separate
step. See the "Starter packs" section in the root [`CLAUDE.md`](../../CLAUDE.md)
for the on-disk content format and how to add a new starter collection.

### Publish flow

1. User clicks "Publish to Community" on collection detail page
2. Modal asks for: category, publish name, publish description
3. Backend validates the collection (has artifacts, valid type)
4. Backend uses `artifacts_to_files()` to convert artifacts to file tree
5. Backend pushes to `collections/{type}/{slug}/` in the MyACE repo
6. A PR is created for admin review
7. Collection is marked `published = True` in the DB

### Community collections listing

- Queries DB for `published == True` collections
- Orders by `download_count` DESC for top 10
- Supports filtering by category
- Returns standard `CollectionRead` schema

### Import flow

1. User clicks "Import" on a community collection detail page
2. Backend creates a new Collection owned by the user
3. All artifacts are copied to the new collection
4. `download_count` is incremented on the source collection

## Epics

### Epic 1: Folder structure + data model migration
- Create `collections/base/` and `collections/additional/` directories
- Add Alembic migration for `download_count`, `published`, `category` fields
- Update Collection model, schemas, and types

### Epic 2: Publish endpoint + GitHub integration
- Add `POST /api/v1/collections/{id}/publish` endpoint
- Add validation logic
- Integrate with existing GitHub export to push to MyACE repo
- Add frontend publish modal on CollectionDetail page

### Epic 3: Community collections listing
- Add `GET /api/v1/collections/community` and `/top` endpoints
- Add `GET /api/v1/collections/community/categories` endpoint
- Add community collections section to CollectionsManager page
- Add browse-by-category page/component

### Epic 4: Community collection detail + import
- Add community collection detail view (reuse existing or new route)
- Add `POST /api/v1/collections/{id}/import` endpoint
- Add import button and flow
- Wire up download tracking

### Epic 5: Testing, audit, documentation
- Write backend tests for new endpoints
- Write frontend tests
- Security audit
- Update docs (data-model.md, invariants.md, README.md)
- Update AGENTS.md with new rules

## Build pattern

Each epic follows: build → test → audit → document → continue

## Branch strategy

Branch: `feature/public-collections`
Commits: conventional commits per epic
PR: to `main` with CI verification
