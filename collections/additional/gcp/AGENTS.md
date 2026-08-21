# Google Cloud Architect

GCP-specific architecture and governance rules. This collection layers on the
vendor-agnostic `iac-expert` collection — it assumes the general IaC
invariants (private-by-default, managed identity over secrets, naming/tagging,
remote state with locking, approval-gated applies, documented exceptions,
well-architected pillar review) and adds the GCP-specific layer on top.
Compose it with `iac-expert` (and a base collection) in a profile.

## Governance By Design (GCAF)

Follow the Google Cloud Adoption Framework (GCAF) governance essentials: a
resource hierarchy (Organization → Folders → Projects) that separates platform
from workloads, projects scoped by environment/workload boundary, IAM assigned
at the narrowest effective scope, and Organization-policy guardrails that
enforce the invariants below rather than relying on convention. See the
`gcp-landing-zones` skill.

## Identity: IAM, Service Accounts, And Federation

Use IAM as the identity plane. Prefer service accounts and Workload Identity
Federation over long-lived service-account keys — never a long-lived secret
where a federated credential works. Scope IAM roles to least privilege; enable
MFA for human access. See the `gcp-identity` skill.

## Security By Default

Private networking and VPC isolation over public exposure. No public IP,
`0.0.0.0/0` firewall rule, or public GCS bucket without a documented exception.
Secrets live in Secret Manager, referenced by ID — never embedded. Security
Command Center posture and Organization-policy guardrails are part of the
baseline, not an afterthought. See the `gcp-security-checklist` skill.

## Cost Attribution

Every resource carries the mandatory labels (owner, cost-center, environment,
workload) so spend rolls up correctly in Cloud Billing. Size to actual load;
use committed-use discounts only where the workload's traffic pattern genuinely
warrants them.

## Map Changes To GCP Architecture Framework Pillars

Before shipping nontrivial GCP changes, note which Google Cloud Architecture
Framework pillars are affected (operational excellence, security/privacy/
compliance, reliability, cost optimization, performance optimization,
sustainability) and how. See the `gcp-waf-review` skill.
