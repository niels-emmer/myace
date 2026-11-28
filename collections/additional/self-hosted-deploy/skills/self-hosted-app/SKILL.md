---
name: Self-Hosted App
description: Conventions for the single-container, single-database self-hosted web app — admin panel, backup and restore, health checks, and reverse-proxy deployment.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [self-hosted, sqlite, admin-panel, backup, reverse-proxy, deployment]
---
## Purpose

Describe the small, operable self-hosted archetype: one deployable application
container, one local database file, and just enough surface to run it safely on
a server you control. The goal is an app a single maintainer can deploy,
back up, restore, and diagnose without a platform team.

## When to use it

Building a self-hosted app — a dashboard, a status page, a personal tool, a
small internal service — where multi-tenant scale, a managed database, or a
queue would be overkill.

## The archetype

- One **application container**, small and dependency-light.
- One **database file** as the only state, on a mounted volume.
- An **admin panel** with authentication to edit content.
- **Backup and restore** of the database.
- A **health endpoint** consumed by the container runtime and deploy scripts.
- Optional **outbound-only helpers** (mail relay, screenshot worker).
- Deployed behind a **reverse proxy** that terminates TLS.

## Repository skeleton

```
AGENTS.md
README.md  CHANGELOG.md  LICENSE  SECURITY.md  CONTRIBUTING.md  CODE_OF_CONDUCT.md
.editorconfig  .gitignore  .dockerignore  .env.example
Dockerfile  docker-compose.yml
docs/{ARCHITECTURE,DEVELOPMENT,DEPLOYMENT,decision-log}.md
src/  test/  scripts/  public/
```

Add a third-party dependency ledger once dependencies ship, and a threat-model
directory once the app stores user input.

## Core modules (one responsibility each)

Keep the source small and single-purpose:

- **app wiring** — server setup only, no business logic.
- **db** — open, migrate, and query the database file.
- **config** — read and validate environment variables; fail fast on missing
  required values.
- **auth** — admin session (hash plus signed cookie), constant-time comparison.
- **validation** — the single place input is validated.
- **health** — returns status and version.
- **backup** — export and import the database.
- **mailer** — outbound only; never blocks a request.

## Admin panel and auth

- Session cookie is `HttpOnly`, `SameSite=Lax`, and `Secure` under TLS.
- Hash passwords with bcrypt or argon2; compare in constant time.
- Gate every mutating route behind the admin session; public routes are
  read-only.
- Rate-limit login and any public write route.

## Backup and restore

- Backup is a consistent snapshot of the database file — for SQLite, `VACUUM
  INTO` or the `.backup` command — downloadable by an admin.
- Restore is upload, validate, replace, restart — and it must be reversible.
- Never expose a backup without the admin session; keep the last few with
  timestamps.

## Health and observability

- `/health` returns `200` with `{status, version}` and is wired into the
  container healthcheck and deploy scripts.
- Log structured events to stdout; never log secrets.

## Networking and reverse proxy

- The app joins the reverse-proxy network; the proxy terminates TLS and
  forwards to it.
- Internal helpers live on a dedicated network with no published port, reachable
  only by the app.
- Publish no host port that the proxy does not need.

## Configuration and secrets

- `.env.example` documents every variable with a safe default; the real
  environment file is gitignored.
- No secrets in the image, compose file, or repository — inject them at run
  time.
- Local-development defaults are explicit, never accidental.

## Deployment loop

1. Commit (through a pull request if the default branch is protected); mark AI-authored commits with an `[ai]` line in the body.
2. On the host, pull the change and rebuild/restart the compose stack.
3. Verify `/health` and load the page.
4. Roll back by checking out the previous tag and re-running compose.

## Docs set

`AGENTS.md` (the portable contract, written first), plus architecture,
development, deployment, and decision-log documents. Keep `AGENTS.md` short and
reference detail.

## Definition of done

- [ ] Container builds and starts as non-root, with a healthcheck.
- [ ] `/health` returns ok; the page renders from the database.
- [ ] Admin auth works; public write routes are rate-limited.
- [ ] Backup downloads and restore round-trips.
- [ ] Tests pass **and** the running app was exercised — a green suite is not a
      working feature.
- [ ] No secrets in the repository; `.env.example` is complete.
- [ ] `AGENTS.md` and the docs set are present.

## Output format

```
## Self-hosted app summary
- Container(s): <list>
- State: <database path / volume>
- Admin auth: yes / no
- Health endpoint: yes / no
- Backup/restore: yes / no
- Reverse-proxy network: yes / no
- Docs set: complete / missing <files>
- Verified by running: yes / no
```
