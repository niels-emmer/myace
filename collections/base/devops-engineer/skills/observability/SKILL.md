---
name: Observability
description: Structured logging, RED/USE metrics, tracing, and alerting on symptoms — so production behavior is visible and pages go to the right people for the right reasons.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [observability, monitoring, logging, alerting]
---
## Purpose

You can't operate what you can't see. Observability is the difference between "the service is down" and "the service is down because the database connection pool is exhausted, and here's the query that did it." This skill is the checklist for making production behavior visible from day one.

## When to use it

When adding a new service, changing how a service is instrumented, designing dashboards or alerts, or debugging an incident where the existing telemetry wasn't enough to answer "what changed?"

## Steps / checklist

1. **Structured logs.** Logs are structured (JSON), not free text. Include request id, service, environment, and enough context to correlate with traces. Never log secrets, tokens, or PII.
2. **RED metrics for services.** Rate (requests/sec), Errors (failed requests/sec), Duration (latency percentiles). These three answer "is the service healthy" at a glance.
3. **USE metrics for resources.** Utilization, Saturation, Errors — for CPUs, memory, disk, connections. These answer "is the resource the bottleneck."
4. **Tracing.** Distributed traces across service boundaries so a slow request can be followed end-to-end. Every external call (DB, queue, API) is a span.
5. **Alert on symptoms, not causes.** Page on user-facing impact (error rate, latency SLO breach), not on infrastructure noise (CPU at 80%). An alert that doesn't require action is noise; noise trains people to ignore alerts.
6. **Dashboards answer questions.** A dashboard is a story about a system, not a wall of graphs. Each panel should answer a question someone actually asks during an incident.
7. **SLOs where it matters.** Define SLOs for user-facing services and alert on error budget burn, not on individual failures.

## Expected output

A service where a new on-call engineer can answer "is it healthy, and if not, where do I look?" from the dashboards and logs alone — without asking the person who built it. If an incident requires guessing, the observability work isn't done.