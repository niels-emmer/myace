---
name: SLO And Alerting Design
description: Method for choosing SLIs and SLOs and turning them into burn-rate alerts. Use when defining reliability targets or fixing noisy paging.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [observability, slo, alerting]
---
## Purpose

Tie paging to user-visible reliability and keep pages rare and actionable.

## When to use it

When defining targets for a service, replacing threshold alerts, or triaging alert fatigue.

## Checklist

- **SLI**: a ratio of good events to valid events measured close to the user, such as successful requests or requests under a latency threshold.
- **SLO**: a target over a rolling window (often 28 or 30 days) agreed with the product owner; start looser than you hope and tighten from data.
- **Error budget**: 1 minus the SLO; use it to decide when to slow feature work in favour of reliability.
- **Alerts**: multi-window, multi-burn-rate alerts (a fast burn pages, a slow burn opens a ticket) rather than raw error-rate thresholds.
- **Dependencies**: do not page for a dependency's failure unless users feel it; track it on a dashboard.
- **Each page** names an owner, links a runbook, and states the first three checks.
- **Review monthly**: count pages, false pages and budget spent; delete or retune alerts that do not lead to action.

## Expected output

A short list of SLOs per service with budget tracking and a small set of actionable, owned alerts.
