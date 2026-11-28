#!/usr/bin/env bash
# Deploy the checkout on this host to a newer commit, running only the steps the
# change needs. Run it ON the server, from the project checkout.
#
#   scripts/deploy.sh                 # plan, ask, deploy origin/main
#   scripts/deploy.sh --plan-only     # show the plan and stop (needs only git)
#   scripts/deploy.sh --status        # deployed commit, container health, protected counts
#   scripts/deploy.sh --check         # is any seeded pack out of step with its files?
#   scripts/deploy.sh --yes           # no prompts (still refuses to soft-delete without --allow-removals)
#
# What it does, in order: classify the diff between what is deployed and the
# target -> back up the database -> fast-forward -> migrate -> rebuild/restart what
# changed -> wait for health -> reconcile seeded packs (dry run first, human gate)
# -> check that users, ratings, verifications, tokens and settings are unchanged.
#
# Deliberately NOT automatic on merge: reconcile soft-deletes items and
# `--update-metadata` overwrites in-app edits, so a person reads the dry run.
# See docs/deployment.md ("Deploying updates") and AGENTS.md rule 25.
#
# Portable bash (3.2+) so --plan-only also works on a laptop.

set -Eeuo pipefail

ROOT="${DEPLOY_REPO_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
COMPOSE_FILES="${COMPOSE_FILES:--f docker-compose.yml -f docker-compose.prod.yml}"
# Not under $ROOT/backups: the postgres-backup sidecar writes that directory as
# root, so the deploying user usually cannot create anything in it.
BACKUP_DIR="${BACKUP_DIR:-${HOME:-$ROOT}/backups/myace-pre-deploy}"
RECONCILE_FLAGS="${RECONCILE_FLAGS:---update-content --update-metadata}"
SITE_URL="${SITE_URL:-}"

TO="origin/main"
FROM=""
PLAN_ONLY=0
CHECK=0
STATUS=0
YES=0
NO_BACKUP=0
NO_RECONCILE=0
ALLOW_REMOVALS=0

usage() {
  sed -n '2,21p' "$0" | sed 's/^# \{0,1\}//'
  cat <<'EOF'

Options:
  --to REF            target commit or ref (default origin/main)
  --from REV          what is deployed (default HEAD; mostly for --plan-only)
  --plan-only         print the plan and exit; changes nothing
  --status            print the deployed commit, container health and protected counts
  --check             run the reconcile dry run only; exit 3 if packs have drifted
  --yes               do not prompt
  --allow-removals    with --yes, apply a reconcile that soft-deletes items
  --no-backup         skip the pg_dump (not recommended)
  --no-reconcile      skip the reconcile step even when the plan includes it
  --reconcile-flags S flags for the apply (default: --update-content --update-metadata)
  --site-url URL      public URL for the post-deploy smoke test (default: FRONTEND_BASE_URL in .env)
  -h, --help

Environment: COMPOSE_FILES, BACKUP_DIR, RECONCILE_FLAGS, SITE_URL, DEPLOY_REPO_DIR.
EOF
}

die() { echo "error: $*" >&2; exit 1; }
say() { echo "==> $*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --to) TO="${2:?--to needs a value}"; shift 2 ;;
    --from) FROM="${2:?--from needs a value}"; shift 2 ;;
    --plan-only) PLAN_ONLY=1; shift ;;
    --status) STATUS=1; shift ;;
    --check) CHECK=1; shift ;;
    --yes|-y) YES=1; shift ;;
    --allow-removals) ALLOW_REMOVALS=1; shift ;;
    --no-backup) NO_BACKUP=1; shift ;;
    --no-reconcile) NO_RECONCILE=1; shift ;;
    --reconcile-flags) RECONCILE_FLAGS="${2?--reconcile-flags needs a value}"; shift 2 ;;
    --site-url) SITE_URL="${2:?--site-url needs a value}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown option: $1" ;;
  esac
done

