@AGENTS.md

## Claude Code

This file provides guidance to Claude Code (claude.ai/code) specifically.
Everything else — what the project is, commands, architecture, rules, and
gotchas — lives in the imported `AGENTS.md` above, which is the single
source of truth shared by every AI coding agent working in this repo. Only
genuinely Claude-Code-specific notes belong below; don't duplicate
`AGENTS.md` content here.

- **Don't confuse this file with the `claude_code` adapter's output.**
  `backend/app/adapters/claude_code.py` *generates* a `CLAUDE.md` +
  `.claude/agents/*.md` + `.claude/workflows/*.md` file set as one of
  MyACE's compile targets — that's a MyACE user's compiled profile output,
  unrelated to this file, which guides Claude Code while it works on the
  MyACE codebase itself.
- `.claude/launch.json` defines the `frontend-dev` preview-server config
  (`npm --prefix frontend run dev`, port 5173) that Claude Code's
  Browser/preview tooling uses to open a live preview. It expects the
  backend already reachable at `localhost:8000` — run
  `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d`
  first (see Commands in `AGENTS.md`), then start the preview.
