---
name: Azure Identity Design
description: Entra ID, managed identity, and workload identity federation design for Azure — when to use which, and how to avoid long-lived service-principal secrets.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [azure, iac, identity, security, entra-id]
---
## Purpose

Identity is the security boundary in Azure. This skill is the Azure-specific
companion to `iac-expert`'s "Managed Identity Over Long-Lived Secrets" rule:
it explains the identity options Azure offers, when to use each, and how to
design so that long-lived secrets are the exception, not the default.

## When to use it

Any time you're designing or reviewing how an Azure workload authenticates —
a new service, a service-to-service call, a CI/CD pipeline deploying to
Azure, or a human accessing the portal/CLI.

## The identity options, and when to use each

**Managed identity** — the default for any Azure-hosted workload (App
Service, Functions, VMs, AKS, Logic Apps, etc.). Azure automatically rotates
the backing credential; your code just requests a token. Use this for
service-to-service access between Azure resources. Prefer a **user-assigned**
managed identity when you need the identity to outlive a single resource or
be shared across several; **system-assigned** when the identity is tied to
exactly one resource.

**Workload identity federation** — for non-Azure or external workloads (a
GitHub Actions workflow, a Kubernetes cluster outside Azure, a third-party
SaaS) that need to act as an Azure identity. Configure a federated identity
credential on an app registration so the external workload's OIDC token is
trusted directly — no client secret exchanged. This is the modern replacement
for service principals with secrets in CI/CD.

**Service principal with a client secret** — the legacy option. Only
acceptable when the target genuinely has no managed-identity or federation
option. If you must use one: store the secret in Key Vault, reference it by
ID, scope its RBAC to least privilege, and rotate it on a short, documented
cadence. Treat any new client secret as a documented exception per
`iac-expert`'s `exception-documentation` skill.

**Human access** — Entra ID accounts with MFA and conditional access. No
shared accounts, no standing admin credentials in code or config. Use
Privileged Identity Management (PIM) for just-in-time elevation to
privileged roles rather than permanent standing access.

## Design rules

- **Default to managed identity.** If the workload runs in Azure, it gets a
  managed identity — no client secret, no connection string.
- **Federate external workloads.** CI/CD and external systems use workload
  identity federation, not a stored secret.
- **Scope RBAC to least privilege.** The identity gets only the roles the
  workload actually needs, at the narrowest scope (see the
  `azure-caf-landing-zones` skill).
- **Never embed secrets.** No client secret, connection string, or API key as
  a literal in `.tf`/`.bicep`/ARM, a tfvars/parameter file, or a module
  default. Reference Key Vault by ID.
- **Document the exception.** Any long-lived secret is a documented exception
  with a compensating control (rotation cadence, Key Vault storage, scoped
  permissions) and an expiry/review date.

## Expected output

An identity design (or a review of one) that states, for each workload: how it
authenticates (managed identity, federated credential, or documented
secret exception), what RBAC it holds and at what scope, and how human access
is gated (MFA, conditional access, PIM). No workload authenticates with an
undocumented long-lived secret.
