---
name: Azure Naming And Tagging
description: CAF-aligned Azure naming convention and mandatory tags — resource-type abbreviations, region codes, and owner/cost-center/environment/workload tags for cost attribution.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [azure, iac, naming, tagging, governance]
---
## Purpose

Give every Azure resource a name and a set of tags that let anyone — not just
the person who created it — answer "what is this, who owns it, what does it
cost, and can we turn it off" without asking around. This is the
Azure-specific companion to `iac-expert`'s generic `resource-naming` skill:
it keeps the same segment structure and adds the Azure-specific abbreviations,
region codes, and character constraints that the generic skill can't name.

## When to use it

Any time you're scaffolding a new Azure resource, renaming an existing one to
bring it into line, or reviewing a plan/diff for naming and tagging
consistency.

## Naming convention

Compose resource names from fixed segments, in a fixed order, separated by a
single consistent delimiter (hyphen is the safest default — many Azure
resource types disallow underscores, dots, or uppercase):

```
<resource-type-abbreviation>-<workload>-<environment>-<region>[-<instance>]
```

- **resource-type-abbreviation** — a short, consistent code for what the
  resource *is*. Pick one abbreviation per resource type and never vary it.
  Common Azure examples: `vm` (virtual machine), `vnet` (virtual network),
  `nsg` (network security group), `st` (storage account), `kv` (Key Vault),
  `sql` (SQL Database), `app` (App Service), `func` (Function App), `aks`
  (AKS cluster), `rg` (resource group), `pip` (public IP), `nic` (network
  interface).
- **workload** — the application or system the resource belongs to, short and
  stable (e.g. `billing`, `checkout`, `ingest`). Usually the most important
  segment for grouping resources in cost/ownership views.
- **environment** — `dev`, `test`, `stage`, `prod` (or your project's fixed
  vocabulary — pick one set and don't let synonyms like `production`/`prd`/
  `prod` coexist).
- **region** — a short code for the deployed region (e.g. `eus` for East US,
  `weu` for West Europe, `uks` for UK South). Omit only if the resource is
  genuinely global/region-less.
- **instance** (optional) — a numeric or short suffix when more than one of
  the same resource exists in the same workload/environment/region (`-01`,
  `-02`).

Azure enforces per-resource-type character/length rules (some types force
lowercase, disallow hyphens, or cap length) — the segment order and content is
what stays constant, not the exact character set. Check the specific resource
type's constraints before finalizing a name.

## Tagging convention

Every Azure resource gets, at minimum, these tags (Azure tags are
case-insensitive key/value pairs; apply them at the resource group level so
they inherit, and confirm they're not overridden):

| Tag key | Required | Meaning |
|---|---|---|
| `owner` | Yes | The team or individual accountable for this resource — an actual name/team, not "platform" for everything. |
| `cost-center` | Yes | The billing code or cost-center identifier this resource's spend should roll up to in Azure Cost Management. |
| `environment` | Yes | Mirrors the environment segment in the name — lets you filter by environment even if naming drifts. |
| `workload` | Yes | Mirrors the workload segment in the name. |
| `managed-by` | Recommended | How this resource is managed (`terraform`, `bicep`, `manual`) — flags hand-created resources that IaC doesn't know about. |
| `review-date` | Only if a documented exception | Ties into `iac-expert`'s `exception-documentation` skill — when this resource's exception status should be re-reviewed. |

Enforce the mandatory tags with an Azure Policy `DeployIfNotExists`/`audit`
effect (see the `azure-caf-landing-zones` skill) so a missing tag is caught
rather than silently drifting.

## Checklist before treating a resource as done

1. Does the name follow the segment order above, using the project's fixed
   abbreviation for this resource type?
2. Are `owner`, `cost-center`, `environment`, and `workload` all set — not
   inherited implicitly from a resource group default that could drift?
3. If this resource is part of a documented exception, does it carry a
   `review-date` tag matching the exception's expiry?
4. Does the name/tag set match sibling resources in the same workload, or did
   this one drift from the pattern?

## Expected output

A resource name matching the segment template, and a tag set containing at
minimum owner, cost-center, environment, and workload — applied consistently
across every resource in the change, not just the new ones.
