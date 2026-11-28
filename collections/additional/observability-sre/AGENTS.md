# Observability & Incident Review

Observability and reliability conventions: telemetry, SLOs, alerting and post-incident review. This
collection layers on a base collection and goes deeper than the base packs' observability rules and
the `devops` incident-response skill: it supplies concrete telemetry conventions, SLO and alert
design, and a blameless review method. It assumes the base pack's change-control and secrets rules.

## Telemetry Carries No Secrets Or Personal Data

<!-- myace: priority=90 tags=observability,security -->

Never put secrets, tokens, credentials, full request bodies or personal data in logs, metrics labels, trace attributes or error reports. Redact at the source, not in the pipeline, and treat telemetry as readable by many people and retained for a long time.

## Instrument With Standard Conventions

<!-- myace: priority=70 tags=observability,telemetry -->

Emit structured logs, RED metrics (rate, errors, duration) for each service and USE metrics (utilisation, saturation, errors) for resources, and traces with context propagated across every service and queue hop. Prefer OpenTelemetry APIs and semantic-convention attribute names over bespoke formats. Keep metric label cardinality bounded: never use user IDs, emails or raw URLs as labels. See the `telemetry-conventions` skill.

## Define SLOs Before Alerts

<!-- myace: priority=70 tags=observability,slo -->

For each user-facing service state what matters to users as a service level indicator, set a service level objective over a window, and track the error budget. Choose a few SLOs per service rather than one per metric. See the `slo-and-alerting` skill.

## Alert On Symptoms, With An Owner And A Runbook

<!-- myace: priority=70 tags=observability,alerting -->

Page only for conditions that need a human now and that users feel (budget burn, sustained errors, saturation about to cause failure); everything else is a ticket or a dashboard. Every alert names an owner, links a runbook and says what to check first. Remove or fix an alert that is routinely ignored.

## Postmortems Are Blameless And Produce Actions

<!-- myace: priority=70 tags=observability,incident -->

After any user-impacting incident write a review that covers the timeline, impact, contributing factors, what went well, what was lucky, and tracked follow-up actions with owners and dates. Focus on system and process causes, not individuals. See the `blameless-postmortem` skill.

## Change Production Observability Carefully

<!-- myace: priority=90 tags=observability,safety -->

Confirm before deleting dashboards, silencing or deleting alerts, shortening retention, rotating telemetry credentials or changing sampling in production: these remove the ability to see failures. Silences have an expiry and a reason.
