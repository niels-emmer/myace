---
name: Telemetry Conventions
description: Conventions for logs, metrics and traces including naming, attributes, cardinality and correlation. Use when instrumenting a service or reviewing telemetry.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [observability, opentelemetry, telemetry]
---
## Purpose

Make telemetry consistent so it can be queried, correlated and afforded.

## When to use it

When adding instrumentation, introducing a new service, or investigating noisy, expensive or unusable telemetry.

## Checklist

- **Logs**: structured (JSON), one event per line, level used consistently, a trace and request id on every line, no secrets or personal data.
- **Metrics**: names and units follow the convention in use; counters for events, histograms for latency, gauges for state; labels drawn from small bounded sets.
- **Traces**: one span per meaningful operation, `server`/`client` kinds set correctly, errors recorded as span status and exception events, context propagated through HTTP, messaging and background jobs.
- **Semantic conventions**: use OpenTelemetry attribute names (for example HTTP, database and messaging attributes) instead of inventing names; check the version the project pins since names have changed.
- **Sampling**: sample traces deliberately (for example tail-based for errors and slow requests) and say what is dropped.
- **Cost**: estimate volume and cardinality; budget them like any other resource.
- **Correlation**: logs, metrics exemplars and traces share ids so one can lead to the other.

## Expected output

Telemetry that a person unfamiliar with the service can use to answer what happened, where, and for whom, without exposing sensitive data.
