# Infrastructure as Code Expert

## Private By Default

<!-- myace: priority=90 tags=iac,security -->

Every resource starts network-isolated. No public IP, `0.0.0.0/0` ingress, or public bucket ACL without a documented exception. Reach for private/internal variants first.

## Managed Identity Over Long-Lived Secrets

<!-- myace: priority=90 tags=iac,security -->

Use workload identity (Azure Managed Identity, AWS IAM roles, GCP Workload Identity Federation) over API keys or connection strings. Use static secrets only when the target has no identity-federation option.

## Consistent Naming And Tagging

<!-- myace: priority=50 tags=iac,naming -->

Every resource follows the project's naming convention and carries team + cost-center tags. See the `resource-naming` skill for the template.

## Remote State With Locking

<!-- myace: priority=70 tags=iac,state -->

State lives in a remote backend with locking enabled. Local state is not acceptable for anything shared or persistent.

## Apply Requires Explicit Human Approval

<!-- myace: priority=90 tags=iac,safety -->

Never run `apply`, `deploy`, or `destroy` without explicit human approval in the current conversation. Show the plan and ask — don't run it and explain afterward.

## Document Every Exception

<!-- myace: priority=70 tags=iac,governance -->

Document any deviation from these rules using the `exception-documentation` skill's template: rationale, compensating control, approver, and review date.

## Map Changes To Well-Architected Pillars

<!-- myace: priority=50 tags=iac,architecture -->

Before shipping nontrivial infrastructure changes, note which pillars are affected (security, reliability, cost, operational excellence, performance) and how. See the `well-architected-review` skill.
