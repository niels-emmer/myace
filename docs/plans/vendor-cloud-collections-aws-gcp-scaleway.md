# Plan: Vendor Cloud Collections — AWS, Google Cloud, Scaleway

## Status

**In progress — AWS done, GCP and Scaleway pending.** Executable follow-up to
the Azure first pass (merged via PR #127). Builds the remaining vendor
collections using the established template from
`docs/plans/vendor-cloud-collections.md` step 5, following the same workflow
and governance as the Azure work. Research for all three providers is baked
into this plan so execution needs no re-research.

- **AWS** (`collections/additional/aws/`) — complete (AGENTS.md + 5 skills,
  registered in `STARTER_COLLECTIONS`, README count updated). Shipped via
  PR #___.

## Decisions (inherited from the Azure pass, apply to all three)

- **Skills-only** — no per-vendor agents; reuse `iac-expert`'s
  `iac-builder`/`iac-reviewer`.
- **Terraform emphasis, provider-native-aware** — rules tool-agnostic but
  written with the `terraform` provider as the primary worked example, with
  explicit notes on provider-native IaC where it differs (AWS CloudFormation/
  CDK, GCP Deployment Manager, Scaleway has no native IaC — Terraform/OpenTofu
  is the path).
- **Governance essentials** — cover the org/account/project structure and
  guardrails, not the full landing-zone accelerator.
- **Scaleway is lighter-weight** — no WAF/CAF split (it has neither); folded
  into a single architecture skill plus security/naming/identity skills.
- **Naming-collision discipline (rule 29)** — every artifact name prefixed
  with the vendor slug (`aws-`, `gcp-`, `scaleway-`) so nothing collides with
  `iac-expert` or the base collections when composed.

## Research summary (grounded, current as of Aug 2026)

### AWS
- **Well-Architected Framework — 6 pillars**: Operational Excellence,
  Security, Reliability, Performance Efficiency, Cost Optimization,
  Sustainability.
- **Cloud Adoption Framework (CAF) — 6 perspectives**: Business, People,
  Governance, Platform, Security, Operations. (Governance/Platform/Security
  are the ones that map to IaC content.)
- **Org structure**: AWS Organizations — organizational units (OUs), Service
  Control Policies (SCPs), account structure (management + workload accounts).
- **Identity**: IAM roles/policies, least privilege, identity federation
  (IAM Roles Anywhere, OIDC federation for GitHub Actions).
- **Security**: Security Hub, GuardDuty, Config, CloudTrail, VPC security
  groups/NACLs, KMS, Secrets Manager.
- **Naming/tagging**: AWS resource naming conventions, tags (owner,
  cost-center, environment, workload), cost-allocation tags.
- **Terraform**: `aws` provider; remote state S3 + DynamoDB locking.

### Google Cloud
- **Architecture Framework — 6 pillars**: Operational Excellence, Security/
  Privacy/Compliance, Reliability, Cost Optimization, Performance
  Optimization, Sustainability.
- **Cloud Adoption Framework (GCAF) — 4 themes**: Learn, Lead, Scale, Secure.
- **Resource hierarchy**: Organization → Folders → Projects → Resources; IAM
  at each level.
- **Identity**: IAM roles, service accounts, workload identity federation
  (Workload Identity Federation for GitHub Actions).
- **Security**: Security Command Center, Cloud Armor, VPC firewall rules,
  Cloud KMS, Secret Manager.
- **Naming**: GCP naming conventions, **labels** (not tags), resource
  hierarchy.
- **Terraform**: `google` provider; remote state GCS + locking.

### Scaleway (lighter-weight)
- **No WAF/CAF equivalent** — no pillar/adoption framework to map to.
- **Org structure**: Organization → Projects; IAM, billing, support at
  Organization level.
- **Identity**: IAM policies (permission sets bound to a scope — Project or
  Organization), principals (user/group/application), API keys for
  applications, MFA, identity federation (OAuth2/SAML SSO).
- **Security**: security groups (virtual firewalls on the public interface),
  private networks, VPC, WAF edge protection.
- **Naming**: Scaleway naming conventions, tags.
- **Terraform**: `scaleway` provider; remote state (S3-compatible Object
  Storage + locking).

## Proposed approach

### Phase 0 — Preflight (once, before any collection)

- [ ] Confirm `main` is clean and up to date (`git checkout main && git pull`).
- [ ] Confirm the `backend/.venv` from the Azure pass still works
      (`.venv/bin/pytest --version`); reinstall `.[dev]` if not.
- [ ] Re-read `docs/plans/vendor-cloud-collections.md` step 5 (the template)
      and the Azure collection (`collections/additional/azure/`) as the
      reference implementation.

### Phase 1 — AWS collection (`collections/additional/aws/`)

**`AGENTS.md`** — AWS standing rules:
- AWS Organizations / CAF governance: OU hierarchy, SCP guardrails, account
  structure (management vs. workload accounts).
- Identity: IAM roles, least privilege, identity federation (IAM Roles
  Anywhere / OIDC) over long-lived access keys.
- Security: Security Hub/GuardDuty/Config posture, VPC security groups/NACLs,
  private subnets, KMS, Secrets Manager.
- Cost: cost-allocation tags, Cost Explorer, reserved instances/savings plans
  where load warrants.
- WAF: map changes to the 6 AWS WAF pillars.

**`skills/`** (each a `SKILL.md`, names prefixed `aws-`):
- `aws-waf-review/SKILL.md` — AWS WAF 6-pillar checklists naming real AWS
  constructs (AZs, multi-AZ, S3 versioning, CloudWatch, etc.).
- `aws-caf-landing-zones/SKILL.md` — CAF governance essentials: OU hierarchy,
  SCPs, account design, IAM scoping, VPC topology (multi-AZ, private subnets,
  NAT, VPC endpoints), guardrails.
- `aws-security-checklist/SKILL.md` — AWS-recommended security practices as a
  PASS/FAIL/N/A gate (identity, network, data, monitoring/posture).
- `aws-identity/SKILL.md` — IAM roles, policies, least privilege, identity
  federation; avoiding long-lived access keys.
- `aws-naming-tagging/SKILL.md` — AWS naming convention + mandatory tags
  (owner, cost-center, environment, workload, managed-by), cost-allocation
  tags.

### Phase 2 — Google Cloud collection (`collections/additional/gcp/`)

**`AGENTS.md`** — GCP standing rules:
- Resource hierarchy / GCAF: Organization → Folders → Projects, IAM at each
  level, guardrails.
- Identity: IAM roles, service accounts, workload identity federation over
  long-lived service-account keys.
- Security: Security Command Center posture, VPC firewall rules, Cloud Armor,
  Cloud KMS, Secret Manager.
- Cost: labels for cost attribution, committed-use discounts where load
  warrants.
- WAF: map changes to the 6 GCP Architecture Framework pillars.

**`skills/`** (names prefixed `gcp-`):
- `gcp-waf-review/SKILL.md` — GCP Architecture Framework 6-pillar checklists
  naming real GCP constructs (regions/zones, managed instance groups,
  Cloud Monitoring, etc.).
- `gcp-landing-zones/SKILL.md` — GCAF governance essentials: resource
  hierarchy, folder/project design, IAM scoping, VPC topology (shared VPC,
  firewall rules, Cloud NAT, Private Service Connect), guardrails.
- `gcp-security-checklist/SKILL.md` — GCP-recommended security practices as a
  PASS/FAIL/N/A gate.
- `gcp-identity/SKILL.md` — IAM roles, service accounts, workload identity
  federation; avoiding long-lived service-account keys.
- `gcp-naming-tagging/SKILL.md` — GCP naming convention + mandatory **labels**
  (owner, cost-center, environment, workload, managed-by).

### Phase 3 — Scaleway collection (`collections/additional/scaleway/`)

**Lighter-weight** — no WAF/CAF split. **`AGENTS.md`** + 3 skills:

**`AGENTS.md`** — Scaleway standing rules:
- Organization → Project structure; IAM at Organization vs. Project scope.
- Identity: IAM policies (permission sets), applications + API keys,
  least privilege, MFA, identity federation (OAuth2/SAML).
- Security: security groups (virtual firewalls), private networks, VPC.
- Cost: tags for cost attribution.

**`skills/`** (names prefixed `scaleway-`):
- `scaleway-architecture/SKILL.md` — the single architecture skill (replaces
  the WAF/landing-zone split): org/project structure, IAM scoping, VPC/private
  network topology, security groups, guardrails.
- `scaleway-security-checklist/SKILL.md` — Scaleway-recommended security
  practices as a PASS/FAIL/N/A gate.
- `scaleway-naming-tagging/SKILL.md` — Scaleway naming convention + mandatory
  tags.

### Phase 4 — Registration & docs (per collection, or batched)

- [ ] Add each vendor to `STARTER_COLLECTIONS["additional"]` in
      `backend/app/services/seed_collections.py` (category `Infrastructure`).
      Suggested names: "AWS Cloud Architect", "Google Cloud Architect",
      "Scaleway Cloud Architect".
- [ ] Update `README.md` starter-pack count (13 → 16) and the specialization
      list.
- [ ] Update `docs/plans/vendor-cloud-collections.md` status to reflect each
      completed vendor.

### Phase 5 — Verification (per collection)

- [ ] **Collision grep** (rule 29): `grep -rn "^name:" collections/*/*/skills/*/SKILL.md`
      — confirm no vendor skill name collides with any existing artifact.
- [ ] **YAML parse**: validate every new SKILL.md frontmatter
      (name/description/version/priority/compatibility/tags) via the scanner's
      `_parse_skill_file` path.
- [ ] **Registry/disk match**: every `collections/additional/<vendor>/` dir has
      a `STARTER_COLLECTIONS` entry and vice versa.
- [ ] **`pytest`**: `cd backend && .venv/bin/pytest` — full suite green
      (incl. seeding path).
- [ ] **`ruff`**: `.venv/bin/ruff check .` — clean.
- [ ] **`mypy`**: `.venv/bin/mypy app` — error count must equal the `main`
      baseline (129), no new errors. Compare via `git worktree add`.

### Phase 6 — Review & ship (per collection)

- [ ] Run `@security-auditor` on the collection content (guidance soundness,
      no secrets, no insecure configs taught).
- [ ] Run `@reviewer` for regression/risk (collisions, cross-references,
      docs sync). If it loops, complete the checks manually as in the Azure
      pass.
- [ ] Create a feature branch per vendor (`feat/aws-cloud-collection`, etc.),
      commit with conventional commits, push, open a PR with the pr-standards
      template.
- [ ] Confirm CI passes (Backend, CLI, Docker, Frontend) via `gh pr checks`.
- [ ] Merge, sync `main`, delete the feature branch (local + remote).

## Sequencing

- **One PR per vendor** keeps each review focused and each merge independent
  (matches the Azure precedent). Order: **AWS → GCP → Scaleway** (AWS and GCP
  are the full 5-skill template; Scaleway is the lighter 3-skill variant, so
  it's quickest last).
- Each vendor is independently shippable — a failure in one doesn't block the
  others.

## Verification of the plan itself

- The plan is executable as written: every phase has concrete file paths,
  skill names, and check commands.
- Research is grounded in current (Aug 2026) provider documentation and baked
  in, so no re-research is needed during execution.

## Open questions

- **Batch vs. per-vendor PRs** — default is per-vendor (recommended). If the
  user prefers a single combined PR, the phases still apply, just batched.
- **Scaleway depth** — the lighter 3-skill variant is the default per the
  earlier decision. Confirm it's not too thin before shipping.
- **GCP pillar count** — official docs list 6 pillars (incl. Sustainability);
  some third-party sources say 5. Use the official 6.
