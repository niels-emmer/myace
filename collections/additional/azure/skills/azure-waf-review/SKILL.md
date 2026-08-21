---
name: Azure WAF Pillar Review
description: Azure-specific Well-Architected Framework pillar checklists — reliability, security, cost optimization, operational excellence, performance efficiency — for reviewing Azure infrastructure changes.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [azure, iac, architecture, well-architected, governance]
---
## Purpose

The Azure Well-Architected Framework (WAF) is Microsoft's set of design
principles for building reliable, secure, cost-optimized, operationally
excellent, and performant workloads on Azure. This skill is the Azure-specific
companion to `iac-expert`'s generic `well-architected-review` skill: it maps
each pillar to the concrete Azure services and decisions that actually move
the needle, so a review checks real Azure constructs rather than abstract
principles.

## When to use it

Before calling any nontrivial Azure infrastructure change done — new
resources, materially changed configuration, anything that affects how the
workload is reached, scaled, secured, or paid for. Skip it for genuinely
cosmetic changes (a tag fix, a variable rename with no resource impact).

## The pillars, and what to actually check in Azure

**Reliability.** Does the resource have a single point of failure it didn't
have to have? Consider availability zones (zone-redundant storage, zonal VMs,
zone-redundant App Service plans), availability sets for legacy VMs, and
redundancy tiers (LRS vs. ZRS vs. GRS for storage). If it fails, what notices
and how does recovery happen — automatically (Azure Monitor alerts, autoscale,
failover) or does someone have to intervene? Does the change affect an
existing backup path (Azure Backup, geo-replication, traffic-manager/front-door
failover)?

**Security.** Does this follow private-by-default networking (private
endpoints, VNet integration, no public IPs) and managed-identity-over-secrets?
Does it grant any new RBAC permission, and is it scoped to least privilege
rather than a broad Contributor/Owner role? Does it introduce or remove a
documented exception? Is Defender for Cloud posture and Azure Policy coverage
still intact?

**Cost optimization.** Does the resource size/tier match actual expected load,
or is it a guess to revisit after real usage data? Is there a cheaper tier or
pricing model (serverless/consumption vs. provisioned, reserved instances or
Azure savings plans vs. pay-as-you-go) that fits the workload's actual traffic
pattern? Is spend attributable to a specific `cost-center` tag so it shows up
correctly in Azure Cost Management?

**Operational excellence.** Can this change be deployed, rolled back, and
monitored the same way as the rest of the environment — same pipeline (Azure
DevOps/GitHub Actions), same alerting (Azure Monitor), same logging (diagnostic
settings to Log Analytics)? Is there a way to tell the resource is healthy
without logging into the portal by hand?

**Performance efficiency.** Is the resource sized and located (region,
proximity to users/data) appropriately for its latency and throughput needs?
Does the change introduce a new dependency or hop (a new gateway, a
cross-region call) that could become a bottleneck under load? Is autoscaling
configured where load varies?

## Expected output

A short per-change note — one line per pillar it plausibly affects, skipping
pillars that are genuinely untouched rather than padding the list. For
example:

```
- Reliability: moves the database to zone-redundant storage.
- Security: replaces a service-principal secret with a managed identity.
- Cost optimization: neutral — same tier, redundancy add-on is the only delta.
- Operational excellence: no change to deploy/monitoring path.
- Performance efficiency: not materially affected.
```

This goes in the PR description or commit message alongside the change —
short enough to write every time, substantive enough to catch the change that
quietly trades one pillar for another.
