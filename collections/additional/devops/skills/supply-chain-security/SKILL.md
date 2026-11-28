---
name: Supply Chain Security
description: Checklist for securing CI/CD and the build supply chain covering pinning, token permissions, provenance, SBOMs and dependency review. Use when designing or reviewing pipelines and release processes.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [devops, supply-chain, ci]
---
## Purpose

Reduce the chance that a compromised dependency, action or build step ships to production, and make what you ship verifiable.

## When to use it

When creating or changing a pipeline, adding a third-party action or base image, publishing an artifact, or responding to a dependency compromise.

## Checklist

- **Pin actions**: reference third-party GitHub Actions by full 40-character commit SHA, not a tag, because tags can be moved (in a 2026 incident the tags of a widely used action were rewritten); keep a readable version comment and update through reviewed bot PRs. An organisation policy can require SHA pinning. Composite actions and reusable workflows can still pull unpinned references, so check them.
- **Pin images and tools**: base images by digest, build tools by version, and install from lockfiles.
- **Token permissions**: set `permissions:` to read-only by default and grant write per job; scope secrets to the jobs and environments that need them, with required reviewers on production.
- **Untrusted code**: do not run pull-request code from forks with secrets or write tokens; be especially careful with `pull_request_target` and `workflow_run`, and never interpolate untrusted values (titles, branch names) into shell steps.
- **Credentials**: use OIDC federation to the cloud provider with narrow trust conditions instead of long-lived keys stored as secrets.
- **Dependencies**: review new dependencies, run dependency review on pull requests, enable alerts, and install with lifecycle scripts disabled where possible.
- **Provenance and signing**: generate build provenance attestations and sign release artifacts and images; verify signatures and digests at deploy time.
- **SBOM**: produce an SBOM (SPDX or CycloneDX) per release and store it with the artifact so you can answer 'are we affected' quickly.
- **Publishing**: use trusted publishing (OIDC) for package registries where supported rather than long-lived tokens, and require approval on the publishing job.
- **Respond**: keep a runbook for a compromised dependency or action (find uses, rotate secrets the job could read, pin to a known-good SHA, review recent runs).

## Expected output

A pipeline whose third-party inputs are pinned, whose tokens are minimal and short-lived, and whose release artifacts carry provenance and an SBOM.