cd "$ROOT"
git rev-parse --git-dir >/dev/null 2>&1 || die "$ROOT is not a git checkout"

dc() { # shellcheck disable=SC2086
  docker compose $COMPOSE_FILES "$@"
}

confirm() {
  if [ "$YES" -eq 1 ]; then return 0; fi
  [ -t 0 ] || die "needs a terminal to confirm; re-run with --yes"
  printf '%s [y/N] ' "$1"
  read -r answer
  case "$answer" in y|Y|yes|YES) return 0 ;; *) return 1 ;; esac
}

# --------------------------------------------------------------------------
# Plan: classify changed paths into the steps they require.
# --------------------------------------------------------------------------
FILES=""
has() { grep -Eq "$1" <<<"$FILES"; }
sample() { grep -E "$1" <<<"$FILES" | head -3 | tr '\n' ' '; }

STEP_BACKEND_BUILD=0
STEP_BACKEND_RESTART=0
STEP_MIGRATE=0
STEP_FRONTEND=0
STEP_MCP=0
STEP_RECONCILE=0
STEP_COMPOSE=0
WARN_ENV=0

plan_line() { # flag label why
  local mark=" "
  [ "$1" -eq 1 ] && mark="x"
  printf '  [%s] %-24s %s\n' "$mark" "$2" "${3:-}"
}

classify() {
  FILES="$(git diff --name-only "$1" "$2")"
  local count
  count="$(grep -c . <<<"$FILES" || true)"

  has '^backend/(Dockerfile|pyproject\.toml)$' && STEP_BACKEND_BUILD=1
  # The backend source is bind-mounted, so code needs a restart, not an image
  # build; collections/ is mounted too and new packs seed on boot.
  has '^backend/(app/|alembic/|alembic\.ini)|^collections/' && STEP_BACKEND_RESTART=1
  [ "$STEP_BACKEND_BUILD" -eq 1 ] && STEP_BACKEND_RESTART=1
  has '^backend/alembic/versions/' && STEP_MIGRATE=1
  # Frontend and mcp are baked into their images. Tests and docs are not.
  # Command substitution, not `grep | grep -q`: under pipefail an early-exiting
  # reader can SIGPIPE the writer and flip the result.
  local fe mcp
  fe="$(grep -E '^frontend/' <<<"$FILES" | grep -Ev '\.test\.(ts|tsx)$|\.md$' || true)"
  mcp="$(grep -E '^mcp/' <<<"$FILES" | grep -Ev '^mcp/tests/|\.md$' || true)"
  [ -n "$fe" ] && STEP_FRONTEND=1
  [ -n "$mcp" ] && STEP_MCP=1
  has '^collections/|^backend/app/services/(seed_collections|seed_reconcile)\.py$' && STEP_RECONCILE=1
  has '^docker-compose[^/]*\.yml$' && STEP_COMPOSE=1
  has '^\.env\.example$' && WARN_ENV=1

  echo "Deploy plan: $(git rev-parse --short "$1") -> $(git rev-parse --short "$2") ($count changed files)"
  plan_line "$STEP_BACKEND_BUILD" "backend image rebuild" "$(sample '^backend/(Dockerfile|pyproject\.toml)$')"
  plan_line "$STEP_BACKEND_RESTART" "backend restart" "$(sample '^backend/(app/|alembic/|alembic\.ini)|^collections/')"
  plan_line "$STEP_MIGRATE" "alembic upgrade head" "$(sample '^backend/alembic/versions/')"
  plan_line "$STEP_FRONTEND" "frontend image rebuild" "$(sample '^frontend/')"
  plan_line "$STEP_MCP" "mcp image rebuild" "$(sample '^mcp/')"
  plan_line "$STEP_RECONCILE" "reconcile seeded packs" "$(sample '^collections/|^backend/app/services/seed_')"
  plan_line "$STEP_COMPOSE" "compose up -d" "$(sample '^docker-compose')"
  if [ "$WARN_ENV" -eq 1 ]; then
    echo "  note: .env.example changed; compare it with this host's .env by hand."
  fi
  if [ "$STEP_BACKEND_RESTART$STEP_FRONTEND$STEP_MCP$STEP_RECONCILE$STEP_COMPOSE" = "00000" ]; then
    echo "  Nothing to deploy beyond the pull (docs, tests or CI only)."
  fi
}

