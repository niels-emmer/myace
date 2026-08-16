# Debugging Guide

Known gotchas, in symptom-first order so you can search for what you're
seeing. Each one names the actual root cause and where it was fixed — read
the linked code before "fixing" it a different way.

## `500 Internal Server Error` from a route returning artifacts

**Symptom:** `GET /collections/{id}/artifacts` (or any route returning
`Artifact`/`ArtifactRead` data) 500s with a `ResponseValidationError` in the
logs, but only for collections that actually have artifacts with tags or
`target_compatibility` set — empty collections work fine.

**Cause:** `Artifact.tags`/`Artifact.target_compatibility` are stored as
JSON-encoded `Text` columns, but `ArtifactRead` declares them as
`list[str]`. Returning a raw SQLModel row lets FastAPI try to serialize a
JSON *string* through a schema that expects a *list* — it fails validation
silently until you look at server logs.

**Fix:** route the row through `_artifact_to_read()`
(`backend/app/api/collections.py`) or `_db_to_canonical()`
(`backend/app/services/compiler.py`), both of which `json.loads()` the two
fields first. Never `return artifact` (or `return result.scalars().all()`)
directly from a route with `response_model=ArtifactRead`.

## `response_model` silently strips fields you didn't declare

**Symptom:** an endpoint's Python code clearly builds a dict with an extra
field (e.g. `{**model.model_dump(), "token": raw_key}`), but the field never
shows up in the actual HTTP response — no error, it's just gone.

**Cause:** FastAPI serializes every response through its declared
`response_model`. If that model doesn't have the field, it's dropped during
serialization — even though the Python dict you returned had it. This bit
`create_token` for the entire lifetime of the project: it built
`{**db_token.model_dump(), "token": api_key}` under `response_model=ApiTokenRead`
(no `token` field), so the one-time "here's your new API key" response
never actually contained the key.

**Fix:** give the route its own response model that's a superset of the
"read" schema (`ApiTokenCreateResponse(ApiTokenRead)` with the extra
`token: str` field — `backend/app/models/token.py`) and use *that* as
`response_model`. If a response needs more than the standard read shape,
type it explicitly; don't rely on an untyped dict matching a narrower
schema at runtime.

## React Query shows stale/wrong data after client-side navigation

**Symptom:** a page shows 0 items (or the wrong items) right after
navigating from another page in the SPA, but a hard reload on the same URL
shows the correct data.

**Cause:** two components fetching the *same resource* with *different
filters* but the *same* React Query key. Whichever query resolves first
caches under that key; the other component reads the stale/mismatched cache
until its own query resolves and overwrites it — which can lose the race
during fast client-side navigation. This happened with `Dashboard.tsx`
fetching `collections?visibility=public` under the bare key `['collections']`
while `CollectionsManager.tsx` fetched the unfiltered list under the same
key.

**Fix:** fold every filter into the query key —
`['collections', { visibility: 'public' }]` vs. `['collections']` are
different cache entries and can't collide. If two components intentionally
want to share a cache entry, they should also share the exact same filter.

## Session cookie isn't sent / user gets logged out unexpectedly

**Symptom:** a request from the frontend gets a 401 even though the user is
clearly logged in elsewhere in the app; or a hand-rolled `fetch()` call
outside `src/lib/api.ts` behaves as if unauthenticated.

**Cause:** browsers don't send cookies on `fetch()` calls by default without
`credentials: 'same-origin'` (or `'include'` for cross-origin). `api.ts`'s
shared `request()` helper sets this, but any hand-rolled `fetch()` elsewhere
(there are two, in `ImportPage.tsx`, for the scan/import calls that stream
differently) must set it too, or the session cookie silently isn't
attached.

**Fix:** always go through `src/lib/api.ts`'s `request()` helper. If you
must call `fetch()` directly, add `credentials: 'same-origin'` yourself.

## OIDC login redirects but nothing happens / state mismatch error

**Symptom:** clicking an OIDC/GitHub/Google login button starts the redirect
but the callback fails, often with an Authlib error about missing or
mismatched `state`.

