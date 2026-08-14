---
name: Observability Stack
description: Structured logging, RED/USE metrics, distributed tracing, and alerting thresholds for production services.
version: "1.0.0"
priority: 55
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [devops, observability, monitoring]
---
## Purpose

Ensure every service can be debugged without reproducing issues live.

## Checklist

- **Structured logging**: JSON output with timestamp, level, service name, request ID, and error context. No free-form text logs.
- **RED metrics** (services): Rate (requests/sec), Errors (failed requests/sec), Duration (latency p50/p95/p99).
- **USE metrics** (resources): Utilization (CPU/memory/disk %), Saturation (queue depth), Errors (device errors).
- **Distributed tracing**: trace context propagated across service boundaries; traces sampled for high-traffic services.
- **Alerting on symptoms**: page on user-facing impact (error rate spike, latency degradation), not infrastructure noise (CPU > 80%).
- **Dashboards**: one dashboard per service showing RED metrics, key dependencies, and recent deployments.

## Expected output

A service that emits structured logs, RED/USE metrics, and trace context from day one, with symptom-based alerting and a service dashboard.
