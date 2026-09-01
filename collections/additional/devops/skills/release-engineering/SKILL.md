---
name: Release Engineering
description: Semantic versioning, changelog generation, and release/hotfix management so releases are predictable and reversible.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [release, versioning, semver, changelog]
---
## Purpose

A release is a contract with everyone downstream. Consistent versioning and a maintained changelog make it predictable; a defined hotfix path makes it reversible. This skill standardizes how versions are bumped, releases are cut, and urgent fixes are shipped — so a release is never a hand-rolled, one-off process.

## When to use it

Any time you bump a version, cut a release, or ship an urgent fix to a released version.

## Semantic versioning

Given `MAJOR.MINOR.PATCH`:

| Bump | When |
|------|------|
| MAJOR | Breaking API or behaviour change |
| MINOR | New feature, backward-compatible |
| PATCH | Bug fix, backward-compatible |
| PRE-RELEASE | `MAJOR.MINOR.PATCH-<tag>.<number>` (e.g. `1.0.0-beta.1`) |

Pre-release precedence: `alpha` < `beta` < `rc` < stable.

## Changelog

Maintain a changelog that records, per release, what was added, changed, fixed, and removed. Group by release version and date, and link each entry to its PR/issue where possible. Never rewrite history — append a new release section rather than editing old ones.

## Cutting a release

1. Confirm the target branch is green (CI passing, no open blockers).
2. Bump the version per the table above.
3. Update the changelog with the new release section.
4. Tag the release commit (`v<MAJOR.MINOR.PATCH>`).
5. Build/publish the release artifact from the tagged commit, not from a moving branch.

## Hotfixes

1. Branch from the release tag, not from main — the hotfix must contain only the fix, not unrelated changes that landed after the release.
2. Apply the fix, bump PATCH, update the changelog.
3. Release the hotfix from its own tag.
4. Merge the fix back into main so it isn't lost.

## Expected output

A versioned release with a maintained changelog, cut from a tagged commit, and a hotfix path that ships only the fix and merges it back.
