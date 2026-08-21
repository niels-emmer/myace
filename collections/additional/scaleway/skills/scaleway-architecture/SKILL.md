---
name: Scaleway Architecture
description: Scaleway architecture and governance essentials — Organization/Project structure, IAM scoping, VPC/private-network topology, security groups, and guardrails for Scaleway environments.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [scaleway, iac, architecture, governance, landing-zones]
---
## Purpose

Scaleway has no WAF/CAF-style pillar or adoption framework to map to, so this
single skill is the governance-essentials layer for designing a Scaleway
environment that is secure, auditable, and cost-attributable — the
Organization/Project structure, IAM scoping, VPC/private-network topology,
security groups, and guardrails. It is the Scaleway-specific companion to
`iac-expert`'s generic `well-architected-review` and `resource-naming` skills,
naming the concrete Scaleway constructs that the generic skills can't.

## When to use it

When designing or reviewing a Scaleway environment's structure — a new
project, an IAM/scope change, a network-topology decision, or a security-group
change. Also before scaffolding a new workload into an existing environment,
to confirm it fits the established pattern.

## Organization and Project structure

- Use the hierarchy **Organization → Projects → Resources**, with IAM, billing,
  and support at the Organization level and IAM inherited down to Projects.
- Separate **platform** (bootstrap, networking, security, logging) from
  **workload** projects, so governance applied at the platform level inherits
  down without entangling workload-specific policy.
- Keep the project set shallow and meaningful — a handful of projects, each
  with a clear purpose, not a deep tree that mirrors the org chart.
- Apply IAM at the highest level where it's uniformly correct and let it
  inherit; override only where a genuine exception exists (and document it per
  `iac-expert`'s `exception-documentation` skill).

## IAM scoping

- Assign IAM at the **narrowest effective scope** — a specific Project, or the
  Organization only where the permission genuinely applies everywhere.
- Use **permission sets** (reusable bundles of permissions) bound to a scope
  (Project or Organization), and grant them to **principals** — users, groups,
  or applications.
- Prefer **applications + API keys** for service-to-service and CI/CD access
  (see the identity guidance in the collection's AGENTS.md), never a long-lived
  secret where a scoped application key works.
- Never grant broad `*`/admin permission sets as a shortcut — least privilege
  is the baseline.

## VPC and private-network topology

- Prefer a **private network** (VPC) model: workloads on a private network with
  a NAT gateway for outbound access, so egress/ingress and network policy are
  centralized.
- Use **private networking** for workloads and keep traffic off the public
  internet where possible; reach public services deliberately, not by default.
- Segment with **security groups** (virtual firewalls applied to the public
  interface) and private-network isolation; default to deny and open only what's
  needed, per `iac-expert`'s private-by-default rule. Use multi-AZ/multi-zone
  placement for anything that must survive a zone failure.

## Guardrails

- Enforce the standing invariants with IAM scoping and security-group defaults
  rather than convention: no public IP or `0.0.0.0/0` security-group rule
  without a documented exception, secrets in Secret Manager referenced by ID,
  mandatory cost-attribution tags on every resource.
- Keep the guardrail set small and reviewed — every policy is a maintenance
  burden and a potential deployment blocker. Guardrails are a complement to,
  not a substitute for, least-privilege IAM at the resource level.

## Expected output

An architecture design (or a review of an existing one) that states: the
Organization/Project layout, the IAM model (permission sets, principals, and
scope), the VPC/private-network topology, the security-group posture, and the
guardrails in place — each justified against the essentials above, with any
deviation documented as an exception.
