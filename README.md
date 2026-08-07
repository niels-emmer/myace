# MyACE — My Agentic Coding Environment

**MyACE** makes agentic coding environments portable by versioning, sharing, combining, and provisioning configurations (rules, skills, agent definitions, workflows, model configs) across frameworks (OpenCode, Claude Code, Cursor, etc.).

## Architecture

```
┌──────────────┐      ┌───────────────────┐
│   Browser    │─────▶│  Frontend (nginx) │
│  localhost   │      │  :80              │
└──────────────┘      └────────┬──────────┘
                               │ /api/* proxy
┌──────────────┐      ┌───────▼──────────┐
│  CLI (myace) │─────▶│  Backend (FastAPI)│
│              │      │  :8000            │
└──────────────┘      └───────┬──────────┘
                              │
                      ┌───────▼──────────┐
                      │  PostgreSQL      │
                      │  :5432           │
                      └──────────────────┘
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for CLI)
- Node.js 20+ (for frontend dev)

### Development Setup

```bash
# 1. Configure environment
cp .env.example .env

# 2. Start the dev stack (hot reload, direct ports, home dir mounted for import)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# 3. Run database migrations
docker compose exec backend alembic upgrade head

# 4. Access
#    Web UI:      http://localhost:80
#    API (direct): http://localhost:8000
#    API Docs:     http://localhost:8000/docs

# For Vite HMR during frontend development:
cd frontend && npm run dev   # starts on :5173, proxies /api to :8000
```

### Production (Single Machine)

```bash
docker compose up -d --build
# Access at http://localhost:80
```

### Production (VPS behind existing reverse proxy)

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

### CLI Setup

```bash
cd cli
pip install -e .
myace --help
```

## Compose Files

| File | Command | Use Case | Access |
|------|---------|----------|--------|
| `docker-compose.yml` | `docker compose up -d` | Single-machine prod | `http://localhost:80` |
| `+ docker-compose.dev.yml` | `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d` | Development | Frontend `:80`, API `:8000`, home dir mounted at `/host-home` |
| `+ docker-compose.prod.yml` | `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` | VPS behind proxy | No host ports; attach via `PROXY_NETWORK` env var |

## CLI Reference

| Command | Description |
|---------|-------------|
| `myace login --server <url> --token <key>` | Store API credentials |
| `myace logout` | Remove stored credentials |
| `myace status` | Show auth status |
| `myace pull --profile <name> --target <fw> [--path <dir>]` | Fetch and write compiled profile |
| `myace list-profiles` | List profiles from server |
| `myace import --path <dir> --name <name> [--push]` | Scan local config dir and convert to canonical artifacts |

### Import Command

The `import` command scans an existing local configuration directory (e.g., `~/.config/opencode`, `~/.claude`, `~/.cursor`) and converts everything to Canonical IR:

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

## Project Structure

```
├── AGENTS.md                    # AI agent maintenance guidelines
├── README.md
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
│   │   ├── main.py              # App entrypoint
│   │   ├── core/                # Config, DB session, OIDC/security
│   │   ├── models/              # SQLModel schemas (User, Collection, Artifact, Profile, ApiToken, DocCache)
│   │   ├── api/                 # Routes: auth, collections, profiles, adapters, doc_cache
│   │   ├── adapters/            # Canonical IR → target translators (Claude, OpenCode, Cursor)
│   │   └── services/            # Compiler, doc verifier, scanner
│   └── tests/                   # 24 tests
│
├── frontend/                    # React + Vite + TailwindCSS
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── src/
│   │   ├── components/          # Layout, shared UI
│   │   ├── pages/               # Dashboard, Collections, Profiles, Import, Export, Settings
│   │   ├── lib/                 # API client
│   │   └── types/               # TypeScript interfaces
│   └── dist/                    # Production build
│
└── cli/                         # Python Typer CLI
    ├── pyproject.toml
    └── myace_cli/
        ├── main.py              # Entrypoint (6 commands)
        ├── auth.py              # Credential storage
        ├── sync.py              # Profile fetch + write
        ├── scanner.py           # Local directory scanner
        └── adapters/            # Client-side translation fallbacks
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/auth/login/{provider}` | OIDC/OAuth2 login |
| `GET` | `/api/v1/auth/callback/{provider}` | OAuth callback |
| `POST` | `/api/v1/auth/tokens` | Create API token |
| `GET` | `/api/v1/auth/tokens` | List tokens |
| `DELETE` | `/api/v1/auth/tokens/{id}` | Revoke token |
| `POST` | `/api/v1/collections` | Create collection |
| `GET` | `/api/v1/collections` | List collections |
| `GET` | `/api/v1/collections/{id}` | Get collection |
| `GET` | `/api/v1/collections/{id}/artifacts` | List artifacts |
| `DELETE` | `/api/v1/collections/{id}` | Delete collection |
| `POST` | `/api/v1/collections/scan` | Scan local directory for artifacts |
| `POST` | `/api/v1/collections/import` | Bulk-import artifacts into a collection |
| `POST` | `/api/v1/profiles` | Create profile |
| `GET` | `/api/v1/profiles` | List profiles |
| `GET` | `/api/v1/profiles/{id}` | Get profile |
| `PUT` | `/api/v1/profiles/{id}` | Update profile |
| `DELETE` | `/api/v1/profiles/{id}` | Delete profile |
| `POST` | `/api/v1/profiles/compile` | Compile profile into target files |
| `GET` | `/api/v1/adapters` | List available adapters |
| `GET` | `/api/v1/adapters/{name}` | Get adapter info |
| `GET` | `/api/v1/doc-cache` | List cached docs |
| `DELETE` | `/api/v1/doc-cache/{id}` | Delete cache entry |

## Canonical Intermediate Representation (IR)

All configurations are stored as Markdown files with structured YAML frontmatter:

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
| OpenCode | `opencode`, `open-code` | `.opencode/skills/*.json`, `.opencode/agents/*.json`, `AGENTS.md` |
| Cursor | `cursor`, `cursor-editor` | `.cursorrules`, `.cursor/rules/*.mdc`, `.cursor/workflows/*.mdc` |

## License

MIT
