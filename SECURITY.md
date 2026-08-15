# Security Policy

## Supported Versions

MyACE does not yet cut versioned releases — `main` is the only supported
branch. Security fixes land there and you should track it directly.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Instead, use one of:

1. **GitHub Private Vulnerability Reporting** (preferred): open the
   [Security tab](../../security/advisories/new) on this repository and
   submit a private advisory. This notifies the maintainer directly without
   disclosing details publicly.
2. Contact [@niels-emmer](https://github.com/niels-emmer) directly via the
   contact details on their GitHub profile.

Please include:

- A description of the vulnerability and its potential impact
- Steps to reproduce (a minimal repro is very helpful)
- The affected component (backend API, frontend, CLI, Docker/deployment
  config)

You should expect an initial response within a few days. This is a
single-maintainer open source project run on a best-effort basis — there's
no SLA, but security reports are prioritized over everything else.

## Scope

In scope:

- The FastAPI backend (`backend/`), including authentication/authorization
  logic
- The React frontend (`frontend/`)
- The CLI (`cli/`)
- The provided Docker/Compose deployment configuration

Out of scope:

- Vulnerabilities in third-party dependencies — please report those upstream
  (though we'd still appreciate a heads-up so we can update)
- Issues that require an attacker to already have admin access to a MyACE
  deployment
- Missing security best-practices in a self-hosted deployment that deviates
  from the documented setup (e.g. running with the default `APP_SECRET_KEY`
  in production — the app refuses to start over this, see below)

## Security Model (summary)

MyACE has real authentication and authorization — every API route requires
an authenticated user (session cookie or Bearer API token), and access to
collections/profiles/artifacts is scoped by ownership plus an explicit
public/private flag, with an admin role that bypasses ownership for
oversight. See [`docs/invariants.md`](docs/invariants.md) for the exact
rules the code is expected to enforce, and
[`docs/architecture.md#authentication--authorization`](docs/architecture.md)
for how it's implemented.

A few things worth knowing if you're self-hosting:

- **`APP_SECRET_KEY` signs session cookies.** Set a real random value before
  exposing a deployment beyond localhost — the default placeholder is
  intentionally obvious and the app refuses to start (`RuntimeError`) if
  it's still in use outside development.
- **GitHub tokens used for the collection-export-to-GitHub API endpoint
  (`POST /collections/{id}/export/github`) are per-request only.** They
  are never persisted to the database or logged. The endpoint has no
  frontend UI — it's reachable by direct API use only.
- **API tokens are bcrypt-hashed at rest** and shown to the user exactly
  once, at creation time.

## Disclosure Policy

Once a reported vulnerability is confirmed and fixed, we'll publish a GitHub
Security Advisory crediting the reporter (unless they prefer to remain
anonymous) and describing the issue and fix.
