---
name: Exception Documentation
description: The template for documenting a deliberate, approved deviation from an infrastructure invariant — rationale, compensating control, approver, and expiry — instead of a silent workaround.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [iac, governance, risk, compliance]
---
## Purpose

Some invariants genuinely can't be met in every situation — a legacy client needs a public endpoint, a third-party system has no workload-identity support and needs a static key. That's fine, occasionally, as long as it's a decision someone made on purpose and can find again later. This skill is the template that turns "we had to break the rule here" into a durable, reviewable record instead of a comment nobody will trust six months from now.

## When to use it

Any time a change violates one of the standing invariants (private-by-default networking, managed identity over secrets, naming/tagging convention, remote state with locking) and there's a genuine reason it has to. Write the exception *before* or *alongside* implementing the deviation — not after the fact when someone asks about it.

## Required fields

Every documented exception needs all four of these — a deviation missing any one of them is not a documented exception, it's an undocumented one with extra steps:

1. **Rationale** — Why can't this resource follow the rule? Be specific about the actual constraint (e.g. "third-party partner's system only supports static API keys, no OAuth/federation option" or "legacy consumer application requires a public endpoint until its Q3 migration lands"), not a restatement of the exception itself.
2. **Compensating control** — What's in place instead to keep the risk bounded? For a public endpoint: IP allow-listing, WAF rules, rate limiting. For a static secret: short rotation interval, storage in a secret manager rather than in code, scoped-down permissions. A compensating control that's just "we'll be careful" is not a compensating control.
3. **Approver** — A named individual (not a team, not "leadership") who reviewed this specific exception and signed off on it. If no one can be named, the exception isn't approved yet.
4. **Expiry / review date** — A concrete date this exception gets revisited, not "permanent" or "TBD." If the underlying constraint is genuinely permanent, that's still worth re-confirming on a cadence (e.g. annually) rather than assumed forever.

## Template

```markdown
### Exception: <short name>

- **Rule deviated from:** <e.g. Private By Default>
- **Resource(s):** <resource name(s), matching the naming convention>
- **Rationale:** <why this can't follow the rule>
- **Compensating control:** <what limits the risk instead>
- **Approver:** <name>, <date approved>
- **Review / expiry date:** <date>
```

## Where it lives

Keep exceptions next to the code they apply to — a comment block above the relevant resource block referencing the template, or a project-level `EXCEPTIONS.md`/`docs/infrastructure-exceptions.md` that every exception gets appended to, whichever the project already has a pattern for. What matters is that it's discoverable by someone reading the code later, not buried in a chat thread or a closed pull request.

## Expected output

A filled-out exception block (all four fields present, no placeholders left in) attached to the change, plus the corresponding resource tagged with a `review-date` per the `resource-naming` skill so the exception surfaces again when it's due for reconsideration.