# --------------------------------------------------------------------------
# Database helpers (only used on a real run).
# --------------------------------------------------------------------------
psql_q() { # SQL on stdin -> one row, pipe separated
  dc exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA -F"|"'
}

protected_counts() {
  psql_q <<'SQL'
select
  (select count(*) from users),
  (select count(*) from collection_ratings),
  (select count(*) from collections where last_verified_at is not null),
  (select count(*) from api_tokens),
  (select count(*) from system_settings);
SQL
}

seeded_pack_fingerprint() {
  psql_q <<'SQL'
select
  coalesce(sum(avg_rating), 0)::numeric(12,2),
  coalesce(sum(rating_count), 0),
  coalesce(sum(download_count), 0),
  count(*) filter (where last_verified_at is not null)
from collections where git_url like 'seed://%';
SQL
}

wait_healthy() {
  local names="myace-postgres myace-backend myace-frontend"
  if docker inspect myace-mcp >/dev/null 2>&1; then names="$names myace-mcp"; fi
  local deadline=$((SECONDS + 180)) name status all
  while [ "$SECONDS" -lt "$deadline" ]; do
    all=1
    for name in $names; do
      status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$name" 2>/dev/null || echo missing)"
      if [ "$status" != "healthy" ] && [ "$status" != "running" ]; then all=0; fi
    done
    [ "$all" -eq 1 ] && return 0
    sleep 4
  done
  return 1
}

reconcile_dry_run() {
  dc exec -T backend python -m app.scripts.reconcile_seeded_collections 2>&1
}

site_url() {
  if [ -n "$SITE_URL" ]; then echo "$SITE_URL"; return; fi
  [ -f .env ] && sed -n 's/^FRONTEND_BASE_URL=//p' .env | head -1 | tr -d '"' || true
}

# --------------------------------------------------------------------------
# --status: read-only snapshot of this host.
# --------------------------------------------------------------------------
if [ "$STATUS" -eq 1 ]; then
  command -v docker >/dev/null 2>&1 || die "docker is not available on this host"
  say "Deployed: $(git describe --tags --always) ($(git rev-parse --short HEAD), $(git log -1 --format=%cd --date=short))"
  say "Containers:"
  for name in myace-postgres myace-postgres-backup myace-backend myace-frontend myace-mcp; do
    if docker inspect "$name" >/dev/null 2>&1; then
      printf '    %-22s %s\n' "$name" "$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$name")"
    fi
  done
  say "Protected counts (users|ratings|verified|tokens|settings): $(protected_counts)"
  say "Seeded packs (rating sum|ratings|uses|verified): $(seeded_pack_fingerprint)"
  exit 0
fi

# --------------------------------------------------------------------------
# --check: drift between seeded packs and their files, nothing else.
# --------------------------------------------------------------------------
if [ "$CHECK" -eq 1 ]; then
  out="$(reconcile_dry_run)" || { echo "$out"; die "reconcile dry run failed"; }
  echo "$out" | tail -25
  if echo "$out" | grep -q "Nothing to reconcile"; then
    say "No drift: every seeded pack matches its files."
    exit 0
  fi
  say "Drift: seeded packs differ from their files. Deploy, or run the reconcile apply."
  exit 3
fi

# --------------------------------------------------------------------------
# Plan-only mode needs no docker and no network.
# --------------------------------------------------------------------------
if [ "$PLAN_ONLY" -eq 1 ]; then
  [ -n "$FROM" ] || FROM="HEAD"
  classify "$FROM" "$TO"
  exit 0
fi

