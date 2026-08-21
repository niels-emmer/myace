---
name: AWS Identity Design
description: IAM roles, policies, and identity federation design for AWS — when to use which, and how to avoid long-lived access keys.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [aws, iac, identity, security, iam]
---
## Purpose

Identity is the security boundary in AWS. This skill is the AWS-specific
companion to `iac-expert`'s "Managed Identity Over Long-Lived Secrets" rule:
it explains the identity options AWS offers, when to use each, and how to
design so that long-lived access keys are the exception, not the default.

## When to use it

Any time you're designing or reviewing how an AWS workload authenticates — a
new service, a service-to-service call, a CI/CD pipeline deploying to AWS, or
a human accessing the console/CLI.

## The identity options, and when to use each

**IAM roles** — the default for any AWS-hosted workload (EC2, ECS/EKS, Lambda,
etc.). Attach an instance/task/execution role and AWS rotates the backing
credentials automatically; your code just requests temporary credentials via
the instance metadata/credentials endpoint. Use this for service-to-service
access between AWS resources. Prefer a role with a narrowly-scoped trust
policy over a shared role with broad permissions.

**Identity federation** — for non-AWS or external workloads (a GitHub Actions
workflow, a Kubernetes cluster outside AWS, a third-party SaaS) that need to
act as an AWS identity. Use **OIDC federation** (e.g. GitHub Actions OIDC) so
the external workload's OIDC token is trusted directly — no access key
exchanged. Use **IAM Roles Anywhere** for workloads outside AWS that can't do
OIDC but still need temporary credentials. This is the modern replacement for
long-lived access keys in CI/CD.

**Long-lived access keys** — the legacy option. Only acceptable when the target
genuinely has no role or federation option. If you must use one: store the
secret in Secrets Manager, reference it by ID, scope its IAM policy to least
privilege, and rotate it on a short, documented cadence. Treat any new access
key as a documented exception per `iac-expert`'s `exception-documentation`
skill.

**Human access** — IAM users with MFA, or (better) identity federation to a
corporate IdP (SSO). No shared accounts, no standing root credentials in code
or config. Use IAM Identity Center (SSO) for just-in-time access to roles
rather than permanent standing credentials.

## Design rules

- **Default to IAM roles.** If the workload runs in AWS, it gets an IAM role —
  no access key, no embedded secret.
- **Federate external workloads.** CI/CD and external systems use OIDC
  federation or IAM Roles Anywhere, not a stored access key.
- **Scope IAM to least privilege.** The role gets only the actions/resources
  the workload actually needs (see the `aws-caf-landing-zones` skill).
- **Never embed secrets.** No access key, secret, or API key as a literal in
  `.tf`, a tfvars file, or a module default. Reference Secrets Manager by ID.
- **Document the exception.** Any long-lived secret is a documented exception
  with a compensating control (rotation cadence, Secrets Manager storage,
  scoped permissions) and an expiry/review date.

## Expected output

An identity design (or a review of one) that states, for each workload: how it
authenticates (IAM role, federated credential, or documented secret
exception), what IAM policy it holds and at what scope, and how human access
is gated (MFA, SSO). No workload authenticates with an undocumented long-lived
access key.
