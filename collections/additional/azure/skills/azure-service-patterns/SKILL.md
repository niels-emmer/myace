---
name: Azure Service Patterns
description: Service-selection and configuration patterns for common Azure workloads covering compute, data, networking and identity defaults. Use when choosing or configuring Azure services in IaC.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [azure, architecture, services]
---
## Purpose

Give Azure-specific defaults and trade-offs that the generic IaC and landing-zone skills cannot.

## When to use it

When selecting compute, data stores or a network path for a new workload, or reviewing IaC that provisions them. Verify current service limits, SKUs and defaults against the provider's documentation before relying on them.

## Checklist

- **Compute**: Container Apps for containerised services and event-driven scale, App Service for web apps and APIs, Functions for event-driven code, AKS when Kubernetes is a requirement, VMs when you need instance control; say which and why.
- **Identity**: give each workload a managed identity (user-assigned when several resources share one) and grant it data-plane roles on the specific resource; avoid connection strings, storage keys and service-principal secrets.
- **Private connectivity**: Private Endpoints for PaaS services plus the matching Private DNS zones linked to the VNet, with public network access disabled on the resource; a Private Endpoint without correct DNS silently fails or falls back to the public path.
- **Key Vault**: use Azure RBAC authorization rather than legacy access policies, soft delete and purge protection on, and reference secrets from App Service, Container Apps or Functions instead of copying them into settings.
- **Storage**: disable shared-key access where clients can use Entra ID, deny public blob access, require TLS 1.2 or later, and use lifecycle management.
- **Databases**: Azure SQL, PostgreSQL or Cosmos DB with Entra authentication where supported, private access, backups and geo-redundancy matched to the recovery target.
- **Edge**: Front Door with WAF for global internet-facing apps, Application Gateway with WAF for regional ones.
- **Observability**: diagnostic settings to a central Log Analytics workspace enforced by policy, Application Insights for apps, alerts with an action group and owner.
- **Cost levers**: right-size SKUs, use reservations or savings plans only for stable baselines, remove orphaned disks and public IPs, and use budgets with alerts.

## Expected output

A design note naming the chosen services with reasons, the managed-identity and private-endpoint design, Key Vault usage and the cost drivers.