# --------------------------------------------------------------------------
# Real run.
# --------------------------------------------------------------------------
command -v docker >/dev/null 2>&1 || die "docker is not available on this host"
[ -z "$(git status --porcelain)" ] || die "the working tree has uncommitted changes; commit or stash them first"
[ -f .env ] || die "no .env in $ROOT; is this the deployed checkout?"

say "Fetching origin"
git fetch --quiet origin
[ -n "$FROM" ] || FROM="$(git rev-parse HEAD)"
git rev-parse --verify --quiet "$TO^{commit}" >/dev/null || die "unknown target: $TO"
FROM_SHA="$(git rev-parse "$FROM")"
TO_SHA="$(git rev-parse "$TO")"

if [ "$FROM_SHA" = "$TO_SHA" ]; then
  say "Already at $(git rev-parse --short "$TO_SHA"). Use --check to look for pack drift."
  exit 0
fi
git merge-base --is-ancestor "$FROM_SHA" "$TO_SHA" || die "$TO is not a fast-forward of the deployed commit; refusing"

classify "$FROM_SHA" "$TO_SHA"
echo
confirm "Deploy this?" || { echo "Aborted; nothing changed."; exit 1; }

RUNNING="$(dc ps --status running --services 2>/dev/null || true)"
grep -q '^backend$' <<<"$RUNNING" || die "the backend container is not running; start the stack first"

BACKUP_FILE=""
BEFORE="$(protected_counts)"
PACKS_BEFORE="$(seeded_pack_fingerprint)"
say "Protected counts before (users|ratings|verified|tokens|settings): $BEFORE"

STARTED=0
on_exit() {
  local code=$?
  if [ "$code" -ne 0 ] && [ "$STARTED" -eq 1 ]; then
    echo >&2
    echo "DEPLOY FAILED (exit $code). Deployed commit before: $(git rev-parse --short "$FROM_SHA")." >&2
    if [ -n "$BACKUP_FILE" ]; then echo "Database backup: $BACKUP_FILE" >&2; fi
    echo "Nothing is rolled back automatically. See docs/deployment.md (Deploying updates) for recovery." >&2
  fi
}
trap on_exit EXIT

STARTED=1
if [ "$NO_BACKUP" -eq 0 ]; then
  mkdir -p "$BACKUP_DIR" || die "cannot create BACKUP_DIR ($BACKUP_DIR); set BACKUP_DIR to a directory you can write"
  BACKUP_FILE="$BACKUP_DIR/$(date +%Y%m%d-%H%M%S)-from-$(git rev-parse --short "$FROM_SHA").sql.gz"
  say "Backing up the database to $BACKUP_FILE"
  dc exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$BACKUP_FILE"
  gzip -t "$BACKUP_FILE"
  [ "$(wc -c < "$BACKUP_FILE")" -gt 1024 ] || die "backup looks empty: $BACKUP_FILE"
else
  say "Skipping the backup (--no-backup)"
fi

say "Fast-forwarding to $(git rev-parse --short "$TO_SHA")"
git merge --ff-only "$TO_SHA" >/dev/null

if [ "$STEP_COMPOSE" -eq 1 ]; then
  say "Compose files changed: bringing the stack up to date"
  dc up -d
fi

if [ "$STEP_BACKEND_BUILD" -eq 1 ]; then
  say "Rebuilding the backend image"
  dc build backend
fi

if [ "$STEP_BACKEND_RESTART" -eq 1 ]; then
  # Migrate with the new code but before it serves traffic. `alembic upgrade
  # head` is a no-op when nothing is pending, so it runs whenever the backend does.
  say "Applying pending migrations"
  dc run -T --rm --no-deps backend alembic upgrade head 2>&1 | tail -5
  if [ "$STEP_BACKEND_BUILD" -eq 1 ]; then
    dc up -d backend
  else
    dc restart backend
  fi
fi

if [ "$STEP_FRONTEND" -eq 1 ]; then
  say "Rebuilding the frontend image"
  dc up -d --build frontend
