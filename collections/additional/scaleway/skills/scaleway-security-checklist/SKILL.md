---
name: Scaleway Security Checklist
description: Scaleway-recommended security practices — identity, network, data, and monitoring — as a PASS/FAIL/N/A checklist run before any Scaleway change is proposed for apply.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [scaleway, iac, security, checklist]
---
## Purpose

A fast, consistent pass over a Scaleway infrastructure change to catch the
Scaleway-recommended security-practice violations that are easy to miss in a
large plan or diff — before it ever reaches the point of asking a human to
approve an apply. This is the Scaleway-specific companion to `iac-expert`'s
generic `iac-security-checklist`, adding the Scaleway constructs (IAM
permission sets, applications + API keys, security groups, private networks,
VPC, WAF edge protection, Secret Manager) that the generic checklist can't
name.

## When to use it

Run this against every nontrivial Scaleway change (new resources, modified
network/identity/access configuration) before handing it off for review or
requesting apply approval. For a trivial change (a tag fix, a variable rename
with no resource impact), a quick skim is enough.

## Checklist

Mark each item PASS, FAIL, or N/A. Every FAIL needs either a fix or a
documented exception (see `iac-expert`'s `exception-documentation` skill)
before the change moves forward.

### Identity and access

- [ ] Service-to-service and CI/CD auth uses IAM applications + API keys (or
      identity federation), not long-lived shared credentials.
- [ ] Any IAM permission set is scoped to least privilege (specific
      permissions/scope, not a broad `*`/admin grant) and bound to the
      narrowest effective scope (Project, not Organization).
- [ ] Human access is behind IAM with MFA (and identity federation via
      OAuth2/SAML SSO where available) — no shared accounts, no standing
      credentials in code or config.
- [ ] Secrets that must exist live in Secret Manager, referenced by ID —
      never embedded as a literal in `.tf`, a tfvars file, or a module
      default.

### Network

- [ ] No resource has a public IP, public endpoint, or `0.0.0.0/0`-equivalent
      security-group rule unless it's a documented exception.
- [ ] Workloads run on a private network (VPC) with a NAT gateway for outbound
      access; traffic stays off the public internet where possible.
- [ ] Security groups default to deny and open only what's needed; WAF edge
      protection is applied where the workload is publicly reachable.

### Data

- [ ] Data at rest is encrypted (Scaleway-managed or customer-managed keys)
      and in transit is TLS.
- [ ] Object-storage buckets are private by default; public access is a
      documented exception, not the default.
- [ ] Backups exist and are tested for anything that must survive a failure
      (database automated backups, snapshot schedules, object-storage
      versioning, etc.).

### Monitoring and posture

- [ ] Logging/metrics capture anything that needs alerting or audit.
- [ ] The change does not regress the security posture (no new public
      exposure, no new broad IAM grant, no new undocumented exception).
- [ ] Guardrails still pass for the changed resources (no new policy
      violation).

## Expected output

A completed checklist (every item marked, no blanks) with each FAIL either
resolved in the change or linked to a documented exception. Report the
checklist result alongside the plan summary when handing off for review —
don't just say "looks good," show what was actually checked.
