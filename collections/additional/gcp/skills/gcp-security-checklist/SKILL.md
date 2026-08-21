---
name: GCP Security Checklist
description: GCP-recommended security practices — identity, network, data, and monitoring — as a PASS/FAIL/N/A checklist run before any GCP change is proposed for apply.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [gcp, iac, security, checklist]
---
## Purpose

A fast, consistent pass over a GCP infrastructure change to catch the
GCP-recommended security-practice violations that are easy to miss in a large
plan or diff — before it ever reaches the point of asking a human to approve
an apply. This is the GCP-specific companion to `iac-expert`'s generic
`iac-security-checklist`, adding the GCP constructs (IAM, service accounts,
VPC firewall rules, Cloud KMS, Secret Manager, Security Command Center, Cloud
Audit Logs) that the generic checklist can't name.

## When to use it

Run this against every nontrivial GCP change (new resources, modified
network/identity/access configuration) before handing it off for review or
requesting apply approval. For a trivial change (a label fix, a variable
rename with no resource impact), a quick skim is enough.

## Checklist

Mark each item PASS, FAIL, or N/A. Every FAIL needs either a fix or a
documented exception (see `iac-expert`'s `exception-documentation` skill)
before the change moves forward.

### Identity and access

- [ ] Service-to-service and CI/CD auth uses service accounts and Workload
      Identity Federation, not long-lived service-account keys.
- [ ] Any IAM role is scoped to least privilege (specific permissions/
      resources, not `roles/owner`/`*`) and uses Google-managed (predefined)
      roles where possible.
- [ ] Human access is behind IAM with MFA — no shared accounts, no standing
      service-account keys in code or config.
- [ ] Secrets that must exist live in Secret Manager, referenced by ID —
      never embedded as a literal in `.tf`, a tfvars file, or a module
      default.

### Network

- [ ] No resource has a public IP, public endpoint, or `0.0.0.0/0`-equivalent
      VPC firewall rule unless it's a documented exception.
- [ ] Workloads run in private networking; Google-managed services are reached
      via Private Service Connect (or VPC peering) where supported, keeping
      traffic off the public internet.
- [ ] Inter-service traffic that could stay on a private VPC does; VPC
      firewall rules default to deny and open only what's needed.

### Data

- [ ] Data at rest is encrypted (Cloud KMS, Google-managed or
      customer-managed keys) and in transit is TLS.
- [ ] GCS buckets are private by default; public access is a documented
      exception, not the default (and blocked by Organization policy where
      possible).
- [ ] Backups exist and are tested for anything that must survive a failure
      (Cloud SQL automated backups, snapshot schedules, GCS versioning, etc.).

### Monitoring and posture

- [ ] Cloud Logging/metrics and Cloud Audit Logs capture anything that needs
      alerting or audit.
- [ ] Security Command Center posture is not regressed by this change (no new
      high-severity finding introduced).
- [ ] Organization-policy guardrails still pass for the changed resources (no
      new policy violation).

## Expected output

A completed checklist (every item marked, no blanks) with each FAIL either
resolved in the change or linked to a documented exception. Report the
checklist result alongside the plan summary when handing off for review —
don't just say "looks good," show what was actually checked.
