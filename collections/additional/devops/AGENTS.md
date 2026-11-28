# DevOps / Platform Engineer

Designed to layer on the Software Engineer base pack. On the DevOps base pack many of these rules and skills overlap its own (immutable builds, observability, incident response, release gates); treat this pack there as a supplement and prefer the base pack's wording where they differ.

## Pipeline As Code

<!-- myace: priority=50 tags=devops,ci -->

CI/CD pipelines are version-controlled alongside application code. Pipeline definitions, deployment configs, and infrastructure references live in the repo, not in a web UI. Manual steps in a deployment process are a bug to automate.

## Immutable Artifacts

<!-- myace: priority=70 tags=devops,release -->

Every build produces a versioned, immutable artifact (container image, compiled binary, package) that is promoted through environments without rebuilding. Never rebuild from source for a deployment — promote the same artifact that passed tests.

## Observability Is A Feature

<!-- myace: priority=50 tags=devops,observability -->

Every service exposes structured logs, metrics, and traces from day one. Logs are structured (JSON), metrics follow RED (Rate/Errors/Duration) for services and USE (Utilization/Saturation/Errors) for resources. Alert on symptoms, not causes — page on user-facing impact, not on infrastructure noise.

## Incident Response Discipline

<!-- myace: priority=50 tags=devops,incident -->

Incidents have a severity classification, a documented runbook, and a blameless postmortem. Restore service first (roll back, flip a flag, shift traffic), then investigate the root cause and fix it forward. Every incident produces a follow-up action item.

## Release Gates

<!-- myace: priority=70 tags=devops,release -->

Every promotion between environments requires passing the previous stage's gates: build → unit test → integration test → staging deploy → smoke test → prod deploy. Rollback must be faster than fix-forward for production issues. See the `ci-cd-pipeline-design` skill for the concrete gate checklist.

## Config As Code

<!-- myace: priority=70 tags=devops,config -->

Environment configuration, feature flags, and service settings are version-controlled and reviewed like code. Secrets are injected at deploy time from a secrets manager, never baked into artifacts or config files.
