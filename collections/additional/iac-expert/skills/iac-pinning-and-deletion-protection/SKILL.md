---
name: IaC Pinning And Deletion Protection
description: Checklist for pinning IaC tool, provider and module versions and for guarding stateful resources against accidental destroy or replace. Use when creating a stack, upgrading providers or reviewing a plan that destroys resources.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [iac, terraform, safety]
---
## Purpose

Make infrastructure changes reproducible and make destructive changes deliberate.

## When to use it

When starting a stack, bumping a tool or provider version, reviewing a plan, or marking resources as protected.

## Checklist

- **Tool version**: set a required version constraint for the IaC tool (for Terraform and OpenTofu, `required_version`) and run the same version locally and in CI.
- **Providers**: declare each provider with a source and a version constraint, commit the dependency lock file, and review its diff on upgrade (`terraform init -upgrade` is a change, not a refresh).
- **Modules**: pin registry modules to a version and git modules to a tag or commit; never track a branch.
- **Upgrades**: one provider or major version at a time, with a plan on a non-production stack first; read the changelog for renamed or removed arguments.
- **Deletion protection**: turn on the resource's native protection where it exists (database and storage deletion protection, key deletion windows, termination protection) and add `lifecycle { prevent_destroy = true }` for the most critical resources. Remember `prevent_destroy` only blocks destroys from this configuration; removing the block or the resource from code defeats it, so review those diffs.
- **Plan review**: search the plan for `destroy`, `replace` and `forces replacement`; each one needs a stated reason and approval, and replacing a stateful resource needs a backup and migration plan.
- **State safety**: back up state, never edit it by hand, and use `moved` blocks or import rather than recreate when refactoring.
- **Drift**: schedule a read-only plan to detect drift and treat unexpected diffs as incidents to understand, not to blindly apply.
- **Exceptions**: any waiver of these checks is recorded with the `exception-documentation` skill.

## Expected output

A stack whose versions are pinned, whose critical resources are protected, and whose plans show no destroy or replace without a recorded approval.
