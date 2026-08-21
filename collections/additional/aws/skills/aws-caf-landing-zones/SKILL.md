---
name: AWS CAF Landing Zones
description: Cloud Adoption Framework governance essentials — AWS Organizations OU hierarchy, account design, Service Control Policies, IAM scoping, and VPC topology for AWS landing zones.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [aws, iac, governance, landing-zones, caf]
---
## Purpose

The AWS Cloud Adoption Framework (CAF) is the set of practices for governing
AWS at scale. This skill covers the governance essentials you need to design a
landing zone that is secure, auditable, and cost-attributable — AWS
Organizations OU hierarchy, account design, Service Control Policies (SCPs),
IAM scoping, and VPC topology. It deliberately does **not** reproduce the full
landing-zone accelerator (AWS Control Tower / Landing Zone Accelerator); the
accelerator is a reference for the complete, opinionated implementation, while
this skill is the decision layer you apply to any AWS environment.

## When to use it

When designing or reviewing an AWS environment's structure — a new account, an
OU reorganization, an SCP/guardrail change, or a network-topology decision.
Also before scaffolding a new workload into an existing landing zone, to
confirm it fits the established pattern.

## AWS Organizations OU hierarchy

- Separate **platform** (management, connectivity, security) from **workload**
  OUs, so governance applied at the platform level inherits down without
  entangling workload-specific policy.
- Keep the hierarchy shallow and meaningful — a handful of OUs, each with a
  clear purpose, not a deep tree that mirrors the org chart.
- Apply SCPs and IAM at the highest level where it's uniformly correct, and
  let it inherit; override only where a genuine exception exists (and document
  it per `iac-expert`'s `exception-documentation` skill).

## Account design

- Use accounts as **scale units and trust boundaries**, not cost centers (cost
  attribution belongs to tags, not account boundaries).
- Group accounts by environment/workload boundary (e.g. a `prod`/`nonprod`
  split, or one per major workload) so blast radius and policy scope stay
  manageable.
- Keep the **management account** for billing and organization-wide
  administration only — never run workloads in it. Use dedicated accounts for
  shared services (logging, networking) and for each workload/environment.
- Avoid a single account for everything, and avoid one account per
  microservice — both extremes make governance either impossible or
  unmanageable.

## Service Control Policies (SCPs)

- Enforce the standing invariants with SCPs rather than convention: deny
  public S3 buckets, deny leaving CloudTrail/Config disabled, deny
  `iam:CreateAccessKey` where federation is the standard, restrict regions and
  instance types.
- Use **deny** effects for hard security invariants and **audit** (via Config
  rules) for things that should be remediated rather than blocked.
- Keep the SCP set small and reviewed — every policy is a maintenance burden
  and a potential deployment blocker. SCPs are a guardrail, not a substitute
  for least-privilege IAM at the resource level.

## IAM scoping

- Assign IAM roles/policies at the **narrowest effective scope** — a specific
  resource or service, not account-wide `AdministratorAccess`, unless the role
  genuinely applies everywhere.
- Prefer AWS-managed policies over custom ones; when a custom policy is
  unavoidable, grant only the specific actions needed.
- Use IAM roles and identity federation for service-to-service and CI/CD
  access (see the `aws-identity` skill), never a long-lived access key.
- Never grant `AdministratorAccess`/`*` broadly as a shortcut — least
  privilege is the baseline.

## VPC topology

- Prefer a **hub-spoke** model: a central connectivity VPC (shared egress/ingress
  path, transit gateway, NAT gateways, VPC endpoints) and workload VPCs that
  peer to it.
- Use **private subnets** for workloads and **VPC endpoints** (interface and
  gateway endpoints) for AWS services (S3, DynamoDB, Secrets Manager, etc.) so
  traffic stays on the AWS backbone, not the public internet.
- Segment with security groups and NACLs and VPC isolation; default to deny and
  open only what's needed, per `iac-expert`'s private-by-default rule. Use
  multi-AZ for anything that must survive an AZ failure.

## Expected output

A landing-zone design (or a review of an existing one) that states: the OU
hierarchy, the account layout, the IAM model, the SCP guardrails in place, and
the VPC topology — each justified against the essentials above, with any
deviation documented as an exception.