**Cause:** Authlib's Starlette OAuth client stores the OIDC `state`/nonce in
`request.session` during the redirect dance — this requires
`SessionMiddleware` to be registered (`backend/app/main.py`). If it's
missing (or removed by mistake — e.g. during a middleware refactor),
`request.session` doesn't exist and the handshake breaks.

**Fix:** `SessionMiddleware` must always be registered in `main.py`, keyed
by `settings.app_secret_key`. It also happens to be what backs the actual
user session after login succeeds — see
[architecture.md](architecture.md#authentication--authorization).

## GitHub/Google/OIDC login fails with "redirect URI is not associated with this application" behind a reverse proxy

**Symptom:** the OAuth provider's callback URL is registered correctly
(exactly matching `https://your-domain/api/v1/auth/callback/<provider>`),
but the provider still rejects the login with a redirect-URI-mismatch
error. Hitting `GET /auth/login/<provider>` directly and inspecting the
`Location` header shows the `redirect_uri` query param is `http://...`
instead of `https://...`.

**Cause:** the backend builds its OAuth `redirect_uri` from
`request.url_for(...)` (`backend/app/api/auth.py`), which trusts the
`X-Forwarded-Proto` header (uvicorn's `--proxy-headers` in
`backend/Dockerfile`). In a `docker-compose.prod.yml` deployment behind an
external reverse proxy (e.g. nginx-proxy-manager), the request actually
passes through **two** proxy hops: the external reverse proxy → the
`frontend` nginx container's `/api/` location → the `backend` container.
If the frontend's `nginx.conf` sets `proxy_set_header X-Forwarded-Proto
$scheme;`, it silently overwrites whatever the external proxy correctly
sent with its *own* `$scheme` — which is always `http`, since that nginx
container never terminates TLS itself. The backend then always thinks the
original request was plain HTTP, no matter what the external proxy saw.

**Fix:** `frontend/nginx.conf` must forward the already-set header from
upstream rather than overwrite it, falling back to `$scheme` only when
nothing set it (e.g. the frontend container is the direct edge listener,
as in the base `docker-compose.yml` single-machine setup with no reverse
proxy in front):
```nginx
map $http_x_forwarded_proto $proxy_x_forwarded_proto {
    default $http_x_forwarded_proto;
    ''      $scheme;
}
# ... in the /api/ location:
proxy_set_header X-Forwarded-Proto $proxy_x_forwarded_proto;
```
This affects every OAuth provider (OIDC/GitHub/Google) equally, since they
all build their `redirect_uri` the same way.

## A SQLAlchemy `.where(Column == True)` clause looks wrong to a linter

**Symptom:** ruff flags `E712` ("avoid equality comparisons to `True`; use
`Column:` for truth checks") on code like
`.where(Collection.is_active == True)`, or mypy complains that a class-level
column attribute doesn't have a method like `.in_()` that it clearly has at
runtime.

**Cause:** both tools are reasoning about `Collection.is_active` as if it
were a plain Python `bool`/`UUID` (the type the *instance* attribute has),
not the SQLAlchemy `InstrumentedAttribute` it actually is when accessed on
the *class* to build a query. `Column == True` and `Column.in_(...)` are
SQLAlchemy operator overloads that build a SQL expression — the linter-
suggested "fix" (`is True`, or treating the column as unsupported) would
either silently break the query or is simply wrong.

**Fix:** don't "fix" these. `E711` and `E712` are both disabled project-wide
in `backend/pyproject.toml` for exactly this reason — `== None` and
`== True`/`== False` are the correct way to build SQL `IS NULL`/boolean
comparisons in SQLAlchemy `.where()` clauses. The mypy `.in_()`-style errors
are a known SQLModel/SQLAlchemy-vs-mypy limitation without native stub
support in this project yet — they're currently informational only (mypy
runs in CI as advisory, not blocking — see
[extending.md](extending.md#improving-type-coverage) if you want to help
close this gap for real).

## `alembic upgrade head` does nothing on a fresh clone / migrations seem to not exist

**Symptom:** a freshly cloned repo has `backend/alembic/versions/` with only
a `.gitkeep` (or is missing migration files entirely that you know exist
upstream).

**Cause:** this actually happened — `.gitignore` used to contain
`backend/alembic/versions/*.py` with a `.gitkeep` exception, which silently
excluded **every** migration file from version control from the very first
commit. The initial schema migration existed on disk in development but was
never actually committed. `git status` didn't even show it as untracked,
because gitignored files don't show up in status output by default — the
gap was invisible until a second migration was added and someone went
looking for why it "wasn't showing up."

**Fix:** already fixed — the `.gitignore` rule is gone, and both migrations
are tracked. If you ever see `alembic/versions/` suspiciously empty on a
clone that should have history, check `.gitignore` first before assuming
the migrations were never written.

## A new migration's `down_revision` guess is stale, or `alembic upgrade head` reports multiple heads

**Symptom:** you write a new migration with `down_revision` set to what
looks like the most recent file under `alembic/versions/` (by filename or
by eyeballing recent git history), but `alembic upgrade head` either fails
with "Multiple head revisions are present" or silently creates a second,
disconnected chain that never gets applied.

**Cause:** filenames and commit recency are not reliable indicators of the
actual head — a merge migration, a branch that added a migration out of
commit order, or simply miscounting recent files can all point you at a
revision that already has a child. The only way to know the true head is
to walk the `revision`/`down_revision` graph, not guess from the
filesystem.

**Fix:** before writing a new migration, get the actual head programmatically:

```bash
docker compose exec backend alembic current   # what the target DB thinks is current
docker compose exec backend alembic heads     # what the migration files themselves resolve to
```

If you don't have a running DB to check `alembic current` against (e.g.
planning a migration before any environment exists), reconstruct the chain
yourself — for every file in `alembic/versions/`, extract `revision` and
`down_revision`, then find the one revision that is never referenced as
anyone else's `down_revision`:

```bash
cd backend
for f in alembic/versions/*.py; do
  rev=$(grep -m1 "^revision" "$f" | sed "s/.*= *//")
  down=$(grep -m1 "^down_revision" "$f" | sed "s/.*= *//")
  echo "$rev <- $down :: $f"
done
```

This is exactly what caught a stale head guess during the
community-enhancements plan's preflight — the plan's research had assumed
`f6a7b8c9d0e1` was current, but two more migrations (`a7b8c9d0e1f2`,
`b8c9d0e1f2a3`) had landed since, which only the graph walk revealed.

## An upsert on a soft-deleted row 500s with a unique-constraint violation

**Symptom:** a "find-or-create" upsert route works the first time, works
after an update, but 500s (`IntegrityError` / `UniqueViolation`) the second
time a user does create → delete → create again on the same logical
resource.

**Cause:** the upsert's lookup query filters on `deleted_at == None` (to
only match "live" rows), finds nothing after a soft-delete, and falls
through to an `INSERT` — but the table's unique constraint isn't scoped to
live rows, so the soft-deleted row still occupies that key. This is exactly
what `CollectionRating`'s `(collection_id, user_id)` constraint hit before
it was fixed: `DELETE /collections/{id}/rating` correctly soft-deleted
(rule 15 — never hard-delete), but the re-rate path only looked at
non-deleted rows before deciding whether to `INSERT` or `UPDATE`.

**Fix:** the lookup for an upsert against a soft-deletable table must
ignore `deleted_at` entirely (find the row regardless of its deleted
state), then either revive it (clear `deleted_at`, overwrite the mutable
fields) or update it in place — never decide "not found" based on a
`deleted_at`-filtered query when the table's uniqueness isn't similarly
scoped. See `_get_rating_row()` in `backend/app/api/ratings.py` for the
reference implementation, and rule 31 in `AGENTS.md`.

## The scanner can't find a path that clearly exists on the host

**Symptom:** `POST /collections/scan` (local mode) 404s with "Directory not
found" for a path you can `ls` on the host machine.

**Cause:** the backend runs in a container. In dev, the host's home
directory is mounted at `/host-home` (`docker-compose.dev.yml`), and
`_resolve_path()` in `backend/app/services/scanner.py` rewrites common
prefixes (`/root`, `/home`, `/Users`) to that mount — but only for patterns
it knows about, including following broken symlinks through the mount.

**Fix:** if you're adding a new host-path convention, extend
`_resolve_path()`'s prefix table rather than special-casing it in the
route. See [extending.md](extending.md) if you're changing how the dev
mount works.

## Backend refuses to start: `RuntimeError: APP_SECRET_KEY is still the default`

**Symptom:** the backend crashes on startup with:
`RuntimeError: APP_SECRET_KEY is still the default placeholder value...`

**Cause:** this key signs session cookies (`SessionMiddleware`). The
default value is an intentionally obvious placeholder
(`change-me-to-a-random-64-char-string`); the app now **refuses to start**
in production if it's still in use (was a warning in earlier versions, now
a `RuntimeError`). Anyone who knows the default value can forge a valid
session cookie for any user.

**Fix:** set a real random `APP_SECRET_KEY` in your `.env` before exposing a
deployment beyond localhost. Generate with `openssl rand -hex 32`.

## `DEBUG` or `ADMIN_BOOTSTRAP_ENABLED` warning at startup

**Symptom:** the backend logs one or both of:
`DEBUG is true outside app_env=development...` /
`ADMIN_BOOTSTRAP_ENABLED is true...`

**Cause:** same pattern as the `APP_SECRET_KEY` warning above — both
default to values that are convenient for local dev but unsafe left on for
a deployment reachable beyond localhost. `DEBUG=true` publicly exposes
`/docs`/`/redoc` and disables the session cookie's `https_only` flag.
`ADMIN_BOOTSTRAP_ENABLED=true` means the *next* person to register becomes
an admin, not just the very first person ever.

**Fix:** set `DEBUG=false` in `.env`, and set `ADMIN_BOOTSTRAP_ENABLED=false`
once you've registered your own admin account. Both warnings only fire
when `APP_ENV != development`, so a local dev setup is unaffected.

## A Dependabot PR fails CI with an unrelated-looking peer dependency error

**Symptom:** a grouped Dependabot PR (e.g. `chore(frontend): bump the
frontend-deps group...`) fails `npm ci`/`pip install` with an `ERESOLVE` or
similar dependency-resolution error, even though nothing about the failure
looks related to the actual code changes.

**Cause:** `.github/dependabot.yml`'s groups used to match `patterns: ["*"]`
with no `update-types` filter, which bundles *every* update in an ecosystem
— including unrelated major-version bumps — into one PR. One instance of
this bundled `typescript` 5→7 with `react` 18→19, `tailwindcss` 3→4, `vite`
5→8, and a dozen others in a single PR; `typescript-eslint@8.x`'s peer
range (`>=4.8.4 <6.1.0`) doesn't allow TS7 yet, so `npm ci` failed before
any of the actually-relevant packages were even considered. Worse, even a
"fix" for that one conflict would've shipped Tailwind 4 (a config-format
breaking change) and React 19 in the same PR — neither of which current CI
would catch as a silent runtime/styling break.

**Fix:** each `groups.<name>` block in `.github/dependabot.yml` now scopes
itself to `update-types: [minor, patch]`. Routine, low-risk bumps still get
grouped into one convenient PR; anything major falls outside every group
and lands as its own individually-reviewable PR instead. If you hit this
again, check whether the failing PR is a major-version bump that should
never have been grouped in the first place, rather than trying to patch
around the peer-dependency error directly.

## `TypeError: can't compare offset-naive and offset-aware datetimes` comparing an expiry field

**Symptom:** comparing a stored `datetime` column (e.g. `expires_at`,
`reset_token_expires_at`) against `datetime.now(UTC)` raises this `TypeError`
— but only sometimes, or only in tests.

**Cause:** SQLite (used by the test suite — see `tests/conftest.py`) doesn't
have a native timezone-aware timestamp type, so a `DateTime(timezone=True)`
column round-trips as a naive `datetime` under `aiosqlite`, even though the
same column comes back tz-aware under real Postgres. Comparing that naive
value directly against `datetime.now(UTC)` (tz-aware) raises `TypeError`.

**Fix:** call `.replace(tzinfo=UTC)` on the stored value before comparing —
`app/core/deps.py`'s `ApiToken.expires_at` check and `app/api/auth.py`'s
`reset_password` both do this. It's a no-op under Postgres (already UTC) and
fixes the SQLite case. Don't reach for `expires_at.tzinfo is None` branching
— the `.replace()` call is safe unconditionally since every such column is
always stored/interpreted as UTC.

## A running dev container doesn't pick up a newly-added Python dependency

**Symptom:** after adding a new package to `backend/pyproject.toml`'s
`dependencies`, the already-running `myace-backend` dev container (started
via `docker-compose.dev.yml`, which bind-mounts `backend/` for hot-reload)
crashes on reload with `ModuleNotFoundError`, even though the source code
change that imports it is correct and present in the container.

**Cause:** the bind mount syncs *source files*, not the installed package
set — `pyproject.toml` changing doesn't trigger a `pip install` inside an
already-running container. The container's `site-packages` is frozen as of
whenever the image was last built.

**Fix:** for local dev iteration, `docker exec myace-backend pip install
<package>` to unblock the running container immediately, then `docker
compose ... up -d --build` (or just restart the container) once you're done
iterating so the image itself picks up the new dependency for the next
person who builds it. Don't forget the actual fix is the `pyproject.toml`
change — the `pip install` inside the container is a dev-loop shortcut, not
a substitute for it.

## Restoring from a backup dump

**Symptom:** the database is corrupted, accidentally dropped, or you need to
roll back to a known-good state. The `postgres-backup` sidecar has been
writing daily dumps to `./backups/`, but you've never actually tested the
restore path.

**Cause:** the backup sidecar only handles the *dump* side — there's no
automated restore mechanism. You need to run `pg_dump`'s inverse (`psql`)
manually.

**Fix:**
```bash
# 1. List available backups
ls -lh backups/

# 2. Restore a specific dump into the running Postgres container
gunzip -c backups/myace-<date>.sql.gz | \
  docker compose exec -T postgres psql -U myace myace
```

**Before you need it:** test this against a scratch Postgres instance (e.g.
`docker run --rm -e POSTGRES_PASSWORD=test postgres:16-alpine`) to confirm
the dump is valid end-to-end. An untested backup is not a backup.

**Gotcha — the backup sidecar uses the same `POSTGRES_PASSWORD` from `.env`
as the `postgres` and `backend` services.** If you change the password in
`.env` without rebuilding the stack, the backup container will fail to
authenticate on its next scheduled run. Restart the backup container after
any credential change: `docker compose restart postgres-backup`.

## `502 Bad Gateway` from nginx after a backend container restart

**Symptom:** after a `docker compose up -d --build` (or any operation that
recreates the backend container), the frontend returns 502s on every `/api/*`
request. The nginx error log shows `connect() failed (111: Connection refused)
while connecting to upstream`.

**Cause:** nginx resolves upstream hostnames at startup and caches the IP
address. When the backend container is recreated, Docker assigns it a new
internal IP — nginx still points to the old one, which no longer exists.

**Fix:** `frontend/nginx.conf` now uses a variable in `proxy_pass`
(`set $backend_upstream http://backend:8000;`), which forces nginx to resolve
DNS at runtime rather than caching at startup. If you add a new `proxy_pass`
directive elsewhere in the config, use the same variable pattern — a bare
`proxy_pass http://service:port;` will have the same caching problem.

**If you're running an older nginx.conf without the variable fix:** restart
the frontend container after any backend restart:
`docker compose restart frontend`.

## Wiki Sync Action fails with `repository '....wiki.git' not found`

**Symptom:** `.github/workflows/wiki-sync.yml` (`scripts/sync_wiki.py`) fails
on `git push` with `remote: Repository not found.` / `fatal: repository
'https://github.com/<owner>/<repo>.wiki.git/' not found`, even though the
repo's Wiki is enabled (`has_wiki: true`) and the workflow's `GITHUB_TOKEN`
has `contents: write`.

**Cause:** enabling the Wiki feature flag does not provision its git
backend. GitHub only creates a repo's `<repo>.wiki.git` repository the first
time a page is saved through the web UI's page editor. Before that, the
repo genuinely doesn't exist server-side — no `git push`, from CI or
otherwise, with any token, can create it first. This is a one-time,
UI-only bootstrap step; there's no REST/GraphQL API for it.

**Fix:** open `https://github.com/<owner>/<repo>/wiki`, click "Create the
first page," and save anything (even a one-line placeholder). Then re-run
the workflow (`workflow_dispatch`, or push another `docs/` change) — it
overwrites that placeholder with the real generated content. `sync_wiki.py`
detects this specific failure and prints this fix inline rather than a raw
traceback.

## A compiled profile is missing a rule/skill/agent that's definitely enabled in one of its collections

**Symptom:** a profile combining a `base/` collection with one or more
`additional/` collections compiles successfully, but a specific agent,
skill, or rule you know is enabled just isn't in the output.

**Cause:** `compile_profile()` (`backend/app/services/compiler.py`)
deduplicates artifacts **by name alone**, across every collection in the
profile at once: `seen_names[canonical.name] = canonical`, iterated in
`[base_id] + additional_ids` order, so a later collection's artifact
silently replaces an earlier one that happens to share its exact name. Two
starter collections can define, say, an agent both named `security-auditor`
with materially different behavior (different handoff targets, different
scope) — compose them into one profile and only one survives.

**As of AGENTS.md rule 32, this is no longer completely silent**: the
compile response's `warnings` field carries a `name_collision`
`ValidationIssue` naming both collections and which one won —
`myace pull` prints it (yellow) after the file table, and
`TargetExporter.tsx` shows it in a dismissible panel above the file
output. If you're troubleshooting via the API/CLI/UI, check there first.
The steps below are for finding and *fixing* a collision in this repo's
own `collections/` source before it ships, which the warning alone
doesn't help with.

**Fix:** compare the artifact's name (skill: frontmatter `name:`;
agent/workflow: file stem; rule: `AGENTS.md` `##` heading text) against
every other collection in the profile:

