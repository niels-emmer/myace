---
name: Secrets Management
description: Secrets manager usage, rotation, and least privilege — so credentials are injected at deploy time, rotated on a schedule, and never end up in artifacts, config, or logs.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [secrets, security, credentials, rotation]
---
## Purpose

Secrets are the highest-value target in any environment — a leaked credential is a breach waiting to happen. This skill is the checklist for handling secrets so they're injected at deploy time, rotated on a schedule, and never committed, baked, or logged.

## When to use it

When adding a new secret, wiring credentials into an application or pipeline, reviewing a diff that touches secrets, or responding to a suspected leak.

## Steps / checklist

1. **Never commit secrets.** No credentials, API keys, or tokens in source, config files, or documentation. A committed secret is a compromised secret — rotate it, don't just delete it.
2. **Secrets manager over files.** Secrets live in a secrets manager (Azure Key Vault, AWS Secrets Manager, GCP Secret Manager, Vault) and are injected at deploy time. Not in `.env` files that get committed, not in image build args.
3. **Managed identity over static secrets.** Prefer workload identity (Azure Managed Identity, AWS IAM roles, GCP Workload Identity Federation) over API keys or connection strings wherever the target supports it.
4. **Least privilege.** Each secret is scoped to the service and permission level that needs it. A database credential with admin rights for a read-only service is a finding.
5. **Rotation.** Secrets have a rotation schedule and a rotation path. If a secret can't be rotated without downtime, that's a design defect.
6. **Never log secrets.** Secrets are excluded from logs, error messages, and trace output. Redact on the way in, not on the way out.
7. **Pipeline hygiene.** CI/CD secrets are scoped to the jobs that need them and never exposed to untrusted PRs (fork builds). Pipeline definitions are reviewed like code.

## Expected output

A system where no credential exists outside a secrets manager, every secret has a rotation path, and a leaked secret can be rotated without downtime. If a developer needs a teammate to tell them a password, the secrets management work isn't done.