fi

if [ "$STEP_MCP" -eq 1 ]; then
  if docker inspect myace-mcp >/dev/null 2>&1; then
    say "Rebuilding the mcp image"
    dc --profile mcp up -d --build mcp
  else
    say "mcp is not deployed on this host; skipping its rebuild"
  fi
fi

say "Waiting for containers to be healthy"
wait_healthy || die "containers did not become healthy within 3 minutes (docker compose ps)"

if [ "$STEP_RECONCILE" -eq 1 ] && [ "$NO_RECONCILE" -eq 0 ]; then
  say "Reconcile dry run"
  DRY="$(reconcile_dry_run)" || { echo "$DRY"; die "reconcile dry run failed"; }
  echo "$DRY" | tail -60
  if echo "$DRY" | grep -q "Nothing to reconcile"; then
    say "No pack drift; nothing to apply."
  else
    REMOVALS="$(echo "$DRY" | grep -E '^\s+- (remove|duplicate):' || true)"
    if [ -n "$REMOVALS" ]; then
      echo
      echo "This reconcile will SOFT-DELETE items:"
      echo "$REMOVALS"
      if [ "$YES" -eq 1 ] && [ "$ALLOW_REMOVALS" -eq 0 ]; then
        die "refusing to auto-apply a reconcile that soft-deletes items; re-run with --allow-removals after reading the list, or apply it by hand"
      fi
    fi
    if confirm "Apply with: --apply $RECONCILE_FLAGS ?"; then
      # shellcheck disable=SC2086
      dc exec -T backend python -m app.scripts.reconcile_seeded_collections --apply $RECONCILE_FLAGS 2>&1 | tail -8
      AFTER_DRY="$(reconcile_dry_run)"
      if echo "$AFTER_DRY" | grep -q "Nothing to reconcile"; then
        say "Reconcile applied; a second dry run is clean."
      else
        echo "$AFTER_DRY" | tail -15
        echo "warning: a second reconcile dry run still reports differences (see above)." >&2
      fi
    else
      say "Reconcile NOT applied. Run: scripts/deploy.sh --check, or apply it by hand."
    fi
  fi
fi

say "Verifying protected data"
AFTER="$(protected_counts)"
PACKS_AFTER="$(seeded_pack_fingerprint)"
if [ "$BEFORE" != "$AFTER" ]; then
  echo "before: $BEFORE" >&2
  echo "after:  $AFTER" >&2
  die "protected counts changed (users|ratings|verified|tokens|settings)"
fi
if [ "$PACKS_BEFORE" != "$PACKS_AFTER" ]; then
  echo "before: $PACKS_BEFORE" >&2
  echo "after:  $PACKS_AFTER" >&2
  die "seeded packs' ratings, use counts or verifications changed"
fi
say "Protected counts unchanged: $AFTER"

URL="$(site_url)"
if [ -n "$URL" ] && command -v curl >/dev/null 2>&1; then
  say "Smoke test against $URL"
  curl -fsS -o /dev/null "$URL/api/v1/collections/community?limit=1" || die "the public pack list did not answer"
  if docker inspect myace-mcp >/dev/null 2>&1; then
    MCP_RESP="$(curl -fsS -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
      "$URL/mcp" -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_targets","arguments":{}}}')" \
      || die "the MCP server did not answer"
    grep -q '"result"' <<<"$MCP_RESP" || die "the MCP list_targets call returned no result"
  fi
else
  say "No site URL (set FRONTEND_BASE_URL in .env or pass --site-url); skipping the external smoke test"
fi

STARTED=0
echo
say "Deployed $(git rev-parse --short "$FROM_SHA") -> $(git rev-parse --short "$TO_SHA")"
if [ -n "$BACKUP_FILE" ]; then echo "    Backup: $BACKUP_FILE (restore steps: docs/backups.md)"; fi
echo "    Previous commit: $FROM_SHA"
