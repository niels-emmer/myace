# Scaleway Cloud Architect

Scaleway-specific architecture and governance rules. This collection layers on
the vendor-agnostic `iac-expert` collection — it assumes the general IaC
invariants (private-by-default, managed identity over secrets, naming/tagging,
remote state with locking, approval-gated applies, documented exceptions,
well-architected pillar review) and adds the Scaleway-specific layer on top.
Compose it with `iac-expert` (and a base collection) in a profile.

## Governance By Design

Follow Scaleway's governance essentials: an Organization → Project structure
that separates platform from workloads, projects scoped by environment/workload
boundary, IAM assigned at the narrowest effective scope (Organization vs.
Project), and guardrails that enforce the invariants below rather than relying
on convention. See the `scaleway-architecture` skill.

## Identity: IAM, Applications, And Federation

Use IAM as the identity plane. Prefer IAM applications + API keys and identity
federation (OAuth2/SAML SSO) over long-lived credentials — never a long-lived
secret where a federated credential works. Scope IAM permission sets to least
privilege; enable MFA for human access. See the `scaleway-architecture` skill.

## Security By Default

Private networking and VPC isolation over public exposure. No public IP,
`0.0.0.0/0` security-group rule, or public object-storage bucket without a
documented exception. Secrets live in Secret Manager, referenced by ID — never
embedded. Security groups (virtual firewalls on the public interface), private
networks, and WAF edge protection are part of the baseline, not an
afterthought. See the `scaleway-security-checklist` skill.

## Cost Attribution

Every resource carries the mandatory tags (owner, cost-center, environment,
workload) so spend rolls up correctly in cost reports. Size to actual load;
use reserved/committed pricing only where the workload's traffic pattern
genuinely warrants them.

## Map Changes To Architecture And Security

Before shipping nontrivial Scaleway changes, note how the change affects the
architecture (org/project structure, IAM scoping, VPC/private-network
topology, security groups) and the security posture, and how. See the
`scaleway-architecture` and `scaleway-security-checklist` skills.
