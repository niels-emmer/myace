---
name: Scaleway Service Patterns
description: Service-selection and configuration patterns for common Scaleway workloads covering compute, data, networking and residency. Use when choosing or configuring Scaleway products in IaC.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [scaleway, architecture, services]
---
## Purpose

Give Scaleway-specific defaults and trade-offs, including where the platform offers fewer managed controls than the larger clouds.

## When to use it

When selecting compute, data stores or a network path for a new workload, or reviewing IaC that provisions them. Verify current service limits, SKUs and defaults against the provider's documentation before relying on them. Scaleway's catalogue and regional availability change, so check the product pages first.

## Checklist

- **Compute**: Serverless Containers or Functions for stateless and event-driven work, Instances for general VMs, Kubernetes Kapsule when Kubernetes is a requirement, Elastic Metal when you need dedicated hardware; say which and why.
- **Network**: attach resources to a VPC Private Network and use a Public Gateway for controlled egress; expose only a Load Balancer or the gateway to the internet. Treat security groups as default-deny and review any rule open to the world.
- **Data**: Managed Databases for PostgreSQL, MySQL or Redis with private access and backups enabled; check their high-availability option matches the availability target.
- **Object storage**: S3-compatible buckets with private ACLs by default and explicit bucket policies; check the lifecycle and versioning features you rely on are supported before assuming AWS behaviour.
- **Secrets**: Secret Manager, with API keys stored per application and rotated.
- **Observability**: Cockpit for metrics and logs, Audit Trail for control-plane events; set alert contacts.
- **Residency**: choose the region deliberately (for example Paris, Amsterdam or Warsaw) when data residency or EU-only operation matters, and keep backups and replicas inside the same boundary.
- **Portability**: prefer open interfaces (S3 API, PostgreSQL, Kubernetes) so a workload can move; avoid assuming a feature exists because another cloud has it.
- **Cost levers**: right-size, use per-project cost views, and delete unattached volumes, IPs and idle load balancers.

## Expected output

A design note naming the chosen products with reasons, the Private Network layout, residency decision and the points where Scaleway offers fewer managed controls than assumed.
