# Add-on pack quality audit

> **Status: Phase 1 complete (read-only audit). Phase 2 decisions pending.**
> Audited 2026-11-28 on branch `audit-by-claude-addon-audit`, against the
> checkout at `main` (c8057b1). All 24 packs in `collections/additional/` were
> read in full (every rule, agent, skill and command). Compiled output via MCP
> `download_pack` was **not** sampled this round (see "Could not verify").
> No pack content was edited. Ratings and verification dates were not touched.

## 1. Headline

The add-ons are consistently written, safe in tone, and mostly useful. The
problems are systemic rather than per-pack:

1. **None of the 24 add-ons carries the governance conventions the base packs
   got in 2.2.0**: no rule priority/tag tiers (0 of ~120 rules), no
   `permissions: {edit: deny}` on any of the ~14 "strictly read-only" reviewer
   agents (the posture is prose only, so it is not enforced and no adapter
   emits it), and no no-subagent fallback sentence in any handoff.
2. **Handoffs to base agents (`verifier`, `security-auditor`, `code-reviewer`)
   resolve only on Software Engineer / DevOps bases.** `ai-engineering` and
   `eu-ai-act` hand off to them; on a Data Scientist or Vibecoder base they dangle
   (`dangling_handoff` warning).
3. **Large content duplication**: the four cloud packs are ~75% one template;
   `backend` and `database` repeat each other nearly verbatim; `devops` repeats
   the DevOps base pack; `auditor/ai-governance` repeats
   `enterprise-ai-governance`; `qa-testing` repeats Testing Discipline in three
   places. Always-loaded rules pay for every copy.
4. **One governance contradiction**: `dev-writing` teaches the agent to make
   text "read as typed by a person rather than generated", while
   `enterprise-ai-governance`, `auditor`, `git-practices` and
   `self-hosted-deploy` require marking AI authorship. Composed, they conflict.
5. **Currency**: factual errors or stale facts in `android-developer`,
   `ios-developer`, `auditor`, `aws`, `azure`, `gcp`, `scaleway`, `java-spring`
   and `eu-ai-act` (details below, each dated and sourced).
6. **Dependent packs have no dependency mechanism**: `aws/azure/gcp/scaleway`
   reference `iac-expert` skills by name (`exception-documentation`,
   `resource-naming`, ...); `docker-patterns` references `container-build`
   (devops pack); `new-app-scaffold` references `self-hosted-app` and a
   "repository-publication checklist" that exists nowhere. Without the other
   pack these are dangling prose references.

Mechanical facts (script-verified): no name collisions between any two add-ons;
no add-on/base artifact-name collision exists either (skill names come from
frontmatter: git-practices "Git Workflow Discipline" vs vibecoder "Git Workflow";
a first draft that compared directory names reported a false collision). The
only same-name artifacts are the base-pack generated pairs. All agent `handoff_to` names that point
inside the pack resolve. All 122 add-on files list the same 11-framework
`compatibility` (no `pi`; identical to base, so not add-on specific).

## 2. Grades

A = ship as is, B = minor fixes, C = needs real fixes, D = misleading or unsafe
as written.

