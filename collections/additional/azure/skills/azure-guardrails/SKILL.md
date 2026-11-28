---
name: Azure Guardrails
description: Catalogue and rollout method for Azure Policy guardrails assigned at management-group scope. Use when designing or changing policy initiatives, effects, exemptions or resource locks.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [azure, governance, guardrails, policy]
---
## Purpose

Enforce governance invariants with Azure Policy in a way that is testable, exempt-able with an expiry and safe to roll out.

## When to use it

When creating or changing Azure Policy definitions, initiatives, assignments or exemptions, or when deciding between policy, RBAC and locks.

## Checklist

- **Assign high**: assign initiatives at the management group that should inherit them, and group related definitions into initiatives instead of many separate assignments.
- **Effects**: use `Audit` to measure, `Deny` for hard invariants, `Modify` and `DeployIfNotExists` to remediate (for example to add tags, since tags do not inherit by themselves), and `Disabled` to switch a definition off without deleting it.
- **Typical guardrails**: allowed locations, required tags, deny public network access on storage and databases, require TLS and minimum TLS version, deny unmanaged disks and public IPs where private networking is the standard, require diagnostic settings to a central workspace.
- **Roll out safely**: assign with `enforcementMode` set to `DoNotEnforce` first so you can see compliance without blocking, review results, then switch to `Default`. Note that in DoNotEnforce mode noncompliant creations may not generate activity-log events, so rely on compliance data. Remediation tasks for `DeployIfNotExists` can still run in that mode.
- **Exemptions**: create them as policy exemptions with a category (waiver or mitigated), a reason and an `expiresOn` date; an expired exemption is no longer honoured but the object remains for the record. For initiatives, match the policy definition reference IDs.
- **Locks**: use `CanNotDelete` locks on critical resources such as the central workspace, key vaults and the hub network; know that a `ReadOnly` lock can break operations that look like reads.
- **Policy versus RBAC**: policy controls what can be configured; RBAC controls who can act. Do not use policy as a substitute for least-privilege roles.
- **As code**: keep definitions, initiatives and assignments in version control and deploy through the pipeline; limit who can edit assignments and exemptions.
- **Record**: each guardrail has an owner, the invariant it enforces and its exception process.

## Expected output

A policy set assigned at the right scope, proven in DoNotEnforce first, with time-boxed exemptions and owners for every definition.
