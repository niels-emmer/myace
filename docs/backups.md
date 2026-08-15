# Backups

A `postgres-backup` sidecar container runs alongside Postgres in the same
stack (`docker-compose.yml`), wrapping `pg_dump` on a daily schedule with
built-in retention. It uses the
[`prodrigestivill/postgres-backup-local`](https://github.com/prodrigestivill/docker-postgres-backup-local)
image and writes compressed `.sql.gz` dumps to `./backups/` on the host.

## Retention defaults

Configurable via environment overrides in the compose file or `.env`:

| Setting | Default | Meaning |
|---------|---------|---------|
| `SCHEDULE` | `@daily` | Cron expression or `@daily`/`@weekly`/`@monthly` |
| `BACKUP_KEEP_DAYS` | `7` | Daily dumps kept for 7 days |
| `BACKUP_KEEP_WEEKS` | `4` | Weekly dumps kept for 4 weeks |
| `BACKUP_KEEP_MONTHS` | `6` | Monthly dumps kept for 6 months |

## Offsite copy

Not automated by this stack — the dumps live on the same host disk as the
database, so a host failure loses both. For production deployments, add a
host-level cron job to copy `./backups/` off-box (e.g. `rclone sync` to
Backblaze B2 or S3, or `rsync` to another machine).

## Restore

```bash
# List available backups
ls -lh backups/

# Restore a specific dump
gunzip -c backups/myace-<date>.sql.gz | \
  docker compose exec -T postgres psql -U myace myace
```

> **Test your restore procedure before you need it.** Run the restore
> against a scratch database on a separate Postgres instance to confirm the
> dump is valid end-to-end. An untested backup is not a backup.

See also [debugging.md#restoring-from-a-backup-dump](debugging.md#restoring-from-a-backup-dump)
for a troubleshooting walkthrough if a restore doesn't go cleanly.
