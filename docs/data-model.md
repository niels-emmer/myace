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
    USER ||--o{ COLLECTION_RATING : rates
    USER ||--o{ COLLECTION_COMMENT : writes
    COLLECTION ||--o{ ARTIFACT : contains
    COLLECTION ||--o{ COLLECTION_RATING : "rated by"
    COLLECTION ||--o{ COLLECTION_COMMENT : "commented on"
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
        string role "user | moderator | admin"
        bool notify_on_download "daily digest opt-in"
        bool notify_on_comment "immediate email opt-in"
        bool mfa_enabled
        string totp_secret "nullable — set once MFA is enrolled"
    }
    COLLECTION {
        uuid id PK
        uuid owner_id FK
        string name
        string git_url "real URL, or imported://name / seed://type/slug for non-git sources"
        string collection_type "base | additional"
        string visibility "private | public"
        bool is_active "soft-delete flag"
        int artifact_count "denormalized cache"
        int download_count "tracked for community collections"
        bool published "true only once moderation_status = approved"
        string category "nullable — browse category"
        bool is_starter_pack "true for the seeded starter collections"
        float avg_rating "denormalized cache of collection_ratings"
        int rating_count "denormalized cache of collection_ratings"
        string moderation_status "draft | submitted | approved | denied"
        string moderation_reason "nullable — set on deny"
        datetime submitted_at "nullable"
        datetime moderated_at "nullable"
        uuid moderated_by FK "nullable — the reviewing moderator/admin"
        int last_digest_download_count "digest-script watermark"
        datetime last_digest_sent_at "nullable"
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
        string target_framework "nullable — preferred compile target, informational only"
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
    COLLECTION_RATING {
        uuid id PK
        uuid collection_id FK
        uuid user_id FK
        int stars "1-5, CHECK constraint"
        datetime created_at
        datetime updated_at
    }
    COLLECTION_COMMENT {
        uuid id PK
        uuid collection_id FK
        uuid user_id FK
        text body "max 2000 chars"
        datetime created_at
        datetime deleted_at "nullable — soft-delete timestamp"
    }
```

`DOC_CACHE` (framework documentation cache for adapter compatibility rules)
has no relationships to the rest of the schema — it's a standalone TTL cache,
keyed by `framework` + `content_hash`.

`SYSTEM_SETTINGS` also has no relationships — it's a singleton row
(`id` always `1`) holding global, admin-editable config: which auth
providers are enabled, whether registration/MFA are allowed or forced, and
the doc cache TTL. See the `system_settings` section below.

## Tables

### `users`

The only table every other owned table has a foreign key into. A user can
authenticate via password (`password_hash`, nullable — SSO-only accounts
never set one), OIDC/GitHub/Google (`oidc_sub` + `oidc_provider`, unique
together), or both. `is_admin` bypasses ownership checks everywhere; see
[invariants.md](invariants.md#authorization). `mfa_enabled` + `totp_secret`
back TOTP-based MFA (`pyotp`) — `totp_secret` is only set once enrollment
completes via `POST /auth/me/mfa/totp/setup` + `.../verify`. `reset_token_hash`
+ `reset_token_expires_at` back password-reset-by-email (`POST
/auth/forgot-password` / `/auth/reset-password`) — only the SHA-256 hash of
the emailed token is stored, mirroring the API-token-hash pattern; the token
is single-use (both fields are cleared on a successful reset) and expires
after 1 hour.

`role` (`user`/`moderator`/`admin`, default `user`) is additive alongside
`is_admin` — see [ADR-0007](adr/0007-additive-user-role-column.md) for why
there are two fields instead of one. `is_admin` still gates every
pre-existing admin check; `role` is read only by the newer
`require_moderator_or_admin` dependency that gates the community
moderation routes. The two are kept in sync by
`PATCH /auth/users/{id}/role` (admin-only), never independently.
`notify_on_download`/`notify_on_comment` (both default `false`) are
per-user, self-service opt-ins for community-collection notification
emails — see the "Community collections" section below.

### `collections`

A named bag of artifacts. `git_url` is a real repository URL for
GitHub-imported collections, or a synthetic URI for anything that didn't
come from a real git remote — `imported://<name>` for a local scan or
bulk-exported artifacts, `imported://community/<name>` for a community
import, `seed://<collection_type>/<slug>` for the built-in starter packs
(`seed_collections.py`) — don't assume it's always dereferenceable.
`visibility` (`private`/`public`) is the only access-control dimension
beyond ownership; there is no per-collaborator sharing. `is_active` is a
soft-delete flag — deleted collections are never physically removed.
`artifact_count` is a denormalized cache updated by every route that
adds/removes artifacts (import, bulk delete, bulk export) — if you add a new
artifact-mutating route, update it there too or the count will drift.
`is_starter_pack` marks the collections seeded on every backend startup from
`collections/base/` and `collections/additional/`, owned by a dedicated
passwordless system account — see the "Starter packs" section in
`CLAUDE.md`. `avg_rating`/`rating_count` are a denormalized cache of
`collection_ratings`, recomputed transactionally on every rating
write/delete — see the `collection_ratings` section below.
`moderation_status` (`draft`/`submitted`/`approved`/`denied`) is the
single source of truth for the community-publishing lifecycle — see
[ADR-0008](adr/0008-collection-moderation-state-machine.md) and the
"Community collections" section below; `published`/`visibility` are only
ever flipped to public by the approve action, never by submission itself.
`last_digest_download_count`/`last_digest_sent_at` are watermark fields
for the daily download-digest script
(`app/scripts/send_download_digests.py`), not exposed via the API.

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

### `collection_ratings`

One row per (collection, user) — enforced by a DB-level unique constraint
(`uq_collection_ratings_collection_user`), not just upsert logic in the
route handler. `stars` has a `CHECK (stars >= 1 AND stars <= 5)`
constraint in addition to the 422 the API returns for an out-of-range
value. `PUT /collections/{id}/rating` upserts the caller's own row and
recomputes `Collection.avg_rating`/`rating_count` transactionally; `DELETE`
removes it and recomputes again. Rating requires
`Collection.moderation_status == "approved"` and blocks self-rating
(`owner_id == current_user.id` → 400).

### `collection_comments`

Soft-deleted (`deleted_at`), never hard-deleted, per the soft-delete rule
below. `body` is capped at 2000 characters, enforced at the Pydantic
schema layer (`CollectionCommentCreate`), not just informally. Commenting
requires `Collection.moderation_status == "approved"`, same gate as
ratings. Deletion is allowed for the comment's own author, the
collection's owner, or a moderator/admin — checked in the route handler,
not by a DB constraint. `GET /collections/{id}/comments` still requires
authentication like every other route in this API (see
[invariants.md](invariants.md#authorization)) — the plan that introduced
comments described this endpoint as public, but that would have been the
first unauthenticated data route in the app, so it was kept consistent
with the existing all-routes-require-auth convention instead.

### `profiles`

`base_collection_id` is a real foreign key; `additional_collection_ids` and
`disabled_artifact_ids` are **not** — they're JSON-encoded UUID lists,
resolved and validated at request time rather than enforced by the database.
This means the database will happily store a profile referencing a
collection that's since been deleted or made private; the compiler
(`compile_profile()`) silently skips any collection ID it can't resolve
rather than erroring. `version` increments on every `PUT` — there's no
history table, just the counter. `target_framework` is an optional,
free-string "preferred target" hint shown in the UI — it's never validated
against the adapter registry and has no effect on compilation; the actual
target is chosen per-compile-request. `is_public` is the profile's own
visibility flag, independent of the visibility of the collections it
references (see the documented gap in
[invariants.md](invariants.md#a-gap-thats-accepted-not-fixed)). `deleted_at`
supports soft-delete — profiles are never physically removed from the
database.

### Compile-time validation warnings (response-only — no table)

`POST /profiles/compile`'s response carries a `warnings` field
(`list[ValidationIssue]`, each `{level: "warning", code: str, message:
str}` — `app/models/profile.py`), additive to the pre-existing
`{profile_id, profile_name, target, artifact_count, files}` shape.
`compile_profile()` (`app/services/compiler.py`) computes these fresh on
every call, in the same step that deduplicates artifacts by name — nothing
here is persisted to the database, there's no `validation_issues` table,
and no migration was needed to add it. `POST /profiles/compile/zip` can't
embed this JSON alongside the zip's binary response, so it instead appends
a `_myace_warnings.txt` file inside the archive when there are any
warnings to report. See [AGENTS.md rule 32](../AGENTS.md) for the
name-collision rule this currently powers. The `{level, code, message}`
shape is deliberately generic rather than name-collision-specific, so a
future compile-time check (e.g. a dangling agent-handoff reference) can
append its own `code` to the same `warnings` list without a schema change
or a second parallel warnings mechanism.

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

### `system_settings`

A singleton row (`id` is always `1`, enforced by convention rather than a
DB constraint) holding global, admin-only config: which auth providers
(`oidc_enabled`/`github_enabled`/`google_enabled`) and registration
(`allow_registration`) are turned on, whether MFA is available
(`mfa_enabled`) or mandatory (`mfa_forced`), and `doc_cache_ttl_days`. Read
via `GET /admin/settings`, written via `PATCH /admin/settings`
(`SystemSettings.tsx`) — both admin-gated. Not owner-scoped; there is
exactly one row.

Also holds the SMTP config used for password-reset emails: `smtp_enabled`,
`smtp_host`, `smtp_port`, `smtp_username`, `smtp_from_email`,
`smtp_from_name`, `smtp_use_tls`, and `smtp_password_encrypted` (the
admin-entered password, Fernet-encrypted — see
[ADR-0006](adr/0006-encrypted-admin-editable-secrets.md)). Any of these left
unset falls back to the matching `SMTP_*` env var at runtime
(`app/services/effective_settings.py`); a non-empty DB value always wins.
`SystemSettingsRead` never returns `smtp_password_encrypted` itself — only a
computed `smtp_password_set: bool` — and `SystemSettingsUpdate` accepts a
plaintext, write-only `smtp_password` field that the `PATCH /admin/settings`
handler encrypts before persisting.

Also holds per-provider OAuth credentials — `oidc_client_id`,
`oidc_client_secret_encrypted`, `oidc_issuer_url`, `oidc_scopes`,
`github_client_id`, `github_client_secret_encrypted`, `google_client_id`,
`google_client_secret_encrypted` — entered via System Settings' expandable
Authentication Providers rows instead of only `.env`. Same precedence and
encryption contract as SMTP above (`get_effective_oauth_config()` in
`effective_settings.py`; `{provider}_client_secret_set` computed booleans,
never the encrypted value, on `SystemSettingsRead`). `security.py`'s
`get_oauth_client()` rebuilds a provider's Authlib client whenever its
effective config changes (tracked by a fingerprint), so a credential saved
here takes effect on the next login/callback request without a restart.

Also holds `disabled_adapters` — a JSON-encoded `list[str]` of adapter
names (`BaseAdapter.adapter_name()`) an admin has disabled system-wide,
same manual-JSON-in-`Text`-column convention as
`Profile.disabled_artifact_ids`. Toggled via `PATCH
/admin/adapters/{name}?enabled=<bool>`. Enforced in two places: the
frontend's compile target picker (`TargetExporter.tsx`) filters disabled
adapters out of the dropdown, and `compile_profile()`
(`app/services/compiler.py`) — the single choke point both
`/profiles/compile` and `/profiles/compile/zip` funnel through — raises
`AdapterDisabledError` (→ HTTP 400) if the requested `target` is disabled,
so the restriction can't be bypassed by calling the API directly.

## Why JSON-as-text instead of proper junction tables

`Collection.tags`/`target_compatibility` and `Profile.additional_collection_ids`/`disabled_artifact_ids`
could be normalized into join tables. They're JSON-in-text instead because:

- These lists are always read/written as a whole (never queried
  element-wise — nothing does "find all artifacts tagged X" at the SQL
  level today).
- It keeps the schema small for what is, so far, a single-user-per-resource
  data model with no need for relational queries across these lists.

## Community collections

Publishing goes through a moderation queue, not a self-serve DB write — see
[ADR-0008](adr/0008-collection-moderation-state-machine.md) for the full
state machine. `POST /collections/{id}/publish` moves a collection from
`draft`/`denied` to `submitted`; only the moderator/admin-only
`POST /moderation/{id}/approve` action flips `published = True` and
`visibility = "public"`. `GET /collections/community` lists anything with
`published = True AND is_active = True` (unchanged query, but now that
predicate is only ever true for `moderation_status = "approved"` rows) and
accepts `sort=rating|downloads|alpha` (default `downloads`).
`GET /moderation/queue` (moderator/admin only) lists `submitted` rows,
oldest-first by default, accepting the same three `sort` values as an
override. `download_count` tracks how many times the collection has been
imported; `category` is a free-text browse string.

Denying (`POST /moderation/{id}/deny`, body `{reason}`) sets
`moderation_status = "denied"` and `moderation_reason`, leaves
`published = False`, and lets the owner edit and resubmit (back to
`submitted`). A moderator/admin can also fix `name`/`description`/
`category` directly via `PATCH /moderation/{id}/meta`, regardless of
`moderation_status` — never `git_url`/`git_branch`/artifact content, and
never available to the collection's own owner (they use their existing
`PATCH /collections/{id}` instead).

This is entirely separate from the seeded starter-pack set (`is_starter_pack
= True`, owned by the system account — see the `collections` table above):
starter packs are grandfathered straight to `moderation_status = "approved"`
at seed time, never routed through the queue. The migration that introduced
`moderation_status` did the same one-time grandfathering for every
collection that was already `published = True AND is_active = True`,
matching this exact query's filter — nothing already visible in the
community disappeared or needed re-review.

Importing a community collection creates a new user-owned `Collection` with
copied `Artifact` rows and increments `download_count` on the source. If the
source owner has `notify_on_download = True`, they get a daily digest
email (not a per-download email) — see `last_digest_download_count`/
`last_digest_sent_at` in the `collections` table above and
`docs/deployment.md`'s cron entry for `app/scripts/send_download_digests.py`.
Comment creation on an approved collection emails the owner immediately
instead (comments are much lower-volume than downloads) if
`notify_on_comment` is on and they have an email on file.

If a future feature needs to query inside these lists (e.g. "find all public
collections tagged `python`"), that's the point to normalize — don't
work around it with `LIKE '%...%'` queries on the JSON text.
