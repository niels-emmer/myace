---
name: Azure Security Checklist
description: Microsoft-recommended Azure security practices — identity, network, data, and monitoring — as a PASS/FAIL/N/A checklist run before any Azure change is proposed for apply.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [azure, iac, security, checklist]
---
## Purpose

A fast, consistent pass over an Azure infrastructure change to catch the
Microsoft-recommended security-practice violations that are easy to miss in a
large plan or diff — before it ever reaches the point of asking a human to
approve an apply. This is the Azure-specific companion to `iac-expert`'s
generic `iac-security-checklist`, adding the Azure constructs (Entra ID,
private endpoints, Key Vault, Defender for Cloud, Azure Policy) that the
generic checklist can't name.

## When to use it

Run this against every nontrivial Azure change (new resources, modified
network/identity/access configuration) before handing it off for review or
requesting apply approval. For a trivial change (a tag fix, a variable rename
with no resource impact), a quick skim is enough.

## Checklist

Mark each item PASS, FAIL, or N/A. Every FAIL needs either a fix or a
documented exception (see `iac-expert`'s `exception-documentation` skill)
before the change moves forward.

### Identity and access

- [ ] Service-to-service auth uses managed identity or workload identity
      federation, not a service-principal client secret or connection string.
- [ ] Any RBAC assignment is scoped to least privilege (resource
      group/resource, not broad Contributor/Owner) and uses built-in roles
      where possible.
- [ ] Human access is behind Entra ID with MFA and conditional access — no
      shared accounts, no standing admin credentials in code or config.
- [ ] Secrets that must exist live in Key Vault, referenced by ID — never
      embedded as a literal in `.tf`/`.bicep`/ARM, a tfvars/parameter file, or
      a module default.

### Network

- [ ] No resource has a public IP, public endpoint, or `0.0.0.0/0`-equivalent
      NSG rule unless it's a documented exception.
- [ ] PaaS services use private endpoints / VNet integration where supported,
      keeping traffic off the public internet.
- [ ] Inter-service traffic that could stay on a private VNet does; NSGs/ASGs
      default to deny and open only what's needed.

### Data

- [ ] Data at rest is encrypted (Azure-managed or customer-managed keys) and
      in transit is TLS.
- [ ] Storage/blob access is private by default; public access is a documented
      exception, not the default.
- [ ] Backups exist and are tested for anything that must survive a failure
      (Azure Backup, geo-replication, etc.).

### Monitoring and posture

- [ ] Diagnostic settings ship logs/metrics to Log Analytics for anything
      that needs alerting or audit.
- [ ] Defender for Cloud posture is not regressed by this change (no new
      high-severity recommendation introduced).
- [ ] Azure Policy guardrails still pass for the changed resources (no new
      policy violation).

## Expected output

A completed checklist (every item marked, no blanks) with each FAIL either
resolved in the change or linked to a documented exception. Report the
checklist result alongside the plan summary when handing off for review —
don't just say "looks good," show what was actually checked.
