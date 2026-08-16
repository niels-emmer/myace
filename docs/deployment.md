# Deployment

MyACE is designed to be forked and self-hosted, not run as someone else's
SaaS. This document covers everything past the [README's Quick
Start](../README.md#getting-started): hardening a fork before exposing it,
running it in production on a single machine, and running it on a VPS
behind a reverse proxy (including a full nginx-proxy-manager walkthrough).

For the three-file Compose layering these commands build on, see
[Compose files](#compose-files) below or
[architecture.md#deployment-shapes](architecture.md#deployment-shapes).

## Fork it and make it yours

After forking, before exposing it beyond localhost:

1. Update `.env`:
   - Set a real random `APP_SECRET_KEY` (it signs session cookies; the app
     **refuses to start** in production if you leave the default — it's a
     `RuntimeError`, not a warning). Generate with `openssl rand -hex 32`.
   - Set `DEBUG=false` (the default, `true`, exposes `/docs`/`/redoc`
     publicly and disables secure-only cookies).
   - Change `POSTGRES_PASSWORD` from the shipped default.
   - Register your own account, then set `ADMIN_BOOTSTRAP_ENABLED=false` and
     restart — otherwise the *next* person to register on a public
     deployment becomes an admin too, not just the first.
   - Set `CORS_ORIGINS` to your real domain(s), and **`TRUSTED_HOSTS`** too
     (required in production — the app refuses to start without it, to
     prevent Host-header injection attacks).
   - Set `SETTINGS_ENCRYPTION_KEY` if you plan to save SMTP or OAuth
     provider secrets from the System Settings UI (rather than only via
     `.env`) — required before those forms can save; generate with
     `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
     See [ADR-0006](adr/0006-encrypted-admin-editable-secrets.md).
2. Optionally configure OIDC/GitHub/Google SSO — via `.env`
   ([`.env.example`](../.env.example)) or from System Settings → Authentication
   Providers in the admin UI. See
   [extending.md#adding-an-sso-provider](extending.md#adding-an-sso-provider).
3. Optionally configure SMTP for password-reset emails, the same way — via
   `.env` or System Settings → Email (SMTP), with a "Send Test Email"
   button to verify it. See
   [extending.md#configuring-smtp-for-password-reset](extending.md#configuring-smtp-for-password-reset).
4. Deploy with `docker-compose.prod.yml` behind your own reverse proxy — see
   [Production (VPS behind a reverse proxy)](#production-vps-behind-a-reverse-proxy)
   below.

The first person to register an account automatically becomes an admin, as
long as `ADMIN_BOOTSTRAP_ENABLED` is still `true` (the default) — that's
step 1's "register your own account" above.

## Production (single machine)

```bash
docker compose up -d --build
# Access at http://localhost:80
```

## Production (VPS behind a reverse proxy)

```bash
# 1. Create an external Docker network for your proxy:
docker network create my-proxy-net

# 2. Set the network name in .env:
echo "PROXY_NETWORK=my-proxy-net" >> .env

# 3. Start the stack (no host ports exposed):
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 4. Configure your proxy to forward:
#    http://frontend:80   → your domain (SPA)
#    http://backend:8000  → api.your-domain.com (API)
```

### Using nginx-proxy-manager

1. In `.env`, set `PROXY_NETWORK` to whatever Docker network your
   nginx-proxy-manager container is attached to (check with
   `docker network ls` / `docker inspect <npm-container>`), then
   `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`.
   `frontend` and `backend` will join that network and be reachable by
   container name from NPM, with no host ports of their own.
2. Add two Proxy Hosts in NPM:
   - Your main domain (e.g. `myace.example.com`) → Forward Hostname/IP
     `frontend`, Forward Port `80`.
   - An API subdomain (e.g. `api.myace.example.com`) → Forward Hostname/IP
     `backend`, Forward Port `8000`.
3. On both Proxy Hosts: enable **Force SSL** (request a cert via NPM's Let's
   Encrypt integration) and leave "Websockets Support" off — this app
   doesn't use any. NPM forwards `X-Forwarded-Proto`/`X-Forwarded-For` by
   default, which pairs with the backend's `--proxy-headers` uvicorn flag
   (`backend/Dockerfile`) to make OIDC redirect URIs resolve to `https://`
   correctly.
4. Set `CORS_ORIGINS=https://myace.example.com` in `.env` (the frontend
   domain, not the API one) and restart the backend.
5. `SessionMiddleware`'s cookie has no explicit `domain=` set, so it's
   scoped to whichever host actually issues it — fine as shipped, since the
   frontend proxies `/api/*` through its own origin (path-based, same
   domain). You'd only need `domain=".example.com"` added in
   `backend/app/main.py` if you instead split the frontend and API onto
   different subdomains and called the API directly from browser JS.

If something doesn't resolve correctly behind a proxy (redirect URIs
resolving to `http://` instead of `https://`, for example), see
[debugging.md](debugging.md) — that failure mode and its fix are documented
there.

## Compose files

Three Compose files layer on top of each other:

| File | Command | Use case | Access |
|------|---------|----------|--------|
| `docker-compose.yml` | `docker compose up -d` | Single-machine prod | `http://localhost:80` |
| `+ docker-compose.dev.yml` | `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d` | Development | Frontend `:80`, API `:8000`, home dir mounted at `/host-home` |
| `+ docker-compose.prod.yml` | `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` | VPS behind proxy | No host ports; attach via `PROXY_NETWORK` env var |

See [`AGENTS.md`](../AGENTS.md#9-compose-file-strategy) for what each
override layer is responsible for.

## Download-digest cron job

Owners who opt into "notify me on downloads" (per-profile preference, see
[README.md](../README.md)) get a daily digest email, not a per-download
email. There is no in-process scheduler in this backend, so the digest is
a standalone script — `backend/app/scripts/send_download_digests.py` —
meant to be invoked once a day by the host's crontab, not run in-process
or on multiple hosts concurrently (the watermark update it does isn't
safe under concurrent runs).

Add a crontab entry on the Docker host, e.g. once daily at 06:00:

```cron
0 6 * * * cd /path/to/myace && docker compose exec -T backend python -m app.scripts.send_download_digests >> /var/log/myace-digest.log 2>&1
```

The script is a no-op (logs a notice, exits 0) if SMTP isn't configured
or enabled in System Settings — safe to add to cron before SMTP is set up.

## Collection freshness digest cron job

Moderators/admins get a weekly email digest when any approved community
collection's manual freshness verification is missing or has aged past
`COLLECTION_FRESHNESS_THRESHOLD_DAYS` (default 180, ~6 months) — see
[data-model.md](data-model.md#freshness-verification) and
[ADR-0011](adr/0011-public-demo-sandbox.md)'s sibling feature note. Same
"no in-process scheduler" shape as the download-digest script above:
`backend/app/scripts/check_collection_freshness.py`, meant for the host's
crontab, not run in-process.

Add a crontab entry, e.g. once weekly on Monday at 07:00:

```cron
0 7 * * 1 cd /path/to/myace && docker compose exec -T backend python -m app.scripts.check_collection_freshness >> /var/log/myace-freshness-digest.log 2>&1
```

Also a no-op if SMTP isn't configured/enabled, and safe to add before SMTP
is set up. Unlike the download-digest script, there's no watermark to
protect — the script always recomputes today's stale count fresh each run.

## Backups

Database backups (retention, restore procedure, offsite copy guidance) are
covered separately in [backups.md](backups.md).