| Pack | Grade | One-line reason |
|---|---|---|
| ai-engineering | C | thin (1 skill, no eval/RAG skill), MyACE-specific wording leaks, dangling base handoffs |
| android-developer | C | several factual errors in rules (LiveData, modifier order, `@Composable` classes), stale Play target |
| auditor | C | two conflicting classification schemes, 2021 OWASP IDs, overlaps enterprise-ai-governance |
| aws | C | "CAF" mislabel, SCP/NACL inaccuracies, OIDC trust without `sub` condition |
| azure | B | accurate framework use; tag-inheritance claim wrong |
| backend | B | solid; duplicates `database`; Alembic-specific wording |
| database | B | solid; duplicates `backend`; no backup/restore, engine specifics |
| design-and-scaffold | B | good; `scout` missing posture/handoff; dangling references |
| dev-writing | D | governance conflict (AI-authorship disguise); also narrow, always-loaded stylistic rules |
| devops | C | mostly redundant on DevOps base; scope creep (PR/release); garbled "fix forward" wording; no supply-chain |
| editor | A- | best-written add-on; minor portability naming |
| enterprise-ai-governance | B | good; absolute REGULATED rule is policy not fact; overlaps auditor |
| eu-ai-act | C | internal date contradictions; Art 50(2) grace period missing; strong otherwise |
| frontend | B | concise; rule/skill duplication; no WCAG version |
| fullstack | C | overlaps frontend+backend; conflicts with qa-testing on retries; stack-specific wording |
| gcp | C | stale framework name; wrong org-policy constraint names |
| git-practices | C | silent override of vibecoder `git-workflow`; release command pushes to default branch |
| iac-expert | B+ | good core; missing version pinning, deletion protection, policy-as-code |
| ios-developer | C | teaches pre-iOS-17 state management only; stale screenshot sizes |
| java-spring | C | no Spring Security; dubious `@Cacheable`/lockfile claims |
| qa-testing | B | good; heavy redundancy with base Testing Discipline |
| scaleway | C | tag model and billing-unit assumptions unverified/wrong; 3 skills only |
| self-hosted-deploy | B | narrow archetype under a generic name; dangling reference |
| spec-driven-dev | B | good pipeline; rule text is long and leaks "MyACE" |

## 3. Cross-pack findings

### 3.1 Systemic convention gaps (all 24 packs) — severity: high

| # | Finding | Evidence | Fix |
|---|---|---|---|
| X1 | No rule priority/tags | 0 `<!-- myace: -->` markers in any add-on `AGENTS.md` | add tiers (90 safety/security, 70 quality gates, 50 process) |
| X2 | Read-only reviewers lack `permissions: {edit: deny}` | `mech.py`: perms=None on every add-on agent incl. `*-reviewer`, `scout`, `context-manager`, EU classifier/reviewer/writer, `api-reviewer`, ... | add the frontmatter key (rule 43; restrict-only, safe) |
| X3 | No-subagent fallback sentence | `grep "no subagents"` over add-ons: 0 hits | add to every Handoff section |
| X4 | Base-agent handoffs only resolve on SE/DevOps | ai-engineering, eu-ai-act (`security-auditor`) | document the requirement, or add a pack-local fallback |
| X5 | Soft dependency on other add-ons undocumented/unenforced | cloud packs -> iac-expert; docker-patterns -> container-build; new-app-scaffold -> self-hosted-app | state "requires X" in the description; make skills degrade gracefully |
| X6 | Two agents' postures use mixed formats | `design-and-scaffold/scout`, `git-practices/github` have no Permission posture/Handoff sections | add |

### 3.2 Overlap matrix (✱ = significant duplicated content)

| | iac-expert | devops | backend | database | qa-testing | auditor | enterprise-ai-gov | eu-ai-act |
|---|---|---|---|---|---|---|---|---|
| aws/azure/gcp/scaleway | ✱ (shared template + generic copy) | | | | | | | |
| devops | partial (apply gate) | — | | | | | | |
| backend | | | — | ✱ (rollback rule, constraints rule, idempotency) | partial | | | |
| qa-testing | | | partial (backend-test-patterns) | | — | | | |
| auditor | | | | | | — | ✱ (classes, routing, attribution) | partial |
| fullstack | | | ✱ (error states, contract) | | ✱ (E2E) | | | |
| dev-writing | | | | | | | **conflict** (attribution) | |

Also: `devops` add-on vs **base devops-engineer** (Immutable & Reproducible,
DevSecOps, Observability By Default, Incident Response Rigor, pipeline/image/
observability/incident skills): different names, so no collision, but the
content is duplicated; on a DevOps base it adds little. `qa-testing` flakiness
rule appears in the rule, in `test-automation`, and in `test-builder` posture;
Testing Discipline in SE/DevOps repeats the rest.

### 3.3 Composition conflicts

