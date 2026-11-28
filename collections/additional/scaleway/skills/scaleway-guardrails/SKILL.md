---
name: Scaleway Guardrails
description: Guardrail approach for Scaleway where no organisation-level deny policy exists, covering IAM design, Project boundaries, audit logging and review. Use when designing or reviewing governance on Scaleway.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [scaleway, governance, guardrails, iam]
---
## Purpose

Compensate for the absence of a central deny layer by designing IAM, Projects and review so the same invariants hold.

## When to use it

When structuring Organizations and Projects, writing IAM policies for people and applications, or reviewing how an invariant is enforced.

## Checklist

- **Know the model**: IAM policies attach to users, groups and applications; each rule pairs permission sets with a scope of one or more Projects or the whole Organization; rules only allow, so access is the union of what a principal's policies grant. There is no per-resource scope, so use Projects as the boundary. Check Scaleway's current documentation, since features are still being added.
- **No deny layer**: because there is no organisation-wide deny equivalent to AWS SCPs, Azure Policy or Google Organization Policy, enforce invariants through narrow permission sets, Project separation, IaC review and detective checks.
- **Projects as boundaries**: one Project per environment and workload boundary; keep production in its own Project with the fewest principals.
- **Least privilege**: give people and applications specific permission sets scoped to the Project they need, not `AllProductsFullAccess` on the Organization; prefer groups over per-user policies.
- **Machine access**: one application per workload with its own policy and API key, keys rotated and stored in a secret manager, and no keys tied to a person's account for automation.
- **Humans**: enforce MFA, remove stale users, and review Organization-scoped policies on a schedule; account for propagation delays of up to a minute when testing a change.
- **Detect**: enable Audit Trail (it needs Organization-level permission sets to read) and alert on IAM changes and API-key creation.
- **Enforce in code**: because the platform will not block a bad configuration, the IaC pipeline's policy checks and human review are the control; add automated checks for public buckets, open security groups and unmanaged keys.
- **Record**: each invariant has an owner and a named enforcement method (permission design, pipeline check or detective control), and exceptions follow the register.

## Expected output

A written map from each governance invariant to the mechanism that enforces or detects it on Scaleway, with owners and a review schedule.
