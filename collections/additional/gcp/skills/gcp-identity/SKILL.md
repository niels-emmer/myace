---
name: GCP Identity Design
description: IAM roles, service accounts, and identity federation design for GCP — when to use which, and how to avoid long-lived service-account keys.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [gcp, iac, identity, security, iam]
---
## Purpose

Identity is the security boundary in GCP. This skill is the GCP-specific
companion to `iac-expert`'s "Managed Identity Over Long-Lived Secrets" rule:
it explains the identity options GCP offers, when to use each, and how to
design so that long-lived service-account keys are the exception, not the
default.

## When to use it

Any time you're designing or reviewing how a GCP workload authenticates — a
new service, a service-to-service call, a CI/CD pipeline deploying to GCP, or
a human accessing the console/CLI.

## The identity options, and when to use each

**Service accounts** — the default for any GCP-hosted workload (Compute
Engine, GKE, Cloud Run, Cloud Functions, etc.). Attach a service account to
the resource and GCP handles the backing credentials automatically; your code
just requests temporary credentials via the instance metadata/Workload
Identity endpoint. Use this for service-to-service access between GCP
resources. Prefer a service account with a narrowly-scoped IAM role over a
shared account with broad permissions.

**Workload Identity Federation** — for non-GCP or external workloads (a GitHub
Actions workflow, a Kubernetes cluster outside GCP, a third-party SaaS) that
need to act as a GCP identity. Configure a Workload Identity Pool and Provider
so the external workload's OIDC token (e.g. GitHub Actions OIDC) is trusted
directly — no service-account key exchanged. This is the modern replacement
for long-lived service-account keys in CI/CD.

**Long-lived service-account keys** — the legacy option. Only acceptable when
the target genuinely has no service-account or federation option. If you must
use one: store the key in Secret Manager, reference it by ID, scope its IAM
role to least privilege, and rotate it on a short, documented cadence. Treat
any new service-account key as a documented exception per `iac-expert`'s
`exception-documentation` skill.

**Human access** — IAM users/groups with MFA, or (better) identity federation
to a corporate IdP (Google Workspace / Cloud Identity SSO). No shared
accounts, no standing service-account keys in code or config. Use
just-in-time access to roles rather than permanent standing credentials.

## Design rules

- **Default to service accounts.** If the workload runs in GCP, it gets a
  service account — no key, no embedded secret.
- **Federate external workloads.** CI/CD and external systems use Workload
  Identity Federation, not a stored service-account key.
- **Scope IAM to least privilege.** The service account gets only the
  permissions/resources the workload actually needs (see the
  `gcp-landing-zones` skill).
- **Never embed secrets.** No service-account key, secret, or API key as a
  literal in `.tf`, a tfvars file, or a module default. Reference Secret
  Manager by ID.
- **Document the exception.** Any long-lived secret is a documented exception
  with a compensating control (rotation cadence, Secret Manager storage,
  scoped permissions) and an expiry/review date.

## Expected output

An identity design (or a review of one) that states, for each workload: how it
authenticates (service account, federated credential, or documented secret
exception), what IAM role it holds and at what scope, and how human access is
gated (MFA, SSO). No workload authenticates with an undocumented long-lived
service-account key.
