# AWS Cloud Architect

AWS-specific architecture and governance rules. This collection layers on the
vendor-agnostic `iac-expert` collection — it assumes the general IaC
invariants (private-by-default, managed identity over secrets, naming/tagging,
remote state with locking, approval-gated applies, documented exceptions,
well-architected pillar review) and adds the AWS-specific layer on top.
Compose it with `iac-expert` (and a base collection) in a profile.

## Governance By Design (CAF)

Follow Cloud Adoption Framework (CAF) governance essentials: an AWS
Organizations organizational-unit (OU) hierarchy that separates platform from
workloads, accounts scoped by environment/workload boundary, IAM assigned at
the narrowest effective scope, and Service Control Policies (SCPs) that
enforce the invariants below rather than relying on convention. See the
`aws-caf-landing-zones` skill.

## Identity: IAM And Federation

Use IAM as the identity plane. Prefer IAM roles and identity federation (IAM
Roles Anywhere, OIDC federation for GitHub Actions) over long-lived access
keys — never a long-lived secret where a federated credential works. Scope IAM
policies to least privilege; enable MFA for human access. See the
`aws-identity` skill.

## Security By Default

Private subnets and VPC isolation over public exposure. No public IP,
`0.0.0.0/0` security-group rule, or public S3 bucket without a documented
exception. Secrets live in Secrets Manager (or SSM Parameter Store), referenced
by ID — never embedded. Security Hub/GuardDuty/Config posture and CloudTrail
are part of the baseline, not an afterthought. See the `aws-security-checklist`
skill.

## Cost Attribution

Every resource carries the mandatory tags (owner, cost-center, environment,
workload) so spend rolls up correctly in Cost Explorer. Size to actual load;
use reserved instances/savings plans only where the workload's traffic pattern
genuinely warrants them.

## Map Changes To AWS WAF Pillars

Before shipping nontrivial AWS changes, note which AWS Well-Architected
Framework pillars are affected (operational excellence, security, reliability,
performance efficiency, cost optimization, sustainability) and how. See the
`aws-waf-review` skill.
