---
name: Incident Response
description: Severity classification, runbook creation, blameless postmortem, and communication channels for production incidents.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [devops, incidents, sre]
---
## Purpose

Respond to incidents consistently and learn from them without blame.

## Checklist

- **Severity classification**: SEV1 (user-facing outage), SEV2 (degraded but usable), SEV3 (minor issue, no user impact). Define response SLAs per severity.
- **Runbooks**: every service has a runbook covering common failure modes, health check endpoints, and rollback procedures.
- **Fix forward, then fix backward**: restore service first (rollback, feature flag, traffic shift), investigate root cause after.
- **Communication**: incident channel established within 5 minutes of SEV1/SEV2 declaration. Status updates every 30 minutes.
- **Blameless postmortem**: within 48 hours of SEV1 resolution. Document timeline, root cause, impact, and action items.
- **Action items**: every postmortem produces at least one concrete, tracked action item to prevent recurrence.

## Expected output

An incident response process where every SEV1/SEV2 has a documented timeline, root cause, and action items — and no blame is assigned.