```bash
grep -rn "^name:" collections/*/*/skills/*/SKILL.md | sort -t: -k3
```

If two collections do collide, rename the artifact in whichever collection
is the `additional/` one (see rule 29 in `AGENTS.md`) rather than the
`base/` one — base collections' own agents tend to be referenced by name
from other files in the same collection (e.g. `orchestrator.md`'s hardcoded
pipeline routing), so renaming there has a wider blast radius. This is also
why the shipped starter packs use `security-compliance-auditor` /
`security-audit-checklist` (in `additional/auditor`) and `technical-writer`
(in `additional/editor`) instead of names that would collide with
`base/software-engineer`'s `security-auditor` / `security-checklist` /
`docs-writer`.

## The Compile Profile zip download doesn't match the on-screen preview

**Symptom:** `/compile` (TargetExporter.tsx) shows a compiled profile with
several files — e.g. `CLAUDE.md`, `.claude/agents/*.md`,
`.claude/skills/*/SKILL.md` — but clicking "Download as .zip" produces an
archive containing a single, often much larger, file (commonly `AGENTS.md`
from the Goose or OpenCode adapters, which merge everything into one file).

**Cause:** `handleDownloadZip()` in `frontend/src/pages/TargetExporter.tsx`
used to build its `POST /profiles/compile/zip` request body from the *live*
`selectedProfile`/`selectedTarget` dropdown state, not from `result.profile_id`/
`result.target` — the values that actually produced the on-screen preview.
Changing either dropdown after clicking Compile (e.g. comparing two target
frameworks) without clicking Compile again leaves the preview showing the
old result while silently changing what the zip endpoint gets asked to
compile, since the "Download as .zip" button stays enabled as long as
`result` is non-null — it doesn't require re-compiling first.

**Fix:** `handleDownloadZip()` now reads `result.profile_id` and
`result.target` for the request body, guaranteeing the zip always matches
what's rendered on screen regardless of subsequent dropdown changes. See
`TargetExporter.test.tsx`'s "downloads the zip for the compiled result, not
the live target dropdown" test, which reproduces the exact scenario (compile
with one target, switch the dropdown, download, assert the original target
was used) — any future change to this component should keep that test
passing rather than relying on manual reproduction.
