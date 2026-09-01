---
name: Incident Management
description: Severity classification, runbook structure, and blameless postmortems — so incidents are handled calmly, restored fast, and learned from.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [incident, on-call, runbooks, postmortem]
---
## Purpose

Incidents are inevitable; chaos is optional. This skill is the structure that turns a scary production event into a sequence of calm, practiced steps — and turns the aftermath into a learning opportunity instead of a blame session.

## When to use it

When an incident happens (or is suspected), when writing or updating runbooks, and when conducting a postmortem.

## Steps / checklist

1. **Severity classification.** Every incident gets a severity (SEV1 = service down / data loss, SEV2 = degraded, SEV3 = minor) so the response matches the impact. Classify early and re-classify as facts change.
2. **Fix forward, then fix backward.** Restore service first (rollback, failover, scale-out), investigate root cause after. The goal during an incident is to stop the bleeding, not to understand it.
3. **Runbooks.** Every known failure mode has a runbook: symptoms, quick diagnosis, immediate mitigation, and escalation path. A runbook that requires the author to be present isn't a runbook.
4. **Communication.** Designate a coordinator. Status updates go to a single channel with a consistent format (what's happening, what's being done, when's the next update). No silent heroes.
5. **Blameless postmortem.** After the incident, write a postmortem covering: timeline, impact, root cause, what worked, what didn't, and action items. Blameless means the goal is to fix the system, not the person.
6. **Action items are tracked.** Every postmortem produces follow-up action items with owners and due dates. A postmortem without tracked follow-ups is a ceremony, not a process.

## Expected output

An incident that a fresh on-call engineer can handle using runbooks and severity definitions alone, and a postmortem that produces tracked, owned action items. If the response depends on who happens to be on call, the incident management work isn't done.