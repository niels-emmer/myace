---
description: Produce a concise handoff with the work state, verification evidence, remaining risk, and the exact next step.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
---
Review the current workspace state and produce a concise handoff for the next
person or session.

## Include

1. **Goal** — achieved, or still in progress and why.
2. **Changes** — the files and areas touched, grouped by intent.
3. **Verification** — the exact commands run and their results, not a claim
   that it "should work".
4. **Residual risk** — what is unverified, flaky, or deliberately deferred.
5. **Next step** — the single most useful action for whoever continues.

## Rules

- Separate what was verified from what was assumed.
- If tests were not run, say so plainly and explain why.
- Note any uncommitted or unstaged state, and any branch or worktree the next
  person must know about.
- Do not present a summary of intent as evidence of behaviour.

## Output format

```
## Handoff
- Goal: <achieved / in progress — detail>
- Changes: <files and intent>
- Verified: <commands and results>
- Unverified / risk: <list>
- Next step: <one action>
```
