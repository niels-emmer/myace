---
name: PR Standards
description: Pull request description, review depth, and merge standards so every PR carries enough context to review and merge safely.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [git, pull-request, review, collaboration]
---
## Purpose

A PR is the unit of review. A good description makes review fast and safe; a thin one makes reviewers guess at intent. This skill standardizes the description, the review depth, and the merge gate so nothing important is left to chance — and so a reviewer can verify the change matches its stated intent rather than trusting the summary.

## When to use it

Any time you open, review, or merge a pull request.

## PR description template

```markdown
## Summary
<!-- One paragraph: what changed and why. -->

## Related issues
<!-- Closes: #N, Refs: #M -->

## Type of change
- [ ] feat (new feature)
- [ ] fix (bug fix)
- [ ] refactor (no behaviour change)
- [ ] test (tests only)
- [ ] docs (documentation)
- [ ] chore (tooling, deps, CI)
- [ ] security (security hardening)

## Testing
<!-- How was this tested? Commands run, manual steps, edge cases checked. -->

## Checklist
- [ ] Self-review completed
- [ ] Tests pass
- [ ] No secrets in the diff
- [ ] Docs updated if behaviour changed
```

## Review depth

- Read the diff, not just the description — verify the change matches the stated intent.
- Check for behavioural regressions, missing verification, and scope creep (unrelated changes sneaking in).
- For security-sensitive changes (auth, payments, data access, crypto), require a dedicated security review, not just a general pass.
- Leave concrete, actionable feedback; approve only when you'd be comfortable owning the change.

## Merge gate

- At least one approving review before merging to a protected branch.
- Stale reviews are dismissed when new commits are pushed — re-review after changes.
- CI must pass before merge.
- Prefer squash or rebase merge for a clean history; avoid merge commits on a linear-history branch.

## Expected output

A PR that a reviewer can understand and verify from the description alone, reviewed to a depth proportional to its risk, and merged only when it passes the gate.
