# Azure Cloud Architect

Azure-specific architecture and governance rules. This collection layers on
the vendor-agnostic `iac-expert` collection — it assumes the general IaC
invariants (private-by-default, managed identity over secrets, naming/tagging,
remote state with locking, approval-gated applies, documented exceptions,
well-architected pillar review) and adds the Azure-specific layer on top.
Compose it with `iac-expert` (and a base collection) in a profile.

## Azure Governance By Design (CAF)

Follow Cloud Adoption Framework (CAF) governance essentials: a management-group
hierarchy that separates platform from workloads, subscriptions scoped by
environment/workload boundary, RBAC assigned at the narrowest effective scope,
and Azure Policy guardrails that enforce the invariants below rather than
relying on convention. See the `azure-caf-landing-zones` skill.

## Identity: Entra ID And Managed Identity

Use Entra ID (Azure AD) as the identity plane. Prefer managed identity and
workload identity federation over service principals with client secrets —
never a long-lived secret where a federated credential works. Scope RBAC to
least privilege; enable MFA and conditional access for human access. See the
`azure-identity` skill.

## Azure Security By Default

Private endpoints and VNet isolation over public exposure. No public IP,
`0.0.0.0/0` NSG rule, or public storage/blob access without a documented
exception. Secrets live in Key Vault, referenced by ID — never embedded.
Defender for Cloud posture and Azure Policy guardrails are part of the
baseline, not an afterthought. See the `azure-security-checklist` skill.

## Azure Cost Attribution

Every resource carries the mandatory tags (owner, cost-center, environment,
workload) so spend rolls up correctly in Azure Cost Management. Size to actual
load; use reserved instances/commitment discounts only where the workload's
traffic pattern genuinely warrants them.

## Map Changes To Azure WAF Pillars

Before shipping nontrivial Azure changes, note which Azure Well-Architected
Framework pillars are affected (reliability, security, cost optimization,
operational excellence, performance efficiency) and how. See the
`azure-waf-review` skill.
