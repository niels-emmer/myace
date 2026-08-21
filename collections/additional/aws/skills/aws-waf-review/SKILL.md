---
name: AWS WAF Pillar Review
description: AWS Well-Architected Framework pillar checklists — operational excellence, security, reliability, performance efficiency, cost optimization, sustainability — for reviewing AWS infrastructure changes.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [aws, iac, architecture, well-architected, governance]
---
## Purpose

The AWS Well-Architected Framework (WAF) is AWS's set of design principles for
building reliable, secure, cost-optimized, operationally excellent, performant,
and sustainable workloads on AWS. This skill is the AWS-specific companion to
`iac-expert`'s generic `well-architected-review` skill: it maps each pillar to
the concrete AWS services and decisions that actually move the needle, so a
review checks real AWS constructs rather than abstract principles.

## When to use it

Before calling any nontrivial AWS infrastructure change done — new resources,
materially changed configuration, anything that affects how the workload is
reached, scaled, secured, or paid for. Skip it for genuinely cosmetic changes
(a tag fix, a variable rename with no resource impact).

## The pillars, and what to actually check in AWS

**Operational excellence.** Can this change be deployed, rolled back, and
monitored the same way as the rest of the environment — same pipeline (GitHub
Actions/CodePipeline), same alerting (CloudWatch alarms), same logging
(CloudWatch Logs, CloudTrail)? Is there a way to tell the resource is healthy
without logging into the console by hand? Does it run as code (IaC) rather
than click-ops, so it's reproducible?

**Security.** Does this follow private-by-default networking (private subnets,
no public IPs, security groups/NACLs scoped to least access) and
IAM-role-over-access-keys? Does it grant any new IAM permission, and is it
scoped to least privilege rather than a broad `AdministratorAccess`/`*`
policy? Does it introduce or remove a documented exception? Is Security
Hub/GuardDuty/Config posture and CloudTrail coverage still intact?

**Reliability.** Does the resource have a single point of failure it didn't
have to have? Consider multi-AZ deployment (an Auto Scaling group across AZs,
a Multi-AZ RDS/Aurora cluster, an ALB/NLB in front of multiple targets), S3
versioning and cross-region replication for durable data, and RDS automated
backups. If it fails, what notices and how does recovery happen — automatically
(CloudWatch alarms, autoscaling, Route 53 failover) or does someone have to
intervene? Does the change affect an existing backup path?

**Performance efficiency.** Is the resource sized and located (region,
proximity to users/data) appropriately for its latency and throughput needs?
Does the change introduce a new dependency or hop (a new gateway, a
cross-region call) that could become a bottleneck under load? Is autoscaling
configured where load varies?

**Cost optimization.** Does the resource size/instance type match actual
expected load, or is it a guess to revisit after real usage data? Is there a
cheaper pricing model (serverless/on-demand vs. provisioned, reserved
instances or savings plans vs. on-demand) that fits the workload's actual
traffic pattern? Is spend attributable to a specific `cost-center` tag so it
shows up correctly in Cost Explorer?

**Sustainability.** Does the change minimize idle resources (right-sized
instances, autoscaling that scales to zero where appropriate, no over-provisioned
storage)? Is data lifecycle-managed (S3 lifecycle policies, EBS snapshots
retention) rather than stored forever?

## Expected output

A short per-change note — one line per pillar it plausibly affects, skipping
pillars that are genuinely untouched rather than padding the list. For
example:

```
- Operational excellence: deploys via the existing GitHub Actions pipeline; CloudWatch alarm added.
- Security: replaces a long-lived access key with an IAM role via OIDC federation.
- Reliability: moves the database to Multi-AZ with automated backups.
- Performance efficiency: not materially affected.
- Cost optimization: neutral — same instance type, Multi-AZ add-on is the only delta.
- Sustainability: scales to zero outside business hours.
```

This goes in the PR description or commit message alongside the change —
short enough to write every time, substantive enough to catch the change that
quietly trades one pillar for another.
