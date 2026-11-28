# Google Cloud Architect

GCP-specific architecture and governance rules. This collection layers on the
vendor-agnostic `iac-expert` collection — it assumes the general IaC
invariants (private-by-default, managed identity over secrets, naming/tagging,
remote state with locking, approval-gated applies, documented exceptions,
well-architected pillar review) and adds the GCP-specific layer on top.
Compose it with `iac-expert` (and a base collection) in a profile. Without `iac-expert`, the skills below still apply, but record any exception in the PR description (rationale, compensating control, named approver, review date) and require explicit human approval before any apply.

## GCP Governance By Design

<!-- myace: priority=70 tags=cloud,governance -->

Follow Google Cloud resource-hierarchy governance essentials: a
resource hierarchy (Organization → Folders → Projects) that separates platform
from workloads, projects scoped by environment/workload boundary, IAM assigned
at the narrowest effective scope, and Organization-policy guardrails that
enforce the invariants below rather than relying on convention. See the
`gcp-landing-zones` skill, and `gcp-guardrails` for the constraint catalogue and rollout.

## Identity: IAM, Service Accounts, And Federation

<!-- myace: priority=90 tags=cloud,security -->

Use IAM as the identity plane. Prefer service accounts and Workload Identity
Federation over long-lived service-account keys — never a long-lived secret
where a federated credential works. Scope IAM roles to least privilege; enable
MFA for human access. See the `gcp-identity` skill.

## GCP Security By Default

<!-- myace: priority=90 tags=cloud,security -->

Private networking and VPC isolation over public exposure. No public IP,
`0.0.0.0/0` firewall rule, or public GCS bucket without a documented exception.
Secrets live in Secret Manager, referenced by ID — never embedded. Security
Command Center posture and Organization-policy guardrails are part of the
baseline, not an afterthought. See the `gcp-security-checklist` skill.

## GCP Cost Attribution

<!-- myace: priority=50 tags=cloud,cost -->

Every resource carries the mandatory labels (owner, cost-center, environment,
workload) so spend rolls up correctly in Cloud Billing. Size to actual load;
use committed-use discounts only where the workload's traffic pattern genuinely
warrants them.

## Map Changes To GCP Well-Architected Pillars

<!-- myace: priority=50 tags=cloud,architecture -->

Before shipping nontrivial GCP changes, note which Google Cloud Well-Architected
Framework pillars are affected (operational excellence, security/privacy/
compliance, reliability, cost optimization, performance optimization,
sustainability) and how. See the `gcp-waf-review` skill.

## GCP Pick The Service For The Workload

<!-- myace: priority=50 tags=gcp,architecture -->

Choose managed Google Cloud services deliberately and say why, give each workload its own service account with narrowly-scoped roles instead of the default compute service account, and prefer private connectivity (Private Service Connect, private IP) to public endpoints. See the `gcp-service-patterns` skill.
