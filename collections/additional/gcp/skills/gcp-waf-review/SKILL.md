---
name: GCP Architecture Framework Pillar Review
description: Google Cloud Architecture Framework pillar checklists — operational excellence, security/privacy/compliance, reliability, cost optimization, performance optimization, sustainability — for reviewing GCP infrastructure changes.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [gcp, iac, architecture, architecture-framework, governance]
---
## Purpose

The Google Cloud Architecture Framework is Google Cloud's set of design
principles for building reliable, secure, cost-optimized, operationally
excellent, performant, and sustainable workloads on GCP. This skill is the
GCP-specific companion to `iac-expert`'s generic `well-architected-review`
skill: it maps each pillar to the concrete GCP services and decisions that
actually move the needle, so a review checks real GCP constructs rather than
abstract principles.

## When to use it

Before calling any nontrivial GCP infrastructure change done — new resources,
materially changed configuration, anything that affects how the workload is
reached, scaled, secured, or paid for. Skip it for genuinely cosmetic changes
(a label fix, a variable rename with no resource impact).

## The pillars, and what to actually check in GCP

**Operational excellence.** Can this change be deployed, rolled back, and
monitored the same way as the rest of the environment — same pipeline (Cloud
Build / GitHub Actions), same alerting (Cloud Monitoring), same logging (Cloud
Logging, Cloud Audit Logs)? Is there a way to tell the resource is healthy
without logging into the console by hand? Does it run as code (IaC) rather
than click-ops, so it's reproducible?

**Security, privacy, and compliance.** Does this follow private-by-default
networking (no public IPs, VPC firewall rules scoped to least access) and
service-account-over-long-lived-keys? Does it grant any new IAM role, and is
it scoped to least privilege rather than a broad `roles/owner`/`*` grant? Does
it introduce or remove a documented exception? Is Security Command Center
posture and Cloud Audit Logs coverage still intact?

**Reliability.** Does the resource have a single point of failure it didn't
have to have? Consider multi-zone deployment (a managed instance group across
zones, a regional Cloud SQL/Spanner instance, a global/regional load balancer
in front of multiple backends), GCS versioning and object lifecycle for
durable data, and Cloud SQL automated backups. If it fails, what notices and
how does recovery happen — automatically (Cloud Monitoring alarms, managed
instance group autoscaling, Cloud DNS failover) or does someone have to
intervene? Does the change affect an existing backup path?

**Cost optimization.** Does the resource size/machine type match actual
expected load, or is it a guess to revisit after real usage data? Is there a
cheaper pricing model (serverless/Cloud Run vs. provisioned, committed-use
discounts vs. on-demand) that fits the workload's actual traffic pattern? Is
spend attributable to a specific `cost-center` label so it shows up correctly
in Cloud Billing?

**Performance optimization.** Is the resource sized and located (region, zone,
proximity to users/data) appropriately for its latency and throughput needs?
Does the change introduce a new dependency or hop (a new gateway, a
cross-region call) that could become a bottleneck under load? Is autoscaling
configured where load varies?

**Sustainability.** Does the change minimize idle resources (right-sized
instances, autoscaling that scales to zero where appropriate, no
over-provisioned storage)? Is data lifecycle-managed (GCS lifecycle policies,
snapshot retention) rather than stored forever? Does it prefer regions with
lower carbon intensity where latency allows?

## Expected output

A short per-change note — one line per pillar it plausibly affects, skipping
pillars that are genuinely untouched rather than padding the list. For
example:

```
- Operational excellence: deploys via the existing Cloud Build pipeline; Cloud Monitoring alarm added.
- Security: replaces a long-lived service-account key with Workload Identity Federation.
- Reliability: moves the database to a regional Cloud SQL instance with automated backups.
- Cost optimization: neutral — same machine type, regional add-on is the only delta.
- Performance optimization: not materially affected.
- Sustainability: scales to zero outside business hours.
```

This goes in the PR description or commit message alongside the change —
short enough to write every time, substantive enough to catch the change that
quietly trades one pillar for another.
