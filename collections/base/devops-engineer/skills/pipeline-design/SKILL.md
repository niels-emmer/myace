---
name: Pipeline Design
description: CI/CD pipeline design — stage isolation, artifact promotion, environment gates, and rollback — so deploys are safe, repeatable, and fast to recover from.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [ci-cd, pipelines, release, devops]
---
## Purpose

A CI/CD pipeline is the release path for every change — if it's slow, flaky, or unsafe, every deploy inherits that. This skill is the checklist for designing pipelines that promote immutable artifacts through environments with gates that actually protect production.

## When to use it

When designing or modifying a pipeline: a new workflow, a new environment, a change to promotion rules, or a pipeline that's become a bottleneck or a source of flakiness.

## Steps / checklist

1. **Pipeline as code.** Pipeline definitions are version-controlled alongside the application. No manual steps in a deployment process — a manual step is a bug to automate.
2. **Stage isolation.** Each stage (build → unit test → integration test → staging deploy → smoke test → prod deploy) runs in a clean environment with the artifacts it needs. Stages don't share mutable state.
3. **Immutable artifacts.** Every build produces a versioned, immutable artifact (container image, binary, package) promoted through environments without rebuilding. Never rebuild from source for a deployment — promote the same artifact that passed tests.
4. **Environment gates.** Every promotion between environments requires passing the previous stage's gates. A failed gate stops the promotion — no force-promoting around a red stage.
5. **Rollback over fix-forward.** Rollback must be faster than fix-forward for production issues. Prefer deploying the previous known-good artifact over patching forward under pressure.
6. **Secret injection.** Secrets are injected at deploy time from a secrets manager, scoped to the job that needs them. Never bake secrets into artifacts or pipeline config.
7. **Caching and speed.** Cache dependencies and build layers where safe, but never cache in a way that makes builds non-reproducible. A pipeline nobody waits for is a pipeline that gets bypassed.
8. **Failure visibility.** Pipeline failures page the right people with the right context. A red pipeline that nobody notices is worse than no pipeline.

## Expected output

A pipeline that a new team member can read and understand end-to-end: what each stage does, what gates protect each promotion, and how a production incident is rolled back. If a deploy requires tribal knowledge or manual steps, the pipeline isn't done.