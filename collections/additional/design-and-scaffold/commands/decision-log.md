---
description: Record a durable architecture or workflow decision — context, decision, rationale, impact, and follow-up — in a decision log.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
---
Record one decision-log entry.

Decision input: the decision described when this command is invoked.

## Rules

- If the arguments name a target path (for example `path: docs/decision-log.md`),
  append the entry there. If no path is given, print the entry so the user can
  file it.
- Append a new entry; never rewrite historical entries unless explicitly asked.
- Keep entries concise and factual.
- Cover: context, decision, alternatives considered, rationale, impact, and
  follow-up actions.
- If a detail is missing, make the smallest reasonable assumption and mark it
  as an assumption.

## Entry format

```
## <YYYY-MM-DD> — <short decision title>
- Status: proposed / accepted / superseded
- Context: <the pressure that forced a decision>
- Decision: <what was chosen>
- Alternatives: <what was rejected and why>
- Impact: <what changes as a result>
- Follow-ups: <work this creates>
```

## Final response

Report the entry date/title, the target path (or `stdout`), and any assumptions
used.
