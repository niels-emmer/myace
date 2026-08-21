# Plan: Vendor-Specific Cloud Collections (Azure First)

## Status

**Azure first pass complete.** The `azure` collection ships (skills-only,
Terraform-emphasis/Bicep-aware, CAF governance essentials), `iac-expert`'s
seed description is fixed, and `azure` is registered in `STARTER_COLLECTIONS`.
AWS / Google Cloud / Scaleway remain as follow-ups using the template in step
5. This is a design plan for restructuring the starter-pack
`Infrastructure` category so that general cloud/IaC practice stays in the
vendor-agnostic `iac-expert` collection, and each cloud vendor gets its own
`additional/` collection layered on top. Azure ships first, grounded in the
Microsoft Well-Architected Framework (WAF), Cloud Adoption Framework (CAF),
and Microsoft-recommended security practices. AWS, Google Cloud, and Scaleway
follow the same template.

## Problem

Today `collections/additional/iac-expert/` is the only Infrastructure
collection. It is deliberately cloud-agnostic (its `AGENTS.md` and skills
reference Azure/AWS/GCP only as passing examples), but it carries a
contradiction in its own seed metadata:

- `seed_collections.py` describes it as *"Cloud-agnostic IaC governance
  (**Azure CAF/WAF worked example**)"* — yet the collection contains no
  Azure-specific content at all. The description promises something the
  content doesn't deliver.

More importantly, there is no home for vendor-specific guidance. A user
deploying to Azure gets the same generic "use managed identity, follow the
well-architected pillars" advice as someone on AWS — nothing about Azure
landing zones, CAF governance/management-group hierarchy, Entra ID identity
design, Azure Policy, Defender for Cloud, or the specific WAF pillar
checklists Microsoft publishes. The same gap exists for AWS, GCP, and
Scaleway.

## Goals

- **Keep `iac-expert` purely vendor-agnostic.** It owns the general IaC
  invariants (private-by-default, managed identity over secrets, naming/
  tagging, remote state with locking, approval-gated applies, documented
  exceptions, well-architected pillar review). Fix its seed description so it
  stops claiming an Azure worked example it doesn't contain.
- **Add one `additional/` collection per vendor**, layered on top of
  `iac-expert` (and typically a base collection) via the existing
  base + additional composition model (`Profile.base_collection_id` +
  `additional_collection_ids`, deduped by name in `compile_profile()`).
- **Ship Azure first**, following WAF, CAF, and Microsoft-recommended
  security practices.
- **Establish a repeatable template** so AWS / Google Cloud / Scaleway are
  mechanical follow-ups, not fresh design work.

## Non-goals

- **No new adapters.** These are content collections (skills/agents/rules),
  not new compile targets. `backend/app/adapters/` is untouched.
- **No backend/schema changes.** This is purely new starter-pack content plus
  a `STARTER_COLLECTIONS` registry entry. No migration, no new model.
- **Not an exhaustive Azure service catalog.** The Azure collection covers
  the *governance/architecture/security* layer (WAF + CAF + security), not a
  per-service reference. Service-specific depth can be a later follow-up.
- **Not building the AWS/GCP/Scaleway collections now** — only the template
  and the Azure instance of it.

## Proposed approach

### 1. Fix `iac-expert` to be cleanly vendor-agnostic

- Update `seed_collections.py`'s `iac-expert` description to drop the
  "Azure CAF/WAF worked example" claim. Suggested: *"Cloud-agnostic IaC
  governance — invariants, naming, approval-gated applies, documented
  exceptions, well-architected pillar review."*
- Audit the existing `iac-expert` content for any residual vendor bias and
  keep it neutral. Current content is already clean (Azure appears only as
  one example among AWS/GCP); no content changes expected beyond the
  description.
- Keep `iac-expert`'s existing artifact names (`iac-builder`, `iac-reviewer`,
  `resource-naming`, `well-architected-review`, `iac-security-checklist`,
  `exception-documentation`) — these are the general layer the vendor
  collections build on.

### 2. Create the Azure collection: `collections/additional/azure/`

Structure mirrors the scanner's on-disk format (skills/, agents/, AGENTS.md).
Proposed content, all named to avoid collisions with `iac-expert` (rule 29 —
see step 4):

**`AGENTS.md`** — Azure-specific standing rules:
- Azure landing zone / CAF governance: management-group hierarchy, RBAC at
  the right scope, policy-driven guardrails, subscription design.
- Identity: Entra ID / managed identity / workload identity federation over
  service principals with secrets; conditional access posture.
- Security: Defender for Cloud posture, Azure Policy, network security
  (NSG/ASG, private endpoints, VNet isolation), Key Vault for secrets.
- Cost: Azure cost management, tagging for cost attribution, reserved
  instances/commitment where load warrants.
- WAF: map changes to Azure WAF pillars (reliability, security, cost
  optimization, operational excellence, performance efficiency).

**`skills/`** (each a `SKILL.md`):
- `azure-waf-review/SKILL.md` — Azure-specific WAF pillar checklists
  (reliability, security, cost optimization, operational excellence,
  performance efficiency), referencing Microsoft's WAF documentation.
