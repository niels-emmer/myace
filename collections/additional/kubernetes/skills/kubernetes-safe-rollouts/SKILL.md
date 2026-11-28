---
name: Kubernetes Safe Rollouts
description: Procedure for diffing, applying, watching and rolling back Kubernetes changes, plus ingress and API-deprecation checks. Use before any change to a live cluster.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [kubernetes, release, rollback]
---
## Purpose

Make every change to a live cluster observable and reversible.

## When to use it

Before applying manifests or upgrading a Helm release to any shared cluster, and when planning a cluster or API-version upgrade.

## Checklist

- **Confirm target**: print the current context and namespace and have a human confirm them for any shared cluster.
- **Render and diff**: `helm template`/`kustomize build`, then `kubectl diff` or `helm diff` against the live state; read the diff.
- **Dry run**: `--dry-run=server` to catch admission and schema rejections.
- **Apply small**: one logical change at a time, roll out to a non-production environment first.
- **Watch**: `kubectl rollout status`, then check error rate and latency; stop and roll back on regression.
- **Rollback**: know it before applying (`kubectl rollout undo`, `helm rollback`, or revert the commit); stateful, CRD and storage changes may not roll back, so plan those separately.
- **API deprecations**: scan manifests for removed API versions before a cluster upgrade, and upgrade one minor version at a time.
- **Ingress**: the ingress-nginx controller was retired by the Kubernetes project in March 2026 with no further security fixes (kubernetes.io blog, Nov 2025 and Jan 2026). For new work prefer Gateway API (`HTTPRoute`); plan a migration for existing installs, since most controller-specific annotations do not carry over.

## Expected output

A change record with the target confirmed, the diff reviewed, the rollout watched and a rollback path stated.
