---
name: GCP Guardrails
description: Catalogue and rollout method for Organization Policy constraints, tags, dry-run mode and VPC Service Controls. Use when designing or changing organisation-wide controls on Google Cloud.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [gcp, governance, guardrails, org-policy]
---
## Purpose

Enforce invariants with Organization Policy and test them before they block anyone.

## When to use it

When setting or changing an Organization Policy, deciding whether a control is a constraint, an IAM condition or a perimeter, or granting the right to edit policy.

## Checklist

- **Typical constraints**: resource location restriction (`gcp.resourceLocations`), no service-account key creation (`iam.disableServiceAccountKeyCreation` or its managed equivalent), public access prevention on Cloud Storage (`storage.publicAccessPrevention`), domain-restricted sharing (`iam.allowedPolicyMemberDomains`), no external IPs on VMs (`compute.vmExternalIpAccess`), OS Login (`compute.requireOsLogin`), no public Cloud SQL IPs (`sql.restrictPublicIp`), and skipping default network creation (`compute.skipDefaultNetworkCreation`). Check the constraint list for current names and managed variants.
- **Inheritance**: policies set at the organisation or folder inherit down; override at a lower level only for a documented exception, and use tag-based conditional rules to scope a constraint to tagged resources (a conditional rule needs at least one unconditional rule).
- **Test first**: use dry-run policies, which audit-log violations without blocking, and Policy Simulator to preview impact. Dry-run is available only for a subset of constraints and needs billing enabled, so check support for the constraint and confirm results against audit logs.
- **Custom constraints**: write a custom constraint only when no built-in or managed one fits, and keep a small, reviewed set.
- **Who can change it**: restrict `roles/orgpolicy.policyAdmin` to a small group and require review for changes; policy edits are an organisation-wide change.
- **Perimeters**: use VPC Service Controls for data-exfiltration boundaries around sensitive services, start in dry-run mode, and plan ingress and egress rules for legitimate flows before enforcing.
- **Policy versus IAM**: Organization Policy limits what can be configured; IAM limits who can act. Use both.
- **As code**: manage policies with IaC and pipeline review; avoid console edits.
- **Record**: each constraint has an owner, the invariant it enforces and its exception process.

## Expected output

A constraint set applied at the right level, proven in dry-run where supported, with restricted edit rights, owners and documented exceptions.
