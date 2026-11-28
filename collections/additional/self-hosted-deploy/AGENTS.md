# Self-Hosted Deployment

## One Container, One Database By Default

<!-- myace: priority=50 tags=deploy,process -->

Start with a single application container and a single on-disk database file. Treat anything heavier — multiple services, a managed database, a queue — as a deliberate decision you can justify, not the default.

## Back Up Before You Change State

<!-- myace: priority=90 tags=deploy,safety -->

Take a consistent snapshot before recreating a stateful service or changing its volume. Restoring must be a tested, reversible procedure, and a backup is never exposed without authentication.

## Health Checks Gate Every Deploy

<!-- myace: priority=70 tags=deploy,release -->

Every long-running service exposes a real readiness check, and a deploy is verified by calling it — not by assuming the container started. A failed health check means roll back, not retry blindly.
