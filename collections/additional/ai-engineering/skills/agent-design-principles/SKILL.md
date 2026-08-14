---
name: Agent Design Principles
description: A checklist for designing agent personas, skills, and multi-agent pipelines that stay reliable as they grow — grounded in the 12-factor-agents principles.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [ai, agents, prompt-engineering, principles]
---
## Purpose

Agent/prompt quality tends to erode the same way code quality does when there's no checklist forcing a second look: an agent persona quietly grows to cover more than it should, context accumulates instead of getting curated, and failures get retried with the same full error dump instead of a compacted summary. This skill exists to catch that drift when authoring or revising an agent, skill, or command — for this repo's own artifacts, or for a target repo an `ai-engineer`/`prompt-engineer` is working in.

It draws specific, named ideas from [12-factor-agents](https://github.com/humanlayer/12-factor-agents) (humanlayer, Apache-2.0) — cited individually below, not reproduced wholesale; read the source for the full essays behind each one.

## When to use it

Before adding a new agent persona or skill, before letting an existing one grow a new responsibility, and when designing how multiple agents hand work to each other (an orchestrator pattern, a pipeline of specialist agents).

## The checklist

1. **Small, focused agents** — Does this persona do one job well, with a clearly stated permission posture (what it does freely, what it never does)? If a persona's responsibility list is growing past what fits in a short paragraph, it's probably two personas.
2. **Own your control flow** — Is the sequence between stages/agents explicit (a named handoff, like this repo's `orchestrator` → `builder` → `verifier` pattern), rather than an open-ended loop hoping the model figures out when to stop or what to do next?
3. **Own your context window** — For each stage, is it clear what context it actually needs? Passing everything by default (full history, every file touched so far) degrades output quality as much as passing too little.
4. **Compact errors into context** — When a step fails and gets retried, is the failure summarized (what was tried, what broke, what's already ruled out) rather than re-fed as a raw stack trace or full tool output on every attempt?
5. **Unify execution state** — Is task progress tracked in one place (e.g. this repo's `plan-tracking`/`memory-system` skills) rather than scattered across an agent's implicit memory of the conversation, which doesn't survive a session boundary?
6. **Natural language to concrete action** — Are instructions phrased as checkable, concrete steps ("run the test suite and quote the result") rather than vague goals ("make sure it's tested")? A step that can't be verified as done or not-done will eventually be skipped.
7. **Resumability** — If this session ended right now, could a fresh session pick up correctly from persisted state (memory files, task tracking) rather than needing the prior conversation's context to make sense of where things stand?

## Expected output

When used to review an agent/skill/pipeline design, a short list of which checklist items pass and which don't, with a concrete fix for each failing item — not just a restatement of the principle.
