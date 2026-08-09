# Contributing to MyACE

Thanks for considering a contribution. MyACE is a small, opinionated project —
please read this before opening a PR so your change lands smoothly.

## Before you start

- **Bug fix or small change?** Just open a PR.
- **New feature or anything that touches the data model, auth, or the
  canonical IR schema?** Open an issue first to discuss the approach. This
  project has a deliberately narrow scope (see
  [`docs/architecture.md`](docs/architecture.md)); we'd rather steer before
  you write code than ask for a rewrite after.
- **Found a security issue?** Do not open a public issue — see
  [`SECURITY.md`](SECURITY.md).

## Development setup

```bash
git clone https://github.com/niels-emmer/myace.git
cd myace
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
docker compose exec backend alembic upgrade head
```

Web UI at `http://localhost`, API docs at `http://localhost:8000/docs`. See
the [README Quick Start](README.md#quick-start) for the full walkthrough,
including frontend hot-reload and CLI setup.

## Running checks locally

```bash
# Backend
cd backend
pip install -e ".[dev]"
pytest                 # tests
ruff check .            # lint
mypy app                # type check

# Frontend
cd frontend
npm install
npm run test            # vitest
npx tsc -b               # type check
npm run build            # production build

# CLI
cd cli
pip install -e ".[dev]"
pytest
```

CI runs all of the above on every PR — see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Conventions

The full, authoritative list of repository conventions — typing rules,
migration rules, adapter structure, auth/authorization patterns, and known
gotchas — lives in [`AGENTS.md`](AGENTS.md). Read it before making
non-trivial changes; it's kept up to date on purpose and is shorter than it
looks.

In short:

- **Type everything.** Full annotations on the backend (SQLModel + Pydantic
  v2), full annotations on the frontend (TypeScript).
- **Every schema change gets an Alembic migration** with a working
  `downgrade()`. Never edit a committed migration.
- **Branch names**: `feat/description`, `fix/description`,
  `chore/description`.
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`).
- **Keep documentation in sync.** If your change alters behavior described in
  `README.md`, `AGENTS.md`/`CLAUDE.md`, or anything under `docs/`, update it
  in the same PR. See [`docs/README.md`](docs/README.md) for what lives
  where.

## Pull requests

1. Fork the repo and create a branch off `main`.
2. Make your change, with tests for new behavior.
3. Run the checks above locally.
4. Open a PR against `main` — the template will ask what changed and how you
   tested it.
5. CI must pass. At least one maintainer review is required before merge.

## Project structure

See the [README's project structure section](README.md#project-structure)
for a map of the codebase, and [`docs/architecture.md`](docs/architecture.md)
for how the pieces fit together conceptually.

## License

By contributing, you agree that your contributions will be licensed under
the [MIT License](LICENSE) that covers this project.
