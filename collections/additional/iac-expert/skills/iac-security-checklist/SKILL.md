---
name: IaC Security Checklist
description: A PASS/FAIL/N-A checklist covering network exposure, identity and secrets, state protection, and tagging — run before any infrastructure change is proposed for apply.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [iac, security, checklist]
---
## Purpose

A fast, consistent pass over an infrastructure change to catch the invariant violations that are easy to miss in a large plan or diff — before it ever reaches the point of asking a human to approve an apply. This is a gate before that request, not a substitute for it.

## When to use it

Run this against every nontrivial IaC change (new resources, modified network/identity/access configuration) before handing it off for review or requesting apply approval. For a trivial change (a tag fix, a variable rename with no resource impact), a quick skim is enough — don't perform ceremony for its own sake.

## Checklist

Mark each item PASS, FAIL, or N/A. Every FAIL needs either a fix or a documented exception (see the `exception-documentation` skill) before the change moves forward.

### Network exposure

- [ ] No resource has a public IP, public endpoint, or `0.0.0.0/0`-equivalent ingress rule unless it's a documented exception.
- [ ] Any newly-public surface is scoped as narrowly as possible (specific ports, specific source ranges) rather than wide-open.
- [ ] Inter-service traffic that could stay on a private network/VPC/VNet does.

### Identity and secrets

- [ ] Service-to-service auth uses managed/workload identity wherever the provider supports it, not a static key or connection string.
- [ ] No plaintext secret, API key, connection string, or credential appears in any `.tf`/`.bicep`/template file, in a committed tfvars/parameter file, or hardcoded in a module default.
- [ ] Any secret that must exist is stored in the provider's secret manager (or equivalent), referenced by reference/ID in code — not embedded as a literal value.
- [ ] Newly-granted permissions (IAM roles, RBAC assignments) are scoped to what the workload actually needs, not a broad built-in admin/owner role taken as a shortcut.

### State protection

- [ ] State is stored in a remote backend with locking enabled — not local state — for anything beyond a personal sandbox.
- [ ] The state backend itself is access-restricted (not broadly readable), since state can contain sensitive values in plaintext.

### Naming and tagging

- [ ] New resources follow the naming convention from the `resource-naming` skill.
- [ ] `owner`, `cost-center`, `environment`, and `workload` tags are all present and correct.

## Expected output

A completed checklist (every item marked, no blanks) with each FAIL either resolved in the change or linked to a documented exception. Report the checklist result alongside the plan summary when handing off for review — don't just say "looks good," show what was actually checked.
