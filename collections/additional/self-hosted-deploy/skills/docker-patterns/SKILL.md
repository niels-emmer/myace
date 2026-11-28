---
name: Docker Patterns
description: Compose layering and runtime hardening for multi-service apps — dev/prod overrides, service dependencies, healthchecks, resource limits, and safe operation.
version: "1.0.0"
priority: 55
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [docker, compose, containers, hardening, deployment]
---
## Purpose

Get from "an image builds" to "a stack runs predictably in development and
production." This skill covers how containers are **composed, run, and
hardened** across environments. For how the image itself is constructed —
multi-stage builds, minimal base images, SBOMs, and vulnerability scanning — use
the `container-build` skill when the devops add-on is composed; this one
deliberately does not repeat it.

## When to use it

Any time you write or change a compose file, add a service, separate development
from production configuration, or harden a running stack.

## Compose layering

Keep a base file that describes the stack, then layer environment-specific
overrides instead of maintaining two divergent files.

```yaml
# docker-compose.yml — shared definition, no environment-specific choices
services:
  app:
    build: .
    environment:
      NODE_ENV: ${NODE_ENV:-development}
```

```yaml
# docker-compose.dev.yml — local development
services:
  app:
    volumes:
      - .:/app
    command: npm run dev
    environment:
      DEBUG: "true"
```

```yaml
# docker-compose.prod.yml — production overrides
services:
  app:
    restart: always
    read_only: true
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

Run a layered stack with `docker compose -f docker-compose.yml -f
docker-compose.prod.yml up -d`. Keep the base file free of anything only one
environment needs.

## Service dependencies

- Use `depends_on` with `condition: service_healthy` for ordered startup.
- Give every long-running service a healthcheck.
- Put services that must talk to each other on a dedicated network; expose only
  what the reverse proxy needs.

```yaml
services:
  api:
    build: ./api
    depends_on:
      db:
        condition: service_healthy
    networks: [app-net]

  db:
    image: postgres:16-alpine
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks: [app-net]

networks:
  app-net:
    driver: bridge
```

## Runtime hardening

- **No secrets in images or compose files** — inject them at run time from a
  secret store or a gitignored environment file.
- **Read-only root filesystem** where the app allows it, with explicit writable
  mounts only for state.
- **Resource limits** — set memory and CPU limits so one service cannot starve
  the host.
- **Drop capabilities** — start from `cap_drop: [ALL]` and add back only what is
  required.
- **No privileged containers** and no host-network mode unless there is a documented reason.
- **Pin image tags** by digest or exact version; do not rely on a floating tag.

## Healthchecks and logging

- A healthcheck should test real readiness, not just that the process started.
- Use a bounded log driver (size and file count) so logs cannot fill the disk.
- Send logs to stdout/stderr; let the platform collect them.

## Safe operation

- Confirm which compose files and environment you are targeting before running a
  destructive command.
- Take a backup or snapshot before recreating a stateful service.
- Prefer `up -d` with a changed image over pruning volumes; never prune volumes
  on a host that holds real data.
- Treat any stack whose name carries `prod` or runs behind a shared proxy as
  live production: pause and confirm before restarting or rebuilding it.

## Output format

```
## Docker summary
- Compose files: <count and layering>
- Services: <list>
- Healthchecks: yes / no
- Resource limits: yes / no
- Read-only root / dropped capabilities: yes / no
- Secrets injected at run time: yes / no
```
