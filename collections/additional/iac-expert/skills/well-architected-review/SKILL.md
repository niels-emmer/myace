---
name: Well-Architected Pillar Review
description: A discipline for mapping any nontrivial infrastructure change to the standard architecture pillars — security, reliability, cost, operational excellence, performance — regardless of cloud provider.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor]
tags: [iac, architecture, well-architected, governance]
---
## Purpose

Every major cloud provider publishes a "well-architected" style framework — Azure's Well-Architected Framework, AWS's Well-Architected Framework, Google Cloud's architecture framework — and they converge on essentially the same handful of pillars, phrased slightly differently. The value isn't in citing a specific provider's document; it's in the habit of checking a change against all of them instead of only the one pillar that happened to motivate the change. This skill is a short walk-through of what to check per pillar, provider-agnostic.

## When to use it

Before calling any nontrivial infrastructure change done — new resources, materially changed configuration of existing ones, anything that affects how the system is reached, scaled, or paid for. Skip it for genuinely cosmetic changes (renaming a variable with no resource impact).

## The pillars, and what to actually check

**Security.** Does this change follow private-by-default networking and managed-identity-over-secrets? Does it grant any new permission, and is that permission scoped to what's needed? Does it introduce or remove a documented exception?

**Reliability.** Does this resource have a single point of failure it didn't have to have (no redundancy, no multi-zone/multi-region option considered)? If it fails, what notices, and how does recovery happen — automatically, or does someone have to intervene? Does the change affect any existing failover or backup path?

**Cost.** Does the resource size/tier match actual expected load, or is it a guess that should be revisited after real usage data exists? Is there a cheaper resource type or pricing model (reserved/committed vs. on-demand, serverless vs. always-on) that fits the workload's actual traffic pattern? Is the cost attributable to a specific `cost-center` tag so it shows up in the right place later?

**Operational excellence.** Can this change be deployed, rolled back, and monitored the same way the rest of the environment is — same pipeline, same alerting, same logging conventions — or does it introduce a one-off process? Is there a way to tell the resource is healthy without logging into a console by hand?

**Performance.** Is the resource sized and located (region/proximity) appropriately for its expected latency and throughput needs? Does the change introduce a new dependency or hop that could become a bottleneck under load?

Some frameworks add a sustainability pillar (resource/energy efficiency) as a sixth consideration — worth a mention if the project already tracks it, but treat the five above as the required baseline.

## Expected output

A short per-change note — one line per pillar it plausibly affects, skipping pillars that are genuinely untouched rather than padding the list. For example:

```
- Security: moves service auth from a static key to managed identity.
- Reliability: adds a second availability zone for the database.
- Cost: neutral — same tier, redundancy add-on is the only delta.
- Operational excellence: no change to deploy/monitoring path.
- Performance: not materially affected.
```

This goes in the PR description or commit message alongside the change — short enough to write every time, substantive enough to catch the change that quietly trades one pillar for another.
