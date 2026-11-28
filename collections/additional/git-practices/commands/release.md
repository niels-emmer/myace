---
description: Release workflow — confirm the default branch is green, choose the next semantic version, update the changelog, tag, push, and publish the release.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
---
Run the release flow in order. Stop and ask the user wherever input is
required, and never skip a gate.

1. **Confirm the branch** — `git branch --show-current` must be the default
   release branch. Otherwise abort and tell the user to switch.

2. **Refresh** — pull the latest default branch. Abort on conflicts or a
   failed pull.

3. **Choose the next version** — read the latest version tag
   (`git tag -l 'v*' --sort=-v:refname | head -1`). Propose the next MINOR bump
   by default, and let the user accept it or enter another
   `vMAJOR.MINOR.PATCH`. Re-prompt on invalid input. Follow semantic
   versioning: MAJOR for incompatible changes, MINOR for backward-compatible
   features, PATCH for backward-compatible fixes.

4. **Confirm the release commit title** — suggest
   `chore(release): v{X.Y.Z}` and allow an override.

5. **Verify the branch is green** — run the project's test and build gates
   documented in its contributing notes. If any gate fails, report it and
   **abort**; do not release a red branch.

6. **Update the changelog** — move the Unreleased section under the new
   version with today's date, preserving the existing format.

7. **Commit on a release branch** — create `release/v{X.Y.Z}`, commit the
   changelog there, and push that branch. Never commit the release to the
   default branch directly.

8. **Open the release pull request** — open a PR from the release branch into
   the default branch and stop. The merge is the user's decision; do not merge.

9. **Tag after merge** — once the user confirms the PR is merged, pull the
   default branch, create an annotated tag on the merge commit
   (`git tag -a v{X.Y.Z} -m "v{X.Y.Z}"`), and push the tag.

10. **Publish the release** — create the release from the tag, using the
   changelog section as the notes. If a release workflow already publishes on
   tag push, say so and skip this step.

## Rules

- Never release from a non-default branch or with a failing gate.
- Never force-push or move an existing tag.
- Report the final version, tag, and release URL.
