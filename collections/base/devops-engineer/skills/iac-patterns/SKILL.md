---
name: IaC Patterns
description: Authoring patterns for Terraform and Bicep — remote state, module structure, naming, tagging, and plan review — so infrastructure stays reviewable and reproducible.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [iac, terraform, bicep, infrastructure]
---
## Purpose

Infrastructure-as-code fails in predictable ways: state drift, unreadable modules, resources nobody can name or attribute, and plans nobody actually reads. This skill is the working checklist for authoring Terraform and Bicep that stays reviewable and reproducible over time.

## When to use it

Every time you write or modify IaC — a new resource, a module, a state change, or a refactor. Reach for it explicitly when starting work in an unfamiliar codebase or when you're about to introduce a pattern that doesn't match its neighbors.

## Steps / checklist

1. **Remote state with locking.** State lives in a remote backend (Terraform) or a deployment stack (Bicep) with locking enabled. Local state is not acceptable for anything shared or persistent. Never commit state files.
2. **Module structure.** Split by concern (networking, compute, data, identity), not by resource type. A module should encapsulate a deployable unit with a clear interface — inputs, outputs, and invariants — not a grab-bag of related resources.
3. **Naming and tagging.** Every resource follows the project's naming convention and carries team + cost-center tags (see the `resource-naming` skill in the iac-expert collection for a template). Names are deterministic from inputs, not hand-assigned.
4. **Private by default.** Every resource starts network-isolated. No public IP, `0.0.0.0/0` ingress, or public bucket ACL without a documented exception.
5. **Managed identity over secrets.** Use workload identity (Azure Managed Identity, AWS IAM roles, GCP Workload Identity Federation) over API keys or connection strings. Static secrets only when the target has no identity-federation option.
6. **Plan review discipline.** Read the plan output before applying: does it create/destroy resources the task didn't ask for? Is the diff scoped to the change? A plan you haven't read is a plan you haven't approved.
7. **Drift detection.** Treat drift as a defect. Prefer `plan`/`validate` in CI and scheduled drift checks over discovering divergence at incident time.
8. **Version pinning.** Pin provider and module versions. Unpinned providers make builds non-reproducible and plans unpredictable.

## Expected output

IaC that a reviewer can read top-to-bottom and understand what it creates, why, and what it costs — with a plan output that matches the stated intent. If a reviewer can't tell what a resource is for from its name and tags, the change isn't done.