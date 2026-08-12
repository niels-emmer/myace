# MyACE — My Agentic Coding Environment

[![CI](https://github.com/niels-emmer/myace/actions/workflows/ci.yml/badge.svg)](https://github.com/niels-emmer/myace/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](backend/pyproject.toml)
[![Node 20+](https://img.shields.io/badge/node-20%2B-green)](frontend/package.json)

**MyACE makes your AI coding agent's rules, skills, and workflows portable.**
Write them once, keep them in one place, and compile them into whatever
format Claude Code, OpenCode, Cursor (and whatever comes next) actually
expects — instead of hand-maintaining N slightly-different copies, or
picking one tool and losing the rest.

<table>
  <tr>
    <td width="50%"><img src="docs/images/login.png" alt="MyACE login screen" /></td>
    <td width="50%"><img src="docs/images/dashboard.png" alt="MyACE dashboard" /></td>
  </tr>
  <tr>
    <td width="50%"><img src="docs/images/collections.png" alt="MyACE collections" /></td>
    <td width="50%"><img src="docs/images/compile.png" alt="MyACE compile — a sample profile compiled to OpenCode" /></td>
  </tr>
</table>

## Why this exists

If you've built up a set of coding conventions, review rubrics, or agent
personas you like, you've probably hit this: every framework wants them in
a different shape. OpenCode wants Markdown skill/agent/command files under
`.opencode/` plus an `AGENTS.md` and a JSON `opencode.json` for models/MCP.
Claude Code wants `CLAUDE.md` plus `.claude/agents/*.md`. Cursor wants
`.cursorrules` and `.mdc` files. None of that structure is really about the
*content* — it's packaging.

MyACE stores the content once, as Markdown with YAML frontmatter (the
**Canonical IR**), and translates it into each framework's native layout on
demand — from a web UI, or with a one-line CLI pull.

## Features

- **Import from anywhere** — scan a local config directory (`~/.claude`,
  `~/.config/opencode`, `~/.cursor`) or a GitHub repo, pick exactly which
  rules/skills/agents to bring in, and they become a portable **Collection**.
- **Compose, don't copy** — a **Profile** combines a base collection with
  additional ones, layered by priority, with individual items toggled on or
  off — a named recipe you compile per target, not a duplicated file tree.
- **Compile to any supported framework** — one click (or `myace pull`) turns
  a profile into the exact files Claude Code, OpenCode, or Cursor expect.
- **Export back out** — push a collection to a new GitHub branch and open a
  PR, so your canonical source of truth can live in its own repo.
- **Community collections** — publish your collections to make them public
  immediately, browse and import collections published by other users. This
  is self-serve, not admin-moderated.
- **Starter packs out of the box** — every fresh install seeds itself with 2
  base collections (Vibecoder, Software Engineer) and 5 goal-specific ones
  (Frontend, Backend, Infrastructure as Code Expert, Security Auditor,
  Documentation Editor), so there's real, opinionated content to build a
  first profile from on day one. This is a fixed, code-reviewed set
  maintained in [`collections/`](collections/) — separate from user-published
  community collections, and not affected by them.
- **A real CLI** — `myace login`, `myace pull`, `myace import --push`. Script
  it, put it in a dotfiles repo, run it on a fresh machine.
- **Real multi-user auth** — email+password (with email-based password
  reset) or OIDC/GitHub/Google SSO, private-by-default collections and
  profiles with an explicit public/private flag, and an admin role for
  oversight. Not a toy single-user hack.
- **Admin controls in the UI, no redeploy needed** — configure SMTP and
  OAuth provider credentials (Client ID/Secret, redirect URLs, a
  connectivity test button) from System Settings instead of editing `.env`;
  enable/disable target adapters and other users' accounts system-wide.
- **Responsive** — the web UI works on a phone-width screen (a slide-out
  drawer replaces the sidebar below ~1024px), not just desktop.

## How it works

```mermaid
flowchart LR
    Browser["Browser"] -->|HTTPS| Frontend["Frontend<br/>React SPA / nginx"]
    Frontend -->|"/api/* proxy"| Backend["Backend<br/>FastAPI"]
    CLI["CLI (myace)"] -->|Bearer token| Backend
    Backend --> DB[("PostgreSQL")]
    Backend -->|push branch + PR| GitHub[("GitHub")]
```

A FastAPI backend owns the data and does all the real work; the React
frontend and the CLI are both thin clients of the same API. See
[`docs/architecture.md`](docs/architecture.md) for the full picture,
including the compilation pipeline and the auth model.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for the CLI)
- Node.js 20+ (for frontend development)

### Clone and run it

```bash
git clone https://github.com/niels-emmer/myace.git
cd myace

# 1. Configure environment
cp .env.example .env

# 2. Start the dev stack (hot reload, direct ports, home dir mounted for import)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# 3. Run database migrations
docker compose exec backend alembic upgrade head

# 4. Access
#    Web UI:       http://localhost:80
#    API (direct): http://localhost:8000
#    API Docs:     http://localhost:8000/docs

# For Vite HMR during frontend development:
cd frontend && npm run dev   # starts on :5173, proxies /api to :8000
```

The first person to register an account automatically becomes an admin,
as long as `ADMIN_BOOTSTRAP_ENABLED` is still `true` (the default) — see
step 1 below for why you should turn it off again once that's you.

### Fork it and make it yours

MyACE is designed to be forked and self-hosted, not run as someone else's
SaaS. After forking:

1. Update `.env` before exposing it beyond localhost:
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
     See [ADR-0006](docs/adr/0006-encrypted-admin-editable-secrets.md).
2. Optionally configure OIDC/GitHub/Google SSO — via `.env`
   ([`.env.example`](.env.example)) or from System Settings → Authentication
   Providers in the admin UI. See
   [`docs/extending.md#adding-an-sso-provider`](docs/extending.md#adding-an-sso-provider).
3. Optionally configure SMTP for password-reset emails, the same way — via
   `.env` or System Settings → Email (SMTP), with a "Send Test Email"
   button to verify it. See
   [`docs/extending.md#configuring-smtp-for-password-reset`](docs/extending.md#configuring-smtp-for-password-reset).
4. Deploy with `docker-compose.prod.yml` behind your own reverse proxy — see
   [Production deployment](#production-vps-behind-a-reverse-proxy) below.

### Production (single machine)

```bash
docker compose up -d --build
# Access at http://localhost:80
```

### Production (VPS behind a reverse proxy)

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

#### Using nginx-proxy-manager

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

### Quick install (binary, no Python required)

Download the binary for your platform from the
[latest release](https://github.com/niels-emmer/myace/releases):

```bash
# Linux (x86_64)
curl -fsSL https://github.com/niels-emmer/myace/releases/latest/download/myace-linux-x86_64 -o myace
chmod +x ./myace
sudo mv ./myace /usr/local/bin/

# macOS (Intel)
curl -fsSL https://github.com/niels-emmer/myace/releases/latest/download/myace-macos-x86_64 -o myace
chmod +x ./myace
sudo mv ./myace /usr/local/bin/

# macOS (Apple Silicon)
curl -fsSL https://github.com/niels-emmer/myace/releases/latest/download/myace-macos-arm64 -o myace
chmod +x ./myace
sudo mv ./myace /usr/local/bin/
```

**Windows:** Download `myace-windows-x86_64.exe` from the
[releases page](https://github.com/niels-emmer/myace/releases) and place it
somewhere in your `PATH`.

Then authenticate and start using it:

```bash
myace login --server <your-server-url> --token <your-api-token>
myace --help
```

Create an API token from the web UI's Settings page.

> **Note for macOS users:** The binary is not signed with an Apple Developer
> certificate. The first time you run it, Gatekeeper may block it. To bypass:
> open **System Settings → Privacy & Security**, scroll to the security
> section, and click **Allow Anyway** next to the `myace` entry. Or remove the
> quarantine attribute manually: `xattr -d com.apple.quarantine /usr/local/bin/myace`.

### CLI setup (via pip)

If you prefer to install via pip (requires Python 3.12+):

```bash
cd cli
pip install -e .
myace login --server http://localhost:8000 --token <your-api-token>
myace --help
```

## Documentation

| Document | What it covers |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Components, compilation pipeline, canonical IR, auth model |
| [`docs/data-model.md`](docs/data-model.md) | Every table, its columns, and how they relate |
| [`docs/invariants.md`](docs/invariants.md) | Rules the system must never violate, and where they're enforced |
| [`docs/extending.md`](docs/extending.md) | How to add an adapter, artifact type, SSO provider, or route |
| [`docs/debugging.md`](docs/debugging.md) | Known gotchas — symptom, cause, fix |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records — why the non-obvious choices were made |
| [`AGENTS.md`](AGENTS.md) / `CLAUDE.md` | Rules and conventions for AI coding agents working in this repo |

`docs/` is written for both humans and AI coding agents — start there for
anything deeper than "how do I run this."

## Contributing

Bug reports, feature requests, and PRs are welcome — see
[`CONTRIBUTING.md`](CONTRIBUTING.md) for the development setup, conventions,
and PR process. Please read [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) too.

Found a security issue? Please don't open a public issue — see
[`SECURITY.md`](SECURITY.md) for how to report it privately.

## Maintaining & updating

- **Schema changes** ship as Alembic migrations
  (`docker compose exec backend alembic upgrade head` to apply). Every
  migration has a working `downgrade()` — see
  [`AGENTS.md`](AGENTS.md#2-database-migration-rules).
- **CI** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs
  lint, type-check, and tests for the backend, CLI, and frontend on every
  PR, plus a Docker build check.
- **Dependabot** ([`.github/dependabot.yml`](.github/dependabot.yml)) opens
  weekly PRs for backend/CLI (pip), frontend (npm), Docker base images, and
  GitHub Actions themselves. Minor/patch bumps within each ecosystem are
  grouped into one PR for convenience; major-version bumps are deliberately
  left ungrouped so each lands as its own reviewable PR instead of getting
  bundled with everything else (a grouped major-version PR previously
  bundled React 18→19, Tailwind 3→4, Vite 5→8, and more into one unmergeable
  PR — see [`docs/debugging.md`](docs/debugging.md) if you hit something
  similar).
- **Documentation** is expected to move in the same PR as the code it
  describes — see [`AGENTS.md`](AGENTS.md#14-documentation-maintenance).

## CLI Reference

| Command | Description |
|---------|-------------|
| `myace login --server <url> --token <key>` | Store API credentials |
| `myace logout` | Remove stored credentials |
| `myace status` | Show auth status |
| `myace pull --profile <name> --target <fw> [--path <dir>]` | Fetch and write compiled profile |
| `myace list-profiles` | List profiles from server |
| `myace import --path <dir> --name <name> [--push]` | Scan local config dir and convert to canonical artifacts |
| `myace serve [--port <port>]` | Run a local companion server so the web UI's Import page can scan this machine (needs `pip install "myace-cli[serve]"`) |

### Import command

The `import` command scans an existing local configuration directory (e.g.,
`~/.config/opencode`, `~/.claude`, `~/.cursor`) and converts everything to
Canonical IR:

```bash
# Scan and export to a local directory
myace import --path ~/.config/opencode --name "my-config" --output ./my-collection

# Scan and push to the MyACE server
myace login --server http://localhost:8000 --token <token>
myace import --path ~/.config/opencode --name "my-config" --push
```

**What it discovers:**

| Source | Artifact Type |
|--------|--------------|
| `skills/<name>/SKILL.md` | `skill` |
| `agents/<name>.md` | `agent` |
| `commands/<name>.md` | `workflow` |
| `AGENTS.md` (## sections) | `rule` |
| `opencode.json` (models + MCP) | `model_config` |

(The web UI's Import page additionally supports scanning a GitHub
repository directly — see [`docs/architecture.md`](docs/architecture.md).)

### Local companion server (`myace serve`)

The web UI's Import page can't read your filesystem directly — a browser
has no API to silently walk `~/.claude`, `~/.cursor`, etc. To scan your own
machine from the browser (rather than running `myace import` by hand), run:

```bash
# Binary users (serve is already included):
myace login --server <your-myace-server-url> --token <token-from-Settings>
myace serve

# pip users (need the serve extras):
# pip install "myace-cli[serve]"
# myace login --server <your-myace-server-url> --token <token-from-Settings>
# myace serve
```

The Import page auto-detects it (polling `http://127.0.0.1:8765/health`)
and switches to a live scan-and-select flow once it's running. It binds to
loopback only and only accepts requests from the exact origin you logged
into — see `cli/myace_cli/local_server.py` for the full security model.

## Canonical Intermediate Representation (IR)

All configurations are stored as Markdown files with structured YAML
frontmatter:

```yaml
---
type: rule | skill | agent | workflow | model_config
name: my-rule
version: 1.0.0
target_compatibility:
  - opencode
  - claude-code
  - cursor
priority: 50
tags:
  - python
  - type-safety
description: Enforces strict type annotations
---
# Rule Content

Markdown body with the actual rule/instruction content...
```

## Target Adapters

| Adapter | Target Frameworks | Output |
|---------|------------------|--------|
| Claude Code | `claude-code`, `claude` | `CLAUDE.md`, `.claude/agents/*.md`, `.claude/workflows/*.md` |
| OpenCode | `opencode`, `open-code` | `.opencode/skills/*/SKILL.md`, `.opencode/agents/*.md`, `.opencode/commands/*.md`, `AGENTS.md`, `opencode.json` |
| Cursor | `cursor`, `cursor-editor` | `.cursorrules`, `.cursor/rules/*.mdc`, `.cursor/workflows/*.mdc` |
| Codex CLI | `codex-cli`, `codex`, `openai-codex` | `AGENTS.md`, `.agents/skills/*/SKILL.md`, `.agents/agents/*.md`, `.codex/config.toml` |
| GitHub Copilot CLI | `copilot-cli`, `copilot`, `github-copilot` | `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md` |
| Cline | `cline`, `clinerules` | `.clinerules/*.md` |
| Windsurf | `windsurf`, `codeium-windsurf` | `.windsurf/rules/*.md` |
| Aider | `aider` | `CONVENTIONS.md`, `.aider.conf.yml` |
| Continue | `continue`, `continue-dev` | `.continue/rules/*.md`, `.continue/prompts/*.prompt`, `config.yaml` |
| Goose | `goose` | `.goosehints` |
| Sourcegraph Cody | `cody`, `sourcegraph-cody` | `.sourcegraph/*.rule.md` |
| Amazon Q Developer | `amazon-q`, `amazonq` | `.amazonq/rules/*.md` |

Roo Code was evaluated but deliberately not built: its extension was shut
down and its repo archived on 2026-05-15 (see
[ADAPTERS_RESEARCH.md](docs/ADAPTERS_RESEARCH.md)). Sourcegraph
Cody's current public docs don't list a dedicated rules capability matching
`.sourcegraph/*.rule.md`; that adapter uses a conservative best-effort
format pending confirmation (see `backend/app/adapters/cody.py`).

Only the first three are mirrored in the CLI's offline fallback adapters
(`cli/myace_cli/adapters/`) — the rest are backend/web-UI-only for now.

An admin can disable any adapter system-wide from System Settings →
Adapter Registry — disabled adapters disappear from the Compile page's
target picker and are rejected server-side if requested directly (e.g. via
`myace pull`).

## Authentication & Roles

Every API route requires an authenticated user — either a browser session
(set by `/auth/login` or an OIDC/GitHub/Google callback) or a Bearer API
token (what the CLI uses). Email + password is the always-available
baseline; OIDC/GitHub/Google are optional extra sign-in methods, registered
only if their client ID/secret env vars are set. A "Forgot password?" link
on the login page sends a one-hour, single-use reset link by email, once
SMTP is configured — see
[`docs/extending.md#configuring-smtp-for-password-reset`](docs/extending.md#configuring-smtp-for-password-reset).

Two roles: **user** (default — full access to their own collections/
profiles/tokens, read-only access to anything another user marked
`visibility: public` / `is_public: true`) and **admin** (bypasses ownership
entirely — can read/write everyone's data, for oversight). The first person
to ever register becomes admin automatically; `ADMIN_EMAILS`
(comma-separated) promotes specific emails on register/login going forward.
Admins can also disable, re-enable, or remove another user's account from
System Settings → Users (soft-delete, same as the self-service account
deletion in Settings — never a hard delete). See
[`docs/invariants.md#authorization`](docs/invariants.md#authorization) for
the exact rules.

## Compose Files

| File | Command | Use Case | Access |
|------|---------|----------|--------|
| `docker-compose.yml` | `docker compose up -d` | Single-machine prod | `http://localhost:80` |
| `+ docker-compose.dev.yml` | `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d` | Development | Frontend `:80`, API `:8000`, home dir mounted at `/host-home` |
| `+ docker-compose.prod.yml` | `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` | VPS behind proxy | No host ports; attach via `PROXY_NETWORK` env var |

## Backups

There is no automated backup mechanism yet — `postgres-data` is a plain
named Docker volume with no scheduled dump job, no offsite copy, and no
built-in restore procedure. If you're running MyACE anywhere that matters
(open registration, real user accounts, anything you'd be upset to lose),
back up the volume yourself in the meantime, e.g. a cron'd
`docker compose exec -T postgres pg_dump -U myace myace | gzip > backup.sql.gz`
copied off the host. See
[`docs/plans/postgres-backups-plan.md`](docs/plans/postgres-backups-plan.md)
for the planned automated setup (in-stack `pg_dump` sidecar + offsite copy +
tested restore procedure) — not yet implemented.

## Project Structure

```
├── AGENTS.md                    # AI agent maintenance guidelines
├── CLAUDE.md                    # Claude Code-specific agent guidance
├── CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md, LICENSE
├── docs/                        # Deep-dive documentation (humans + agents)
├── collections/                 # Starter-pack content (seeded on boot),
│   ├── base/                    #   hand-curated and code-reviewed here —
│   └── additional/              #   see "Starter packs" section in AGENTS.md
├── docker-compose.yml           # Single-machine production
├── docker-compose.dev.yml       # Dev overrides (ports, mounts, CORS)
├── docker-compose.prod.yml      # VPS overrides (external network, no ports)
├── .env.example
│
├── backend/                     # FastAPI + SQLModel
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/                 # Migrations
│   ├── app/
│   │   ├── main.py              # App entrypoint, CORS + session middleware
│   │   ├── core/                # Config, DB session, OIDC/security, crypto (encrypted admin secrets), deps (auth), authz (ownership checks)
│   │   ├── models/               # SQLModel schemas (User, Collection, Artifact, Profile, ApiToken, DocCache, SystemSettings)
│   │   ├── api/                  # Routes: auth, collections, profiles, adapters, doc_cache, admin
│   │   ├── adapters/             # Canonical IR → target translators (7: Claude Code, OpenCode, Cursor, Codex CLI, Copilot CLI, Cline, Windsurf)
│   │   └── services/             # Compiler, doc verifier, scanner (local + git), github_export, seed_collections,
│   │                              #   email (SMTP send), effective_settings (DB-override-vs-env resolver)
│   └── tests/                    # pytest suite
│
├── frontend/                    # React + Vite + TailwindCSS
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── src/
│   │   ├── components/           # Layout (responsive sidebar/drawer), shared UI
│   │   ├── contexts/              # AuthContext (current user/session), ThemeContext (light/dark/system)
│   │   ├── pages/                 # Login, ResetPassword, Dashboard, Collections, CollectionDetail,
│   │   │                          #   CommunityCollections, CommunityCollectionDetail, Profiles, ProfileDetail,
│   │   │                          #   Import, Compile, UserSettings, SystemSettings (admin-gated)
│   │   ├── lib/                   # API client
│   │   └── types/                 # TypeScript interfaces
│   └── dist/                     # Production build
│
├── cli/                          # Python Typer CLI
│   ├── pyproject.toml
│   └── myace_cli/
│       ├── main.py               # Entrypoint (7 commands)
│       ├── auth.py               # Credential storage
│       ├── sync.py               # Profile fetch + write
│       ├── scanner.py            # Local directory scanner
│       └── adapters/             # Client-side translation fallbacks
│
└── .github/                      # Issue/PR templates, CI workflow, Dependabot config
```

## Credits

MyACE is built on [FastAPI](https://fastapi.tiangolo.com/),
[SQLModel](https://sqlmodel.tiangolo.com/), [Alembic](https://alembic.sqlalchemy.org/),
[Authlib](https://authlib.org/), [React](https://react.dev/),
[Vite](https://vitejs.dev/), [TanStack Query](https://tanstack.com/query),
[Tailwind CSS](https://tailwindcss.com/), and [Typer](https://typer.tiangolo.com/).
Thanks to the maintainers of all of them.

Logo: <a href="https://www.flaticon.com/free-icons/layers" title="layers icons">Layers icons created by Good Ware - Flaticon</a>.

This entire project — every line of code, every test, every doc, every
infrastructure config — was written by AI coding agents:
[Claude Code / Sonnet 5](https://docs.anthropic.com/en/docs/claude-code/overview)
and [OpenCode / DeepSeek V4-Flash](https://github.com/niels-emmer/opencode).
The human (Niels) reviewed, directed, and shipped it.

## License

[MIT](LICENSE) © 2026 [Niels Emmer](https://github.com/niels-emmer)
