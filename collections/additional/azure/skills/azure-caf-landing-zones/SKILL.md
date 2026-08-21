---
name: Azure CAF Landing Zones
description: Cloud Adoption Framework governance essentials — management-group hierarchy, subscription design, RBAC scoping, Azure Policy guardrails, and network topology for Azure landing zones.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [azure, iac, governance, landing-zones, caf]
---
## Purpose

The Microsoft Cloud Adoption Framework (CAF) is the set of practices for
governing Azure at scale. This skill covers the governance essentials you
need to design a landing zone that is secure, auditable, and cost-attributable
— management-group hierarchy, subscription design, RBAC scoping, Azure Policy
guardrails, and network topology. It deliberately does **not** reproduce the
full landing-zone accelerator; the accelerator is a reference for the
complete, opinionated implementation, while this skill is the decision layer
you apply to any Azure environment.

## When to use it

When designing or reviewing an Azure environment's structure — a new
subscription, a management-group reorganization, a policy/guardrail change, or
a network-topology decision. Also before scaffolding a new workload into an
existing landing zone, to confirm it fits the established pattern.

## Management-group hierarchy

- Separate **platform** (management, connectivity, identity) from **workload**
  management groups, so governance applied at the platform level inherits
  down without entangling workload-specific policy.
- Keep the hierarchy shallow and meaningful — a handful of levels, each with a
  clear purpose, not a deep tree that mirrors the org chart.
- Apply policy and RBAC at the highest level where it's uniformly correct, and
  let it inherit; override only where a genuine exception exists (and document
  it per `iac-expert`'s `exception-documentation` skill).

## Subscription design

- Use subscriptions as **scale units and trust boundaries**, not cost centers
  (cost attribution belongs to tags, not subscription boundaries).
- Group subscriptions by environment/workload boundary (e.g. a
  `prod`/`nonprod` split, or one per major workload) so blast radius and
  policy scope stay manageable.
- Avoid a single subscription for everything, and avoid one subscription per
  microservice — both extremes make governance either impossible or
  unmanageable.

## RBAC scoping

- Assign roles at the **narrowest effective scope** — resource group or
  resource, not subscription-wide, unless the role genuinely applies
  everywhere.
- Prefer built-in roles over custom ones; when a custom role is unavoidable,
  grant only the specific actions needed.
- Use managed identity / workload identity for service-to-service access
  (see the `azure-identity` skill), never a human account or a long-lived
  service-principal secret.
- Never grant Owner/Contributor broadly as a shortcut — least privilege is
  the baseline.

## Azure Policy guardrails

- Enforce the standing invariants with Azure Policy rather than convention:
  deny public IPs / `0.0.0.0/0` NSG rules, require private endpoints where
  supported, require mandatory tags (owner, cost-center, environment,
  workload), enforce allowed regions and SKUs.
- Use **deny** effects for hard security invariants and **audit** (or
  `DeployIfNotExists`) for things that should be remediated rather than
  blocked.
- Keep the policy set small and reviewed — every policy is a maintenance
  burden and a potential deployment blocker.

## Network topology

- Prefer a **hub-spoke** model: a central connectivity hub (shared VNet with
  the egress/ingress path, Azure Firewall, VPN/ExpressRoute gateway) and
  workload spokes that peer to it.
- Use **private endpoints** for PaaS services (storage, SQL, Key Vault, App
  Service) so traffic stays on the Microsoft backbone, not the public
  internet.
- Segment with NSGs/ASGs and VNet isolation; default to deny and open only
  what's needed, per `iac-expert`'s private-by-default rule.

## Expected output

A landing-zone design (or a review of an existing one) that states: the
management-group hierarchy, the subscription layout, the RBAC model, the
policy guardrails in place, and the network topology — each justified against
the essentials above, with any deviation documented as an exception.
