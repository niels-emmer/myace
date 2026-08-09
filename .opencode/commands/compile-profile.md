---
description: Compile a MyACE profile for a target framework (opencode, claude-code, cursor).
agent: general
---

Compile a MyACE profile into target framework files.

Usage: `/compile-profile <profile-id> <target>`

Targets:
- `opencode` — Generates `.opencode/skills/*.json`, `.opencode/agents/*.json`, `AGENTS.md`
- `claude-code` — Generates `CLAUDE.md`, `.claude/agents/*.md`, `.claude/workflows/*.md`
- `cursor` — Generates `.cursorrules`, `.cursor/rules/*.mdc`

Steps:
1. Ensure the dev stack is running
2. POST to the compile endpoint:
   ```
   curl -X POST http://localhost:8000/api/v1/profiles/compile \
     -H "Content-Type: application/json" \
     -d '{"profile_id": "<profile-id>", "target": "<target>"}'
   ```
3. The response contains `{filename: content}` map — write each file to the project root

Alternatively, use the web UI at `http://localhost:80/compile` to download a zip.
