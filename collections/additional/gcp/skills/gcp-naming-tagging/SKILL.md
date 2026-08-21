---
name: GCP Naming And Labeling
description: GCP naming convention and mandatory labels — resource-type abbreviations, region codes, and owner/cost-center/environment/workload labels for cost attribution.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [gcp, iac, naming, labeling, governance]
---
## Purpose

Give every GCP resource a name and a set of labels that let anyone — not just
the person who created it — answer "what is this, who owns it, what does it
cost, and can we turn it off" without asking around. This is the GCP-specific
companion to `iac-expert`'s generic `resource-naming` skill: it keeps the same
segment structure and adds the GCP-specific abbreviations, region codes, and
character constraints that the generic skill can't name.

## When to use it

Any time you're scaffolding a new GCP resource, renaming an existing one to
bring it into line, or reviewing a plan/diff for naming and labeling
consistency.

## Naming convention

Compose resource names from fixed segments, in a fixed order, separated by a
single consistent delimiter (hyphen is the safest default — many GCP resource
types disallow underscores, dots, or uppercase):

```
<resource-type-abbreviation>-<workload>-<environment>-<region>[-<instance>]
```

- **resource-type-abbreviation** — a short, consistent code for what the
  resource *is*. Pick one abbreviation per resource type and never vary it.
  Common GCP examples: `vm` (Compute Engine instance), `vpc` (VPC network),
  `fw` (firewall rule), `gcs` (Cloud Storage bucket), `sql` (Cloud SQL
  instance), `lb` (load balancer), `gke` (GKE cluster), `bq` (BigQuery
  dataset), `sa` (service account), `nat` (Cloud NAT), `psc` (Private Service
  Connect endpoint).
- **workload** — the application or system the resource belongs to, short and
  stable (e.g. `billing`, `checkout`, `ingest`). Usually the most important
  segment for grouping resources in cost/ownership views.
- **environment** — `dev`, `test`, `stage`, `prod` (or your project's fixed
  vocabulary — pick one set and don't let synonyms like `production`/`prd`/
  `prod` coexist).
- **region** — a short code for the deployed region (e.g. `us-central1`,
  `europe-west1`, `asia-southeast1`). Omit only if the resource is genuinely
  global/region-less (e.g. IAM, Cloud DNS, some load balancers).
- **instance** (optional) — a numeric or short suffix when more than one of
  the same resource exists in the same workload/environment/region (`-01`,
  `-02`).

GCP enforces per-resource-type character/length rules (some types force
lowercase, disallow hyphens, or cap length) — the segment order and content is
what stays constant, not the exact character set. Check the specific resource
type's constraints before finalizing a name.

## Labeling convention

Every GCP resource gets, at minimum, these labels (GCP labels are
case-sensitive key/value pairs; apply them consistently and confirm they're
not overridden):

| Label key | Required | Meaning |
|---|---|---|
| `owner` | Yes | The team or individual accountable for this resource — an actual name/team, not "platform" for everything. |
| `cost-center` | Yes | The billing code or cost-center identifier this resource's spend should roll up to in Cloud Billing. |
| `environment` | Yes | Mirrors the environment segment in the name — lets you filter by environment even if naming drifts. |
| `workload` | Yes | Mirrors the workload segment in the name. |
| `managed-by` | Recommended | How this resource is managed (`terraform`, `deployment-manager`, `manual`) — flags hand-created resources that IaC doesn't know about. |
| `review-date` | Only if a documented exception | Ties into `iac-expert`'s `exception-documentation` skill — when this resource's exception status should be re-reviewed. |

Enable **label-based cost attribution** in Cloud Billing so the mandatory
labels actually roll up in cost reports. Enforce the mandatory labels with an
Organization policy (or a Cloud Asset Inventory / Security Command Center
check, see the `gcp-landing-zones` skill) so a missing label is caught rather
than silently drifting.

## Checklist before treating a resource as done

1. Does the name follow the segment order above, using the project's fixed
   abbreviation for this resource type?
2. Are `owner`, `cost-center`, `environment`, and `workload` all set — not
   inherited implicitly from a default that could drift?
3. If this resource is part of a documented exception, does it carry a
   `review-date` label matching the exception's expiry?
4. Does the name/label set match sibling resources in the same workload, or
   did this one drift from the pattern?

## Expected output

A resource name matching the segment template, and a label set containing at
minimum owner, cost-center, environment, and workload — applied consistently
across every resource in the change, not just the new ones.
