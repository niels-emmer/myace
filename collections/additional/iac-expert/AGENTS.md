# Infrastructure as Code Expert

An additional rule set for cloud infrastructure work — Terraform, OpenTofu, Bicep, CloudFormation, Pulumi, or any other IaC tool — meant to sit on top of a base collection (software-engineer or vibecoder). It codifies a small set of invariants that should hold on every cloud regardless of provider, plus a hard boundary around who is allowed to actually change running infrastructure.

## Private By Default

Every resource that can be network-isolated starts network-isolated. No public IP, public endpoint, `0.0.0.0/0` ingress rule, or public storage/bucket ACL gets attached to a resource unless there's a documented reason it has to be reachable from the open internet (see the "Document Every Exception" rule below). This applies the same way on every provider — Azure private endpoints and NSGs, AWS security groups and VPC endpoints, GCP firewall rules and Private Service Connect are different mechanisms for the same default. When scaffolding a new resource, reach for the private/internal variant first and only widen exposure when a real requirement forces it, not because it's the path of least resistance while prototyping.

## Managed Identity Over Long-Lived Secrets

Wherever the provider offers workload identity — Azure Managed Identity, AWS IAM roles for services (including IRSA/pod identity), GCP service accounts with Workload Identity Federation — use it instead of minting an API key, connection string, or access key for a service to authenticate with another service. Long-lived credentials are a liability the moment they're created: they can leak, they don't rotate themselves, and they usually end up broader in scope than the workload actually needs. Reach for a static secret only when the target system genuinely has no identity-federation story, and even then prefer a short-lived, provider-issued credential over a hand-generated one.

## Consistent Naming And Tagging

Every resource gets a name and a set of tags/labels that follow one convention across the whole environment — see the `resource-naming` skill for the concrete template. At minimum, every resource is tagged with an owning team or individual and a cost-center/billing identifier, in addition to whatever resource-type/workload/environment/region convention the naming skill lays out. Untagged or inconsistently-named resources are how "which team owns this and can we turn it off" turns into an afternoon of archaeology. Don't skip tagging for a resource because it feels temporary — temporary resources are exactly the ones that get forgotten.

## Remote State With Locking

State lives in a remote backend with locking enabled — a cloud storage backend with a lease/lock mechanism, or a dedicated state-locking service — for anything beyond a genuinely personal, throwaway sandbox that only one person will ever touch. Local state files are not acceptable for anything shared, anything that persists past a single session, or anything backing real infrastructure, because they can't be safely used by more than one person or process at a time and they're one lost laptop away from losing the only copy of truth about what's deployed. If you find local state being used for something that looks like it's outgrown "personal sandbox," flag it and propose migrating to a remote backend rather than continuing to build on top of it.

## Apply Requires Explicit Human Approval

Generating IaC, running a plan/diff, linting, and running policy checks are all things an agent can do freely and repeatedly without asking permission — that's exploratory and reversible. Applying that plan against real infrastructure is not. An agent must never run `apply`, `deploy`, or any equivalent state-changing command against real infrastructure without an explicit, unambiguous go-ahead from a human in the current conversation — not an inferred approval, not a prior approval for a different change, not "the plan looked fine so I proceeded." Treat this as a hard boundary rather than a judgment call: when in doubt, show the plan and ask, don't run it and explain afterward. This applies equally to destroy/teardown operations.

## Document Every Exception

Any time a rule in this file genuinely can't be followed — a workload needs a public endpoint, a system has no identity-federation option and needs a static credential, a resource can't fit the naming convention — the deviation gets written down using the `exception-documentation` skill's template, not silently applied. A documented exception needs a rationale (why the rule can't be met here), a compensating control (what's in place instead to limit the risk), an approver (a named person who signed off, not just "the team"), and an expiry or review date (exceptions are reviewed, not permanent by default). An undocumented deviation from an invariant is a bug in the infrastructure, not a judgment call that speaks for itself.

## Map Changes To Well-Architected Pillars

Before calling any nontrivial infrastructure change done, be able to say which of the standard pillars it touches and how: security, reliability, cost, operational excellence, and performance (the naming varies slightly by provider — Azure's Well-Architected Framework, AWS's Well-Architected Framework, and Google Cloud's architecture framework all converge on essentially this same set). This isn't paperwork for its own sake — it's a forcing function to notice, for example, that a change which improves performance also loosens a security control, or that a reliability improvement quietly doubles cost. A one-line note per affected pillar in the PR description or commit message is enough; the discipline is in actually checking each pillar, not in the length of the writeup. See the `well-architected-review` skill for a walk-through of what to check per pillar.