- `azure-caf-landing-zones/SKILL.md` — CAF landing-zone design: management
  group hierarchy, subscription design, RBAC scoping, policy/guardrails,
  network topology (hub-spoke, private endpoints), naming/tagging per CAF.
- `azure-security-checklist/SKILL.md` — Microsoft-recommended security
  practices: identity (Entra ID, MFA, conditional access), network
  (private endpoints, NSG/ASG, VNet isolation), data (Key Vault, encryption,
  Defender for Cloud), monitoring (Defender, Sentinel, diagnostic settings).
- `azure-identity/SKILL.md` — Entra ID + managed identity + workload
  identity federation design; when to use which; avoiding long-lived
  service-principal secrets.
- `azure-naming-tagging/SKILL.md` — CAF-aligned naming convention and
  mandatory tags (owner, cost-center, environment, workload, managed-by),
  extending `iac-expert`'s generic `resource-naming` skill with Azure
  specifics (resource-type abbreviations, region codes, allowed characters).

**`agents/`** — **none (decided: skills-only).** The Azure collection reuses
`iac-expert`'s `iac-builder`/`iac-reviewer` agents and adds only Azure
*skills*. The generic builder/reviewer already reference `.tf`/`.bicep` and
the WAF/security invariants; dedicated Azure agents would duplicate that
layer without a concrete gap to fill.

### 3. Register in `seed_collections.py`

Add an `azure` entry to `STARTER_COLLECTIONS["additional"]`:

```python
"azure": {
    "name": "Azure Cloud Architect",
    "category": "Infrastructure",
    "description": (
        "Azure-specific architecture and governance — WAF pillars, CAF "
        "landing zones, Entra ID identity, Azure Policy/Defender security "
        "posture. Layers on the vendor-agnostic iac-expert collection."
    ),
},
```

No migration needed — seeding is idempotent by `(name, is_starter_pack)` and
picks up new collections on next backend start (rule 25).

### 4. Naming-collision discipline (rule 29)

`compile_profile()` dedups artifacts by name across all collections in a
profile, later collections winning. Since `azure` is designed to layer onto
`iac-expert` (a natural pairing), every Azure artifact name must be distinct
from `iac-expert`'s and from the base collections. Concretely:

- Prefix Azure skill names with `azure-` (`azure-waf-review`, not
  `well-architected-review`; `azure-security-checklist`, not
  `iac-security-checklist`; `azure-naming-tagging`, not `resource-naming`).
- Agent names `azure-builder`/`azure-reviewer` (not `iac-builder`/
  `iac-reviewer`).
- Before finalizing, run the collision grep from rule 29 across
  `collections/` to confirm no name reuse.

### 5. Establish the vendor template (for AWS/GCP/Scaleway follow-ups)

Document the pattern so the remaining vendors are mechanical:

- One `additional/<vendor>/` collection, category `Infrastructure`.
- `AGENTS.md` with vendor-specific standing rules.
- Skills: `<vendor>-waf-review`, `<vendor>-landing-zones` (or equivalent
  org/account structure), `<vendor>-security-checklist`, `<vendor>-identity`,
  `<vendor>-naming-tagging` — each extending the generic `iac-expert` skill
  with vendor specifics.
- Optional `<vendor>-builder`/`<vendor>-reviewer` agents.
- All artifact names prefixed with the vendor slug to avoid collisions.
- A `STARTER_COLLECTIONS` entry per vendor.

## Verification

- `cd backend && pytest` — seeding path (`test_starter_collections.py` if it
  exists, else the seed/scan tests) still green; new collection parses with
  zero YAML errors.
- Run the rule-29 collision grep across `collections/` — no name reuse
  between `azure` and `iac-expert`/base collections.
- Boot the backend (or run `seed_starter_collections()` against a test DB)
  and confirm the `azure` collection seeds with the expected artifact count.
- `cd backend && ruff check . && mypy app` — clean (no Python changes
  expected beyond the registry dict, but confirm).

## Decisions (resolved)

- **Skills-only.** The Azure collection ships no agents; it reuses
  `iac-expert`'s `iac-builder`/`iac-reviewer` and adds Azure skills only.
- **Terraform emphasis, Bicep-aware.** Rules are tool-agnostic but written
  with Terraform as the primary worked example (the `azurerm` provider),
  with explicit notes on how the same rule maps to Bicep/ARM where they
  differ. This reflects that most teams use Terraform while Microsoft's
  recommended path is Bicep — the collection must be fluent in both.
- **CAF governance essentials.** The `azure-caf-landing-zones` skill covers
  management-group hierarchy, subscription design, RBAC scoping, Azure
  Policy guardrails, and network topology — not the full landing-zone
  accelerator (referenced, not reproduced).
- **Scaleway.** Follows the same template but lighter-weight: no separate
  WAF/landing-zone split (Scaleway has no WAF/CAF equivalent), folded into
  a single `scaleway-architecture` skill plus security/naming/identity
  skills. Deferred until the Azure instance proves the template.

## Open questions

- None blocking. Remaining follow-ups (AWS/GCP/Scaleway collections) are
  tracked in step 5's template and are out of scope for the Azure first
  pass.
