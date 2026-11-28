---
name: Kubernetes Security Hardening
description: Pod security, RBAC, NetworkPolicy and secrets hardening checklist. Use when onboarding a namespace, reviewing RBAC or tightening a workload.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [kubernetes, security, rbac]
---
## Purpose

Reduce the blast radius of a compromised pod and of a misused credential.

## When to use it

When creating a namespace, granting access, handling secrets, or reviewing a workload that needs extra privileges.

## Checklist

- **Pod Security Admission**: label each namespace with an enforce level (target `restricted`) and a warn/audit level one step stricter while migrating. PodSecurityPolicy was removed in Kubernetes 1.25; do not reintroduce it.
- **Policy as code**: use ValidatingAdmissionPolicy or an admission controller to enforce rules the built-in levels do not (trusted registries, required labels, no `latest`).
- **RBAC**: namespaced Roles over ClusterRoles; bind to groups from the identity provider; no wildcards; audit `cluster-admin` bindings regularly; remember that `create` on pods or `get` on secrets is high privilege.
- **Service accounts**: one per workload, `automountServiceAccountToken: false` unless the pod calls the API, short-lived projected tokens.
- **NetworkPolicy**: default-deny ingress and egress per namespace, then allow DNS and the specific flows; verify the CNI enforces it.
- **Secrets**: external secret store or encrypted-at-rest with a KMS provider; restrict who can read them; rotate on exposure.
- **Images**: pinned by digest, signed or scanned, from a registry you control; no pulling arbitrary images into production namespaces.
- **Nodes and control plane**: keep within supported versions, restrict API-server access and enable audit logging.

## Expected output

A namespace and workload set whose privileges are explicit, enforced by admission, and documented where an exception exists.
