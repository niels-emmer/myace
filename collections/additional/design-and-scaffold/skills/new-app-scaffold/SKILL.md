---
name: New App Scaffold
description: Day-one bootstrap for a new application repository — the baseline file set, docs, CI, decision-log seed, and environment template.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [scaffold, bootstrap, repository, project-setup]
---
## Purpose

Start a new application with its documentation, CI, and decision log already in
place, instead of retrofitting them at release time. The first commit should be
a working skeleton a new contributor — human or agent — can pick up immediately.

## When to use it

Creating a brand-new application repository. When the self-hosted-deploy add-on is composed and the app fits the
single-container shape, pair it with the `self-hosted-app` skill.

## The baseline file set

```
AGENTS.md                      # portable contract — write this FIRST
README.md                      # the front door, in the first commit
CHANGELOG.md
LICENSE
SECURITY.md
CONTRIBUTING.md
CODE_OF_CONDUCT.md
.editorconfig
.gitignore
.dockerignore
.env.example
Dockerfile
docker-compose.yml
docs/ARCHITECTURE.md
docs/DEVELOPMENT.md
docs/DEPLOYMENT.md
docs/decision-log.md
src/  test/  scripts/  public/
.github/workflows/ci.yml
.github/dependabot.yml
```

Add a third-party dependency ledger once dependencies ship, and a threat-model
directory once the app stores user input.

## Order of operations

1. **`AGENTS.md` first.** Record the architecture map, exact build and test
   commands, conventions, and traps already hit. It is the highest-leverage
   file: an agent with no memory becomes productive by reading it.
2. **Tests before features.** Stand up the test runner and one passing test so
   "done" is runnable from day one.
3. **Decision log.** Seed the log with the initial stack choice and what you
   rejected.
4. **`.env.example`.** Document every variable with a safe default; the real
   environment file stays gitignored.
5. **Container.** A Dockerfile (non-root, pinned base, healthcheck) and a
   compose file, following the container guidance.
6. **CI.** A workflow that installs, lints, and tests, plus a dependency-update
   configuration.
7. **Community files.** License, security policy, contributing guide, code of
   conduct, and changelog.
8. **First commit** on the default branch, then branch protection requiring a
   green CI check.

## Conventions

- Pin dependency versions and base image tags; never rely on a floating
  `latest`.
- No secrets in the repository, ever — commit only the example environment
  file.
- Keep `AGENTS.md` short and link out to detail rather than inlining it.
- Default to one container and one local database file; justify anything
  heavier.
- Mark AI-authored commits with an `[ai]` line in the body (the same marker the enterprise-ai-governance and auditor packs use).

## Definition of done

- [ ] `AGENTS.md` present with real build and test commands.
- [ ] Test runner configured with at least one passing test.
- [ ] `.env.example` complete; the real environment file gitignored.
- [ ] Container builds and runs non-root with a healthcheck.
- [ ] CI green on the first push; dependency updates configured.
- [ ] Docs set present (architecture, development, deployment, decision log).
- [ ] Community file set present.

## Output format

```
## Scaffold summary
- Files created: <count>
- Docs set: complete / missing <files>
- CI: <workflow> / none
- Env template: yes / no
- First commit: <sha or pending>
```
