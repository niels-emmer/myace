# Plan: Automated Postgres Backups

## Status

**Shipped.** The `postgres-backup` sidecar described below is live in the
base `docker-compose.yml` (not `docker-compose.prod.yml`-only, resolving
the last open question), using the exact defaults proposed here. See
[docs/backups.md](../backups.md) for the current retention table and
restore procedure. The offsite-copy step (§2) remains unautomated by the
stack itself, as noted there. Kept here as historical design record, not a
live task list.

Original problem statement, for context:

## Problem

`postgres-data` (`docker-compose.yml`) is a plain named Docker volume with no
dump job, no offsite copy, and no documented restore procedure — in the repo,
in `docs/`, or in `scripts/`. On the VPS deployment (`docker-compose.yml` +
`docker-compose.prod.yml`, see [`~/myace` on the VPS — reference in global
memory]), that volume is the only copy of every user's account (password
hash), API tokens, collections, artifacts, and profiles.

Since registration is open and the app is publicly hosted (and hostable by
other operators), a host disk failure, an accidental `docker volume rm`, or a
bad migration is currently unrecoverable data loss with no fallback. This
plan describes the minimal setup to close that gap.

## Goals

- Automated, unattended daily backups — no manual step to remember.
- Retention (daily/weekly/monthly), not just "last night's dump" — need to
  survive a corruption that isn't noticed for a few days.
- A copy that lives off the VPS itself, so a lost/destroyed host doesn't
  take the backups down with it.
- A documented, tested restore procedure — an untested backup is not a
  backup.
- Config lives in the repo (compose files / `.env.example`), consistent with
  how the rest of the deployment is managed, not a hand-configured cron job
  that only exists on one operator's VPS.

## Non-goals

- Point-in-time recovery / WAL streaming — daily `pg_dump` snapshots are
  enough for this app's scale and RPO tolerance. Revisit only if data volume
  or write rate grows enough to make a full-day loss unacceptable.
- Automating failover to a second Postgres instance — out of scope; this is
  about not losing data, not minimizing downtime.

## Proposed approach

### 1. In-stack backup sidecar

Add a `postgres-backup` service to `docker-compose.prod.yml` (and optionally
`docker-compose.yml` for single-machine installs, since any operator running
the base compose file has the same exposure) using
[`prodrigestivill/postgres-backup-local`](https://github.com/prodrigestivill/docker-postgres-backup-local).
It wraps `pg_dump` on a schedule with built-in retention, so no separate cron
infrastructure is needed on the host:

```yaml
services:
  postgres-backup:
    image: prodrigestivill/postgres-backup-local:16
    restart: unless-stopped
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_DB=${POSTGRES_DB:-myace}
      - POSTGRES_USER=${POSTGRES_USER:-myace}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-myace_secret}
      - SCHEDULE=@daily
      - BACKUP_KEEP_DAYS=7
      - BACKUP_KEEP_WEEKS=4
      - BACKUP_KEEP_MONTHS=6
    volumes:
      - ./backups:/backups
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - myace
```

Notes for whoever implements this:

- `./backups` should be added to `.gitignore` — it's host-local data, not
  repo content.
- Runs on the private `myace` network only, same as `postgres` — no exposed
  ports.
- `POSTGRES_PASSWORD` here duplicates what `postgres`/`backend` already read
  from `.env`; keep them in sync the same way `docker-compose.yml`'s
  `backend.environment.DATABASE_URL` already does.

### 2. Offsite copy

The sidecar alone only protects against schema mistakes or accidental
deletion — the dumps still live on the same disk as the VPS, so a host
failure loses both the live DB and the backups together. Close that with a
scheduled off-box copy, in order of preference:

1. **`rclone` cron to object storage** (Backblaze B2 or S3) — a single
   `rclone sync ~/myace/backups/ remote:myace-backups` line in the VPS's
   crontab, run daily after the dump job. B2's free tier comfortably covers
   a DB this size. Needs `rclone config` run once to store credentials.
2. **`rsync`/`scp` to a second machine** if avoiding a cloud dependency is
   preferred — same idea, different destination.

### 3. Restore procedure (to document in `docs/` once built)

```bash
gunzip -c backups/myace-<date>.sql.gz | \
  docker compose exec -T postgres psql -U myace myace
```

This needs to actually be run against a scratch DB once during
implementation to confirm it works end-to-end — an untested restore path is
the same as not having one.

### 4. Documentation

Once implemented:

- Add a short "Backups & Restore" section to `README.md` (near the Compose
  Files table). *(Actual outcome: a dedicated [docs/backups.md](../backups.md),
  linked from README's Getting Started, with the Compose Files table living
  in [docs/deployment.md](../deployment.md#compose-files).)*
- Add the restore command and troubleshooting to `docs/debugging.md` or a
  new `docs/ops.md`, whichever this repo settles on as the home for
  operational (not architectural) docs.
- Note the new `postgres-backup` service and `./backups` mount in
  `CLAUDE.md`'s deployment-hardening section, consistent with how other
  `docker-compose.prod.yml` behavior is documented there.

## Open questions

- Object storage account/credentials for the offsite copy aren't set up yet
  — needs a decision on provider (B2 vs S3 vs other) before step 2 can be
  implemented.
- Whether `docker-compose.yml` (single-machine prod, no reverse proxy) should
  ship the backup sidecar by default, or whether it should live only in
  `docker-compose.prod.yml` and be opt-in for simpler installs.
