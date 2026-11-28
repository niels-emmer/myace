---
name: Node Service Conventions
description: Conventions for Node.js services, workers and CLIs covering configuration, shutdown, logging and outbound calls. Use when building or reviewing a Node service.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [node, service, reliability]
---
## Purpose

Make a Node process predictable to run, observe and stop.

## When to use it

When creating a service or worker, adding an outbound call, or reviewing startup, shutdown and error handling.

## Checklist

- **Config**: read and validate environment variables once at startup into a typed object; fail fast with a clear message on a missing or invalid value.
- **Shutdown**: handle SIGTERM, stop accepting work, drain in-flight requests with a deadline, close pools, then exit.
- **Errors**: one place turns errors into responses; do not leak stack traces or internal messages to clients; log with context and a correlation id.
- **Outbound calls**: timeouts on every call, retries only for idempotent operations with backoff and a cap.
- **Logging**: structured logs, no secrets or personal data, levels used consistently.
- **Process**: do not catch `uncaughtException` to keep running; log and exit so the supervisor restarts a clean process.
- **Blocking work**: keep CPU-heavy work off the event loop (worker threads or a separate process).

## Expected output

A service that starts only when correctly configured, stops cleanly, and reports failures with enough context to debug.
