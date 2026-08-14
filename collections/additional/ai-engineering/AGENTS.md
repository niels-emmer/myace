# AI / LLM Engineering

## Model Output Is Untrusted Input

Anything an LLM call returns — a tool-call argument, a structured-output
field, text destined for a template or a shell command — gets the same
treatment as user input at a trust boundary: validated, typed, and never
interpolated unescaped into a query, path, or command. This is the
`ai-engineer` agent's version of the `security-checklist` skill's injection
category, and it applies even when the model call is your own prompt with
no external user in the loop — a model can still be steered by content it
retrieved (a scraped page, a tool result) into producing something the
calling code shouldn't trust blindly.

## Prompt Changes Need Evals, Not Vibes

A prompt or system-instruction change that isn't checked against a
concrete before/after comparison on real (or representative) inputs is a
guess wearing a diff. The `prompt-engineer` agent owns defining what
"better" means for a given prompt — task success rate, format compliance,
a specific failure mode no longer occurring — before changing it, not
after, so a regression is caught by the eval rather than by a user.

## Context Is Curated, Not Accumulated

Don't let an agent's context window grow by default accretion — every
message, tool result, and file excerpt appended forever. The
`context-manager` agent (and the `agent-design-principles` skill) exist to
make an explicit call about what a given step actually needs: recent
decisions and their rationale, not the full history that produced them;
the relevant file excerpt, not the whole file; a compacted summary of a
failed attempt, not its full stack trace on every retry.

---

Grounded in [12-factor-agents](https://github.com/humanlayer/12-factor-agents)
(humanlayer, Apache-2.0) — see the `agent-design-principles` skill for the
specific factors this collection draws on, cited individually rather than
reproduced wholesale.
