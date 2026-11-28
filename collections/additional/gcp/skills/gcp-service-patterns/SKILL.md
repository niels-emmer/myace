---
name: GCP Service Patterns
description: Service-selection and configuration patterns for common Google Cloud workloads covering compute, data, networking and identity defaults. Use when choosing or configuring GCP services in IaC.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [gcp, architecture, services]
---
## Purpose

Give Google Cloud-specific defaults and trade-offs that the generic IaC and landing-zone skills cannot.

## When to use it

When selecting compute, data stores or a network path for a new workload, or reviewing IaC that provisions them. Verify current service limits, SKUs and defaults against the provider's documentation before relying on them.

## Checklist

- **Compute**: Cloud Run for stateless containers, Cloud Run functions for event-driven code, GKE (Autopilot or Standard) when Kubernetes is a requirement, Compute Engine when you need instance control; say which and why.
- **Identity**: a dedicated service account per workload with the minimum predefined roles, attached to the resource; do not rely on the default compute service account, and avoid exporting keys (use Workload Identity Federation for external callers).
- **Default grants**: new projects can give default service accounts broad roles; turn that off with the organisation policy for automatic IAM grants on default service accounts and review existing ones.
- **Network**: custom-mode VPC rather than the default network, private Google access, Cloud NAT for egress, Private Service Connect for Google and partner services, and Cloud Run ingress and VPC egress settings set deliberately (internal and load-balancer-only ingress by default for internal services).
- **Storage**: Cloud Storage with uniform bucket-level access, public access prevention, CMEK where required, retention and lifecycle rules.
- **Databases**: Cloud SQL or AlloyDB with private IP, automated backups, point-in-time recovery and deletion protection; BigQuery datasets with explicit IAM, authorised views, and expiration for scratch data.
- **Messaging**: Pub/Sub with dead-letter topics, retry policy and per-subscription IAM.
- **Secrets**: Secret Manager with versions referenced by Cloud Run, GKE or Functions rather than copied into environment variables in code.
- **Observability**: log sinks to a central project, Data Access audit logs on for sensitive services, alerting policies with an owner.
- **Cost levers**: labels for billing export, budgets and alerts, right-sizing recommendations, committed-use discounts only for stable baselines, and scale-to-zero where the platform supports it.

## Expected output

A design note naming the chosen services with reasons, the service-account and network design, and the cost drivers.