- **C1 (high) AI-authorship conflict.** `dev-writing` (rules *Write The Way A
  Person Types*, skill `developer-voice`: "reads as typed by a person rather
  than generated", avoid "stock vocabulary that reads generated") vs
  `enterprise-ai-governance` *Attribute AI-Authored Changes*, `auditor/ai-governance`
  (`[ai]` marker), `git-practices` precommit ("AI-authorship marker"),
  `self-hosted-deploy` ("mark AI authorship in the commit body"). Three
  slightly different marker conventions exist (`[ai]` prefix in body; "marker
  in body"; "AI-authored" in PR line) on top of that.
- **C2 (med) retries.** `fullstack/end-to-end-testing`: "retry on transient
  failures"; `qa-testing` rule and `test-builder`: never retry flaky tests.
- **C3 (med) data classes.** `auditor` uses 3 tiers in the rule and
  `data-classification-guide` (public/internal/sensitive) and 4 classes in
  `ai-governance` (PUBLIC/INTERNAL/CONFIDENTIAL/REGULATED);
  `enterprise-ai-governance` uses the 4. The auditor rule says sensitive data
  "must never reach LLM prompts"; the guide says "no, unless the tool is
  approved".
- **C4 (med) git workflow.** git-practices `Git Workflow Discipline` ("never
  directly on the default branch") vs vibecoder `Git Workflow` ("fine to push
  directly"): different names so both ship, with contradictory advice when
  composed. `git-practices/release` itself commits
  the changelog and pushes the default branch directly, contradicting its own
  rule and any protected-branch policy (this repo's rule 7).
- **C5 (low) agent sprawl.** frontend+backend+fullstack(+database) composed give
  6-8 builder/reviewer agents with overlapping remit and no routing between
  them; every add-on pair hands off only to its own twin.

### 3.4 seed_collections.py

Categories/descriptions are coherent. `design-and-scaffold`, `git-practices`,
`qa-testing`, `spec-driven-dev` share "Process & Methodology", `dev-writing`
and `editor` "Documentation". `dev-writing` is categorised Documentation but is
really a text-voice/disguise tool (see C1). Not checked against live ratings
(by design).

## 4. Per-pack findings

Severity: **H** wrong/unsafe/misleading, **M** stale or inconsistent,
**L** polish. Paths are under `collections/additional/`. Line references are
omitted where the finding is a whole-file property; rule/skill names are exact.

### 4.1 ai-engineering — C
- M `agents/*`, `skills/agent-design-principles`: "this repo's `orchestrator`
  -> `builder` -> `verifier`", "this collection's", "MyACE-style artifacts"
  (prompt-engineer) leak the product and a specific pipeline into portable text.
- M handoffs `verifier`, `security-auditor`, `code-reviewer` dangle on DS/Vibecoder bases (X4).
- M scope: *Prompt Changes Need Evals* is a rule but there is no eval skill;
  nothing on prompt-injection beyond one paragraph, RAG, tool-calling
  permissions, cost/latency. 1 skill for 3 rules.
- L `context-manager` says "never edit source code" but declares no deny.
- Attribution: 12-factor-agents is Apache-2.0 for **code** and CC BY-SA 4.0
  for **content** per its README (secondary sources, see 6). The pack cites only
  Apache-2.0 and paraphrases; if text is adapted, ShareAlike may apply.

### 4.2 android-developer — C (community)
- **H** *Lifecycle Awareness*: "`collectAsStateWithLifecycle()` for a Flow or
  LiveData" — that API is for Flow/StateFlow; LiveData uses `observeAsState()`.
- **H** *Jetpack Compose-First*: "prefer composable functions over custom
  `@Composable` classes" — there are no `@Composable` classes; meaningless.
- **H** `jetpack-compose-conventions`: modifier order "size/position, padding,
  visual, then clickable" is wrong as a rule: order is semantic;
  `clickable` before `padding` is the usual way to include padding in the touch
  target; `background` vs `padding` order changes what is painted.
- M rule says `mutableStateOf` in ViewModels; `android-builder` says
  `StateFlow` (inconsistent; current guidance is StateFlow +
  `collectAsStateWithLifecycle`).
- M `NetworkBoundResource` is a 2018 sample pattern, not a library; fine as
  an idea, misleading as a named API.
- M `play-store-readiness`: `targetSdkVersion`/`compileSdkVersion` are the
  legacy Gradle names (`targetSdk`/`compileSdk`); "latest within one year" is
  vague. Verified 2026-11-28: new apps and updates must target Android 16 (API
  36) as of 2026-08-31; Wear OS/Auto API 35, TV/XR API 34 (see 6).
- M `android-testing`: Robolectric for ViewModel tests is unnecessary (plain
  JVM); "every composable previews default/empty/error" is overkill.
- L missing: DI (Hilt), navigation, Keystore/network security config, R8,
  accessibility, Play Data Safety form, edge-to-edge. X1-X3.

### 4.3 auditor — C
- M `security-audit-checklist` cites OWASP **A03:2021 Injection** and A01:2021.
  OWASP Top 10:2025 exists: Broken Access Control still A01 (SSRF merged in),
  Injection moved down, Software Supply Chain Failures is A03, Mishandling of
  Exceptional Conditions is A10 (owasp.org + secondary, see 6). Cite the
  version or drop the number.
- M C3 above (3 vs 4 classes; absolute vs conditional prompt rule).
- M `ai-governance`: "REGULATED: local models only, no exceptions" and lists
  "SOC2-scoped" as a data class; this is policy preference stated as fact and
  ignores BAA/EU-region enterprise endpoints. Duplicates enterprise-ai-governance.
- L `compliance-reviewer` <-> `security-compliance-auditor` ping-pong with no
  terminal condition; both lack deny.
- Good: redaction instruction in `secrets-scan-checklist`; PASS/FAIL/N/A shape.

### 4.4 aws — C
- **H** *AWS Governance By Design (CAF)* / `aws-caf-landing-zones`: AWS CAF is a
  perspective-based organisational framework (Business, People, Governance,
  Platform, Security, Operations). OU/account/SCP design comes from AWS multi-account
  guidance ("Organizing your AWS environment", Security Reference Architecture,
  Control Tower). The label looks transplanted from Azure CAF.
- **H** safety gap: GitHub OIDC federation is recommended with no mention of
  constraining `token.actions.githubusercontent.com:sub` (and `aud`) in the role
  trust policy; an unconstrained trust lets other repos assume the role. AWS and
  GitHub docs call this out (verified, see 6). Also new repos from 2026-07-15
  may use an immutable-ID `sub` format.
- M SCPs "deny public S3 buckets": an SCP cannot do this directly; use S3 Block
  Public Access and an SCP that prevents changing it. "NACLs default to deny":
  false for the default NACL (allow all). "workload VPCs that peer to hub": hub-
  spoke uses Transit Gateway (peering is non-transitive).
- M human access leads with "IAM users with MFA"; current guidance is federation
  / IAM Identity Center.
- L checklist missing: root MFA/no root keys, IMDSv2, EBS default encryption,
  KMS key policy, IAM Access Analyzer.
- No agents, so no apply gate in the pack (relies on iac-expert; X5).

### 4.5 azure — B
- M `azure-naming-tagging`: "apply tags at the resource group level so they
  inherit" — Azure tags do not inherit from RG by default; use Azure Policy
  *Inherit a tag from the resource group* (Modify effect; new/updated resources
  only until remediated) (verified, see 6). The pack's own "DeployIfNotExists
  for tags" is also the wrong effect.
- L `sql` vs CAF `sqldb`/`sql` server distinction. WAF five pillars, Entra,
  hub-spoke, PIM, workload identity federation are correct.

### 4.6 gcp — C
- M framework named "Google Cloud Architecture Framework"; Google now calls it
  **Well-Architected Framework** and, since 2026-01-28, lists sustainability as
  a full pillar (verified, see 6). The "GCAF" label and the landing-zone content
  (really the Enterprise foundations blueprint) are two different things.
- **H** `gcp-landing-zones`: "deny `iam.serviceAccountKeys.create`" is an IAM
  permission, not an org-policy constraint; use `iam.disableServiceAccountKeyCreation`
  or the managed `iam.managed.disableServiceAccountKeyCreation`. "Deny disabling
  Cloud Audit Logs" has no such constraint (Admin Activity logs cannot be
  disabled; Data Access logs are an IAM audit config).
- M "Cloud Foundation Toolkit" status (archived/superseded?) not verified.
- L PSC example lists GKE as a Google-managed service; region segment
  `us-central1` blows the 30-char service-account ID budget.

### 4.7 scaleway — C (community)
- M tags are described as key/value; Scaleway resource tags are plain strings
  (a `key=value` convention is user-made); a separate Annotations feature has
  real keys (conflicting sources, see 6). The mandatory-tag table needs an
  explicit `owner=<x>` encoding statement.
- M carried-over "cost attribution belongs to tags, not project boundaries":
  on Scaleway the Project is the billing/cost grouping; unverified whether tag
  roll-up exists. Reword or verify.
- Verified: SAML SSO exists (Owner excluded); Edge Services WAF exists
  (OWASP CRS, **public beta**, Object Storage/Load Balancer backends only).
  The rule says WAF is "part of the baseline" - overclaims for a beta feature.
- L only 3 skills; rule "Identity" points at `scaleway-architecture` which has
  no identity-federation section.

### 4.8 cloud packs (aws/azure/gcp/scaleway) together
- M ~75% shared prose across four packs; generic parts also exist in
  `iac-expert`. Candidates: move generic text into iac-expert, or generate the
  four from one template (like `_shared/`).
- M all packs say "Compose with iac-expert"; nothing enforces it (X5).

### 4.9 iac-expert — B+
- M missing: provider/module version pinning, saved-plan-equals-applied-plan,
  deletion protection/`prevent_destroy` for stateful resources, drift
  detection, policy-as-code (OPA/Checkov/Trivy), state encryption/versioning.
- M `well-architected-review` says "Google Cloud's architecture framework" (stale name).
- L `.tf` bias in examples. `iac-reviewer` has no edit deny (X2).

### 4.10 devops — C
- M duplicates base devops-engineer (3.2); no add-on value on that base.
- **M** *Incident Response Discipline*: "Fix forward, then fix backward: restore
  service first (rollback...)" mislabels rollback as "fix forward"; *Release
  Gates* says "rollback must be faster than fix-forward". Reword.
- M `pr-standards` and `release-engineering` are git-practices territory (scope
  creep) and prescriptive ("at least one approving review").
- M missing supply chain: pin third-party Actions to SHAs, least-privilege
  `GITHUB_TOKEN`, OIDC to cloud, SBOM/provenance/signing, OpenTelemetry named.

### 4.11 self-hosted-deploy — B
- M name/description are generic but the content is one archetype (single
  container + SQLite + single maintainer, CODE_OF_CONDUCT in skeleton).
  Rename or reword description to say so.
- M `docker-patterns` -> `container-build` dangling without devops (X5).
- L example `postgres:16-alpine`; `restart: always`. Good: confirm-before-prune,
  backup-before-recreate.

### 4.12 backend / database — B each
- M duplication: *Every Schema Change Needs A Working Rollback* == *Migrations
  Must Roll Back* (same sentences), constraints rule, idempotency text, near
  identical agent postures. Merge or have `backend` reference `database`.
- M `downgrade()` is Alembic vocabulary in rule text.
- L missing (backend): authN/Z, pagination, rate limiting, timeouts/retries,
  OWASP API Top 10. (database): backup/restore tests, pooling, engine specifics
  (`CREATE INDEX CONCURRENTLY`, `lock_timeout`), PII/retention.

### 4.13 frontend — B / fullstack — C
- frontend M: two rules repeated verbatim in `component-conventions`; a11y
  checklist names no WCAG version (2.2 AA: target size, focus not obscured);
  React-isms. Missing XSS/CSP, performance, forms, component testing.
- fullstack M: "Pydantic models and TypeScript interfaces" in a portable rule;
  overlaps (C5); C2 conflict; custom error envelope without mentioning RFC 9457.

### 4.14 qa-testing — B
- M 3-way repetition of flaky/regression/level rules; overlaps base Testing
  Discipline. Missing property/mutation/contract/perf/security testing.

### 4.15 ios-developer — C (community)
- **M (high currency)** teaches `ObservableObject`/`@StateObject`/`@ObservedObject`/
  `@EnvironmentObject` only. Apple documents the Observation framework
  (`@Observable`, iOS 17+) and a migration guide; not mentioned.
- M XCTest only (Swift Testing absent); no Swift concurrency; "preview provider"
  vs `#Preview`.
- M `app-store-readiness`: screenshot sets "6.7", 6.5", 5.5"" are stale; 6.9"
  (1320x2868) is the baseline, 6.5" only needed if no 6.9" set (verified
  against secondary sources; Apple's own page not fetched, see 6). SDK
  requirement not verified.

### 4.16 java-spring — C
- M `@Cacheable` "on repository methods, not services": unsourced/contested.
- M "avoid component scanning for production-critical beans": odd for Spring Boot.
- **M** "lockfiles (Maven Enforcer)": Enforcer rules are convergence checks, not
  lockfiles (not verified against a source; see 6). Gradle dependency locking is real.
- M no Spring Security rule, no Testcontainers/`@ServiceConnection`, no
  Boot/Java baseline, Actuator/Micrometer, Flyway/Liquibase.

### 4.17 git-practices — C
- M C4 (contradicts vibecoder advice when composed; release command pushes default branch).
- L rule *Never Commit Secrets* duplicates base *Secrets And Destructive Actions*.
- Good: `github` agent confirms repo/auth first, merges only when authorised.

### 4.18 design-and-scaffold — B
- M `scout` has no Permission posture/Handoff and no deny; overlaps SE
  *Dependency Hygiene* (rule duplicate). `new-app-scaffold` references
  `self-hosted-app` and a non-existent "repository-publication checklist".
- L "AGENTS.md ... the only artifact a fresh agent reads" (Claude Code reads CLAUDE.md).

### 4.19 spec-driven-dev — B
- M both rules are ~1KB each of always-loaded prose; move the guidance into the
  commands/skill and keep a 2-line rule. Rule text says "MyACE's plain-markdown
  command format". spec-kit is MIT (not re-verified).

### 4.20 enterprise-ai-governance — B
- M *Keep A Zero-Egress Path*: "REGULATED never goes to a cloud model,
  regardless of provider terms" is a policy default stated as an invariant;
  make it configurable or say "unless the project documents an exception".
- M overlaps `auditor/ai-governance` (3.2). Good: guardrails skill is concrete;
  protected-target list; confirmation not carried over.

### 4.21 dev-writing — D
- **H** C1. Purpose is making AI-authored text indistinguishable from human
  text under a person's name. Conflicts with the product's governance purpose
  and with the attribution rules above. Honest alternatives: keep as a plain
  *style* guide (brevity, no filler, no invented events) without the
  "reads as typed by a person / avoid words that read generated" framing, or
  make it explicitly opt-in and document the conflict.
- M five always-loaded rules for pure style (em dash ban etc.) are the owner's
  taste, not a team default; should be a skill, not rules.
- Good: *Never Invent An Event* is a real integrity rule.

### 4.22 editor — A-
- L names `CLAUDE.md` alongside `AGENTS.md` (fine); `docs-editor` is "lean
  read-only" (correct, it may make small edits). Best-structured pack;
  `writing-for-agent-readers` is the highest-value skill in the set.

### 4.23 eu-ai-act — C (community)
- M internal contradictions: `eu-ai-act-high-risk-obligations` says Art 49
  registration "applies from 2 Aug 2026", while classification skill and
  classifier agent say Annex III high-risk obligations apply from **2 Dec 2027**
  (Omnibus). Registration of Annex III systems follows the deferred date.
- L Art 50(2) machine-readable marking has a grace period to **2 Dec 2026**
  for generative systems already on the market before 2026-08-02. The
  transparency skill already says so; the `AGENTS.md` rule and the timeline
  line did not (corrected in the factual branch). Verified from law-firm
  commentary only; confirm against the Official Journal text (sources cite
  Regulation (EU) 2026/1744, in force 2026-07-27, unverified).
- L cite regulation number of the Omnibus once confirmed; FRIA is Art 27, not 26.
- Good: legal-advice disclaimers; "never write we are compliant".

## 5. Prioritised fix list (proposal; none applied)

**P1 - correctness/safety (do first)**
1. Fix the factual errors: android rules (LiveData, `@Composable` classes,
   modifier order), gcp org-policy names, aws OIDC `sub`/`aud`, aws "CAF" label
   + SCP/NACL, azure tag inheritance, java-spring caching/lockfile, eu-ai-act
   date contradiction + Art 50(2) grace.
2. Resolve C1 (dev-writing vs attribution) per owner decision.
3. Add `permissions: {edit: deny}` to all read-only reviewers; add the
   no-subagent fallback sentence (X2, X3).
4. Fix git-practices `release` (PR flow); note the vibecoder contradiction.

**P2 - currency**
5. Update OWASP refs, ios Observation/Swift Testing/screenshot sizes, Play
   target API wording, GCP framework name, scaleway tags/billing/WAF-beta wording.

**P3 - structure/effectiveness**
6. Rule tiers on all add-ons (X1). Resolve data-class scheme (C3). Resolve
   duplication: backend/database, auditor/enterprise-ai-governance, cloud
   template, devops vs base, qa-testing.
7. Dependencies: state them in descriptions; make dangling references
   conditional ("if iac-expert is composed").
8. Gap-fill: ai-engineering eval/RAG/injection skills, java-spring security,
   iac-expert pinning/deletion protection, devops supply chain.

## 6. Sources and verification log (2026-11-28)

Verified against web sources (secondary where noted):
- EU AI Act Omnibus: Annex III high-risk -> 2 Dec 2027, Annex I -> 2 Aug 2028,
  Art 50(2) grace to 2 Dec 2026 for pre-existing systems, rest of Art 50 from
  2 Aug 2026. Secondary only: [Gibson Dunn](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/),
  [aiacto](https://www.aiacto.eu/en/blog/digital-omnibus-ai-act-report-2027),
  [Sigma Law](https://sigmalawgroup.com/blog/2026-07-26-eu-ai-act-article-50/).
- OWASP Top 10:2025 categories: [owasp.org](https://owasp.org/Top10/2025/0x00_2025-Introduction/),
  [The Register](https://www.theregister.com/2025/11/11/new_owasp_top_ten_broken/).
- Play target API 36 by 2026-08-31: [Android developers](https://developer.android.com/google/play/requirements/target-sdk).
- GCP Well-Architected Framework + sustainability pillar:
  [Google Cloud docs](https://docs.cloud.google.com/architecture/framework).
- Azure tag inheritance via Policy: [Microsoft Learn](https://learn.microsoft.com/azure/governance/policy/tutorials/govern-tags).
- GCP SA key constraint: [Google Cloud docs](https://docs.cloud.google.com/organization-policy/restrict-service-accounts).
- Scaleway SAML/WAF/tags: [SSO](https://www.scaleway.com/en/docs/iam/user-provisioning/set-up-identity-federation/),
  [WAF](https://scaleway.com/en/docs/edge-services/reference-content/understanding-waf),
  [tag example](https://www.scaleway.com/en/docs/instances/api-cli/tag-instances-hds-cli-api/).
- AWS CAF perspectives / multi-account: [AWS whitepaper](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/organizing-your-aws-environment.html).
- GitHub OIDC to AWS `sub`/`aud`: [GitHub docs](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws).
- SwiftUI Observation migration: [Apple docs](https://developer.apple.com/documentation/swiftui/migrating-from-the-observable-object-protocol-to-the-observable-macro).
- 12-factor-agents licence split (mirrors/summaries, not the repo): see search
  results; check the repo README.

### Could not verify (do not treat as confirmed)
- Apple's own screenshot-spec page and the Xcode/iOS SDK upload requirement.
- Official Journal text and number of the AI Act Omnibus; whether Art 49
  registration of Annex III systems is deferred in the final text.
- OWASP Top 10:2025 exact ranks A02-A09 (only some categories seen).
- Maven Enforcer vs lockfiles; `@Cacheable` placement guidance; Cloud Foundation
  Toolkit status; NIST SSDF version cited by auditor; Scaleway billing/tag
  roll-up; PG/Docker image currency; spec-kit licence; 12-factor-agents LICENSE
  files themselves.
- Compiled output via MCP `download_pack` (claude-code/opencode) was **not**
  sampled; findings are from source files only. Not run: pytest/ruff.

## 7. Owner decisions

Recorded 2026-11-28:

1. **dev-writing**: reframe as a plain style guide; drop the "reads as typed by
   a person / avoid words that read generated" framing; style rules become
   skills; keep a single integrity rule (*Never Invent An Event*).
2. **Duplication**: trim in place. Keep every pack and item name; remove
   verbatim duplicate rules and point to the canonical pack. No merges/renames.
3. **Conventions applied to all 24 add-ons**: `permissions: {edit: deny}` on
   read-only agents, no-subagent fallback sentence, rule priority/tag tiers,
   documented dependencies (conditional cross-pack references).
4. **Structure**: stacked local branches by theme, each with tests green:
   `audit-by-claude-addon-audit` (this report) ->
   `audit-by-claude-addon-factual` (P1) -> `...-addon-conventions` ->
   `...-addon-currency` -> `...-addon-dedup`.

## 8. Outcome (2026-11-28)

Stacked local branches (none pushed, no PR; owner merges):

| Branch | Content |
|---|---|
| `audit-by-claude-addon-audit` | this report + decisions |
| `audit-by-claude-addon-factual` | P1 factual/safety fixes, dev-writing reframed, git-practices release via PR |
| `audit-by-claude-addon-conventions` | rule tiers, `edit: deny`, no-subagent fallback, conditional dependencies, `test_addon_conventions.py` |
| `audit-by-claude-addon-currency` | iOS Observation/screenshots, OWASP edition, GCP name, Scaleway, wording |
| `audit-by-claude-addon-dedup` | trim-in-place overlaps, one AI-authorship marker, classification alignment |

Backend `pytest` (738) and `ruff` pass on every branch tip. CLI/MCP/frontend
suites were not run (no code in those components changed). Not run against a
real framework binary.

**Deliberately not done** (needs larger decisions or sources): rename of
`GCP Architecture Framework Pillar Review` skill and `... (CAF)` rule headings
(item names are identity); gap-fill skills (ai-engineering evals/RAG, java-spring
security, iac-expert pinning/deletion protection, devops supply chain, frontend
WCAG 2.2); de-templating the four cloud packs; java-spring `@Cacheable` and
Swift Testing claims remain unsourced; compiled-output sampling via MCP.

**Reconcile impact**: removed items (`dev-writing`: Write The Way A Person
Types, No Dashes And No Forced Contrast, Stop At The Last Point, Name Things
The Way People Do) are soft-deleted by `reconcile --apply`; all other changes
are content updates needing `--update-content`. Rule order changes for every
add-on (tiers). Counts for `dev-writing` drop from 7 to 3.

Estimated grades after: factual packs (android, aws, azure, gcp, java-spring,
git-practices, dev-writing, eu-ai-act) one step up (C->B, D->B); ios and
auditor C->B; the rest unchanged apart from convention compliance.
