---
name: GCP Landing Zones
description: Google Cloud Adoption Framework governance essentials — resource hierarchy, folder/project design, IAM scoping, VPC topology, and Organization-policy guardrails for GCP landing zones.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [gcp, iac, governance, landing-zones, gcaf]
---
## Purpose

The Google Cloud Adoption Framework (GCAF) is the set of practices for
governing GCP at scale. This skill covers the governance essentials you need
to design a landing zone that is secure, auditable, and cost-attributable —
the resource hierarchy, folder/project design, IAM scoping, VPC topology, and
Organization-policy guardrails. It deliberately does **not** reproduce the full
landing-zone accelerator (Google Cloud's Enterprise Foundations blueprint /
Cloud Foundation Toolkit); the accelerator is a reference for the complete,
opinionated implementation, while this skill is the decision layer you apply
to any GCP environment.

## When to use it

When designing or reviewing a GCP environment's structure — a new project, a
folder reorganization, an Organization-policy/guardrail change, or a
network-topology decision. Also before scaffolding a new workload into an
existing landing zone, to confirm it fits the established pattern.

## Resource hierarchy

- Use the hierarchy **Organization → Folders → Projects → Resources**, with
  IAM and Organization policies applied at each level and inherited down.
- Separate **platform** (bootstrap, networking, security, logging) from
  **workload** folders, so governance applied at the platform level inherits
  down without entangling workload-specific policy.
- Keep the hierarchy shallow and meaningful — a handful of folders, each with
  a clear purpose, not a deep tree that mirrors the org chart.
- Apply IAM and Organization policies at the highest level where it's
  uniformly correct, and let it inherit; override only where a genuine
  exception exists (and document it per `iac-expert`'s
  `exception-documentation` skill).

## Folder and project design

- Use **projects** as scale units and trust boundaries, not cost centers (cost
  attribution belongs to labels, not project boundaries).
- Group projects by environment/workload boundary (e.g. a `prod`/`nonprod`
  split, or one per major workload) so blast radius and policy scope stay
  manageable.
- Keep the **bootstrap/organization** project for organization-wide
  administration and shared infrastructure only — never run workloads in it.
  Use dedicated projects for shared services (logging, networking) and for
  each workload/environment.
- Avoid a single project for everything, and avoid one project per
  microservice — both extremes make governance either impossible or
  unmanageable.

## Organization-policy guardrails

- Enforce the standing invariants with Organization policies rather than
  convention: deny public GCS buckets, deny disabling Cloud Audit Logs, deny
  `iam.serviceAccountKeys.create` where federation is the standard, restrict
  regions and machine types.
- Use **deny** effects for hard security invariants and **audit** (via
  Cloud Asset Inventory / Security Command Center) for things that should be
  remediated rather than blocked.
- Keep the Organization-policy set small and reviewed — every policy is a
  maintenance burden and a potential deployment blocker. Organization policies
  are a guardrail, not a substitute for least-privilege IAM at the resource
  level.

## IAM scoping

- Assign IAM roles at the **narrowest effective scope** — a specific resource
  or service, not project-wide `roles/owner`, unless the role genuinely
  applies everywhere.
- Prefer Google-managed (predefined) roles over custom roles; when a custom
  role is unavoidable, grant only the specific permissions needed.
- Use service accounts and Workload Identity Federation for service-to-service
  and CI/CD access (see the `gcp-identity` skill), never a long-lived
  service-account key.
- Never grant `roles/owner`/`*` broadly as a shortcut — least privilege is the
  baseline.

## VPC topology

- Prefer a **shared VPC** model: a central host project (shared VPC, Cloud NAT,
  Private Service Connect, firewall rules) and service projects that attach to
  it, so egress/ingress and network policy are centralized.
- Use **private networking** for workloads and **Private Service Connect**
  (or VPC peering) for Google-managed services (Cloud SQL, GKE, etc.) so
  traffic stays on the Google backbone, not the public internet.
- Segment with VPC firewall rules and VPC isolation; default to deny and open
  only what's needed, per `iac-expert`'s private-by-default rule. Use
  multi-zone/multi-region for anything that must survive a zone/region
  failure.

## Expected output

A landing-zone design (or a review of an existing one) that states: the
resource hierarchy, the folder/project layout, the IAM model, the
Organization-policy guardrails in place, and the VPC topology — each justified
against the essentials above, with any deviation documented as an exception.
