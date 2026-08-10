# Data Model

All tables use UUID primary keys (never auto-increment integers — see
[invariants.md](invariants.md)). Timestamps are timezone-aware
(`DateTime(timezone=True)`), stored in UTC.

## Entity relationships

```mermaid
erDiagram
    USER ||--o{ COLLECTION : owns
    USER ||--o{ PROFILE : owns
    USER ||--o{ API_TOKEN : owns
    COLLECTION ||--o{ ARTIFACT : contains
    PROFILE }o--|| COLLECTION : "base_collection_id"
    PROFILE }o--o{ COLLECTION : "additional_collection_ids (JSON list, not FK)"

    USER {
        uuid id PK
        string email UK
        string display_name
        string password_hash "nullable — SSO-only users have none"
        string oidc_sub UK "nullable"
        string oidc_provider "nullable"
        bool is_active
        bool is_admin
    }
    COLLECTION {
        uuid id PK
        uuid owner_id FK
        string name
        string git_url "real URL, or imported://name for non-git sources"
        string collection_type "base | additional"
        string visibility "private | public"
        bool is_active "soft-delete flag"
        int artifact_count "denormalized cache"
        int download_count "tracked for community collections"
        bool published "true when submitted to community store"
        string category "nullable — browse category"
    }
    ARTIFACT {
        uuid id PK
        uuid collection_id FK
        string artifact_type "rule|skill|agent|workflow|model_config"
        string name
        string target_compatibility "JSON-encoded list[str]"
        string tags "JSON-encoded list[str]"
        int priority
        text body "markdown"
        bool is_enabled
        datetime deleted_at "nullable — soft-delete timestamp"
    }
    PROFILE {
        uuid id PK
        uuid owner_id FK
        uuid base_collection_id FK
        string additional_collection_ids "JSON-encoded list[uuid]"
        string disabled_artifact_ids "JSON-encoded list[uuid]"
        bool is_public
        datetime deleted_at "nullable — soft-delete timestamp"
        int version "incremented on every update"
    }
    API_TOKEN {
        uuid id PK
        uuid user_id FK
        string token_prefix "first 8 chars, for lookup"
        string token_hash "bcrypt"
        datetime expires_at
        bool is_active
    }
```

`DOC_CACHE` (framework documentation cache for adapter compatibility rules)
has no relationships to the rest of the schema — it's a standalone TTL cache,
keyed by `framework` + `content_hash`.

## Tables

### `users`

The only table every other owned table has a foreign key into. A user can
authenticate via password (`password_hash`, nullable — SSO-only accounts
never set one), OIDC/GitHub/Google (`oidc_sub` + `oidc_provider`, unique
together), or both. `is_admin` bypasses ownership checks everywhere; see
[invariants.md](invariants.md#authorization).

### `collections`

A named bag of artifacts. `git_url` is a real repository URL for
GitHub-imported collections, or a synthetic `imported://<name>` URI for
collections created from a local scan or from bulk-exporting artifacts —
don't assume it's always dereferenceable. `visibility` (`private`/`public`)
is the only access-control dimension beyond ownership; there is no
per-collaborator sharing. `is_active` is a soft-delete flag — deleted
collections are never physically removed. `artifact_count` is a denormalized
cache updated by every route that adds/removes artifacts (import, bulk
delete, bulk export) — if you add a new artifact-mutating route, update it
there too or the count will drift.

### `artifacts`

Belongs to exactly one collection (`collection_id`, `ON DELETE` not
configured — see [invariants.md](invariants.md#data-integrity) for what
that means in practice). Has **no `owner_id` of its own** — authorization is
always done via the parent collection. `target_compatibility` and `tags` are
JSON-encoded into `Text` columns rather than being normalized into their own
tables; every route that returns artifacts must decode them before
responding (see
[debugging.md](debugging.md#response_model-silently-strips-fields-you-didnt-declare)).
`is_enabled` is per-artifact and independent of the collection's
`is_active` — a disabled artifact is skipped during compilation unless a
profile explicitly asks to `include_disabled`. `deleted_at` supports
soft-delete — artifacts are never physically removed from the database.

### `profiles`

`base_collection_id` is a real foreign key; `additional_collection_ids` and
`disabled_artifact_ids` are **not** — they're JSON-encoded UUID lists,
resolved and validated at request time rather than enforced by the database.
This means the database will happily store a profile referencing a
collection that's since been deleted or made private; the compiler
(`compile_profile()`) silently skips any collection ID it can't resolve
rather than erroring. `version` increments on every `PUT` — there's no
history table, just the counter. `is_public` is the profile's own
visibility flag, independent of the visibility of the collections it
references (see the documented gap in
[invariants.md](invariants.md#a-gap-thats-accepted-not-fixed)). `deleted_at`
supports soft-delete — profiles are never physically removed from the
database.

### `api_tokens`

CLI authentication. The raw key is generated once, split into an 8-char
`token_prefix` (stored in plaintext, used to narrow the lookup) and the full
key (bcrypt-hashed into `token_hash`). The raw key is returned to the caller
exactly once, at creation — the database never stores it in recoverable
form. `expires_at` is enforced in `get_current_user`; there's no background
job that revokes expired tokens, they just stop authenticating.

### `doc_cache`

Unrelated to the auth/ownership model above — a TTL-based cache of fetched
framework documentation, used by adapter compatibility checks. Not
owner-scoped; it's shared, read-only reference data. `deleted_at` supports
soft-delete — cache entries are never physically removed from the database.

## Why JSON-as-text instead of proper junction tables

`Collection.tags`/`target_compatibility` and `Profile.additional_collection_ids`/`disabled_artifact_ids`
could be normalized into join tables. They're JSON-in-text instead because:

- These lists are always read/written as a whole (never queried
  element-wise — nothing does "find all artifacts tagged X" at the SQL
  level today).
- It keeps the schema small for what is, so far, a single-user-per-resource
  data model with no need for relational queries across these lists.

## Community collections

Published collections have `published = True` and a `category` string for
browsing. `download_count` tracks how many times the collection has been
imported. When a user publishes a collection, it is exported to the MyACE
repository's `collections/` folder via the GitHub API, and a pull request
is opened for admin review. The database row is marked as published
immediately on a successful API response.

Importing a community collection creates a new user-owned `Collection` with
copied `Artifact` rows and increments `download_count` on the source.

If a future feature needs to query inside these lists (e.g. "find all public
collections tagged `python`"), that's the point to normalize — don't
work around it with `LIKE '%...%'` queries on the JSON text.
