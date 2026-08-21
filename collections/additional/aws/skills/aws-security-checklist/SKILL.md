---
name: AWS Security Checklist
description: AWS-recommended security practices — identity, network, data, and monitoring — as a PASS/FAIL/N/A checklist run before any AWS change is proposed for apply.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [aws, iac, security, checklist]
---
## Purpose

A fast, consistent pass over an AWS infrastructure change to catch the
AWS-recommended security-practice violations that are easy to miss in a large
plan or diff — before it ever reaches the point of asking a human to approve
an apply. This is the AWS-specific companion to `iac-expert`'s generic
`iac-security-checklist`, adding the AWS constructs (IAM, security groups,
private subnets, KMS, Secrets Manager, Security Hub/GuardDuty/Config,
CloudTrail) that the generic checklist can't name.

## When to use it

Run this against every nontrivial AWS change (new resources, modified
network/identity/access configuration) before handing it off for review or
requesting apply approval. For a trivial change (a tag fix, a variable rename
with no resource impact), a quick skim is enough.

## Checklist

Mark each item PASS, FAIL, or N/A. Every FAIL needs either a fix or a
documented exception (see `iac-expert`'s `exception-documentation` skill)
before the change moves forward.

### Identity and access

- [ ] Service-to-service and CI/CD auth uses IAM roles and identity federation
      (IAM Roles Anywhere, OIDC federation), not long-lived access keys.
- [ ] Any IAM policy is scoped to least privilege (specific actions/resources,
      not `AdministratorAccess`/`*`) and uses AWS-managed policies where
      possible.
- [ ] Human access is behind IAM with MFA — no shared accounts, no standing
      root/access-key credentials in code or config.
- [ ] Secrets that must exist live in Secrets Manager (or SSM Parameter Store),
      referenced by ID — never embedded as a literal in `.tf`, a tfvars file,
      or a module default.

### Network

- [ ] No resource has a public IP, public endpoint, or `0.0.0.0/0`-equivalent
      security-group rule unless it's a documented exception.
- [ ] Workloads run in private subnets; AWS services are reached via VPC
      endpoints where supported, keeping traffic off the public internet.
- [ ] Inter-service traffic that could stay on a private VPC does; security
      groups/NACLs default to deny and open only what's needed.

### Data

- [ ] Data at rest is encrypted (KMS, AWS-managed or customer-managed keys) and
      in transit is TLS.
- [ ] S3 buckets are private by default; public access is a documented
      exception, not the default (and blocked by SCP where possible).
- [ ] Backups exist and are tested for anything that must survive a failure
      (RDS automated backups, EBS snapshots, S3 versioning, etc.).

### Monitoring and posture

- [ ] CloudWatch Logs/metrics and CloudTrail capture anything that needs
      alerting or audit.
- [ ] Security Hub/GuardDuty/Config posture is not regressed by this change (no
      new high-severity finding introduced).
- [ ] SCP/Config guardrails still pass for the changed resources (no new policy
      violation).

## Expected output

A completed checklist (every item marked, no blanks) with each FAIL either
resolved in the change or linked to a documented exception. Report the
checklist result alongside the plan summary when handing off for review —
don't just say "looks good," show what was actually checked.
