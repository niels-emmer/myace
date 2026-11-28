---
name: Kubernetes Workload Checklist
description: Checklist for a production-ready Deployment, StatefulSet or Job covering resources, probes, availability and shutdown. Use when writing or reviewing workload manifests.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [kubernetes, workloads, reliability]
---
## Purpose

Make a workload schedulable, observable and safe to restart and upgrade.

## When to use it

When creating or reviewing a Deployment, StatefulSet, DaemonSet, Job or CronJob.

## Checklist

- **Resources**: CPU and memory requests set from measurement; a memory limit; CPU limits only where throttling is understood.
- **Probes**: readiness gates traffic, liveness restarts only a stuck process, startup covers slow boots; none depend on a downstream the pod does not own.
- **Availability**: at least two replicas for anything user-facing, a PodDisruptionBudget, and topology spread across zones or nodes.
- **Shutdown**: handle SIGTERM, finish in-flight work inside `terminationGracePeriodSeconds`, and use a short `preStop` only if the load balancer needs time to drain.
- **Jobs**: set `backoffLimit`, `activeDeadlineSeconds` and a CronJob `concurrencyPolicy`; make the work idempotent.
- **Config**: ConfigMaps for non-secret config, versioned or hashed so a change rolls the pods.
- **Labels**: the recommended `app.kubernetes.io/*` labels plus owner and environment, consistently on every object.
- **Sidecars**: use native sidecar containers where the cluster version supports them rather than ordering hacks.

## Expected output

A workload manifest that survives node drains, rolling updates and restarts without dropping traffic.
