---
name: Resource Naming And Tagging
description: A concrete, cloud-agnostic naming and tagging template for infrastructure resources — resource type, workload, environment, region, plus mandatory ownership and cost tags.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [iac, naming, tagging, governance]
---
## Purpose

Give every resource a name and a set of tags that let anyone — not just the person who created it — answer "what is this, who owns it, what does it cost, and can we turn it off" without having to ask around. This is the concrete template behind the "Consistent Naming And Tagging" rule.

## When to use it

Any time you're scaffolding a new resource, renaming an existing one to bring it into line, or reviewing a plan/diff for naming and tagging consistency.

## Naming convention

Compose resource names from fixed segments, in a fixed order, separated by a single consistent delimiter (hyphen is the safest default — some resource types don't allow underscores or dots):

```
<resource-type-abbreviation>-<workload>-<environment>-<region>[-<instance>]
```

- **resource-type-abbreviation** — a short, consistent code for what the resource *is* (e.g. `vm`, `sql`, `st` for storage, `kv` for a secret/key vault, `func` for a function app). Pick one abbreviation per resource type and never vary it.
- **workload** — the application or system the resource belongs to, short and stable (e.g. `billing`, `checkout`, `ingest`). This is usually the most important segment for grouping resources in cost/ownership views.
- **environment** — `dev`, `test`, `stage`, `prod` (or your project's equivalent set — pick one fixed vocabulary and don't let synonyms like `production`/`prd`/`prod` coexist).
- **region** — a short code for the deployed region (provider-specific, e.g. `eus` for East US, `weu` for West Europe, `use1` for AWS us-east-1). Omit only if the resource is genuinely global/region-less.
- **instance** (optional) — a numeric or short suffix when more than one of the same resource exists in the same workload/environment/region (`-01`, `-02`).

Adjust casing and allowed characters to whatever the specific resource type permits (some cloud resource types disallow hyphens or force lowercase) — the segment order and content is what stays constant across providers and resource types, not the exact character set.

## Tagging convention

Every resource gets, at minimum, these tags/labels (key names below are illustrative — match whatever key convention the project has already standardized on):

| Tag key | Required | Meaning |
|---|---|---|
| `owner` | Yes | The team or individual accountable for this resource — an actual name/team, not "platform" for everything. |
| `cost-center` | Yes | The billing code or cost-center identifier this resource's spend should roll up to. |
| `environment` | Yes | Mirrors the environment segment in the name — lets you filter by environment even if naming drifts. |
| `workload` | Yes | Mirrors the workload segment in the name. |
| `managed-by` | Recommended | How this resource is managed (`terraform`, `opentofu`, `bicep`, `manual`) — flags hand-created resources that IaC doesn't know about. |
| `review-date` | Only if this resource is a documented exception | Ties into the `exception-documentation` skill — when this resource's exception status should be re-reviewed. |

## Checklist before treating a resource as done

1. Does the name follow the segment order above, using the project's fixed abbreviation for this resource type?
2. Are `owner`, `cost-center`, `environment`, and `workload` all set — not inherited implicitly from a resource group/project default that could drift?
3. If this resource is part of a documented exception, does it carry a `review-date` tag matching the exception's expiry?
4. Does the name/tag set match sibling resources in the same workload, or did this one drift from the pattern?

## Expected output

A resource name matching the segment template, and a tag/label set containing at minimum owner, cost-center, environment, and workload — applied consistently across every resource in the change, not just the new ones.
