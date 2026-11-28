---
name: LLM Evals
description: How to design, run and maintain evaluations for prompts, agents and model changes. Use before changing a prompt, model or tool set, or when a quality regression is reported.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [ai, evals, testing]
---
## Purpose

Replace opinion with measurement: a small, versioned eval set that shows whether a change made the system better, worse or just different.

## When to use it

Before changing a prompt, model, retrieval setup or tool definition, when choosing between models, and when production feedback shows a failure the current evals did not catch.

## Checklist

- **Define success first**: write what 'good' means for the task (correct answer, format compliance, refusal behaviour, tool-call accuracy, latency, cost) before building the set.
- **Build the set from real inputs**: sample production or representative cases, include hard and adversarial ones, and add every real failure as a permanent case. Keep it small enough to run on every change.
- **Grade deterministically where you can**: exact match, schema validity, unit tests on generated code, retrieval hit rate. Use an LLM judge only for what code cannot grade, with a written rubric, a different model from the one under test where possible, and a human-labelled sample to measure the judge's agreement.
- **Compare, do not eyeball**: run before and after on the same set, repeat runs where outputs vary, and report the difference with its spread, not a single run.
- **Slice results**: by task type, input length and difficulty so a gain on average does not hide a regression somewhere.
- **Guard the held-out set**: do not tune prompts against the cases you report on; keep a separate set for final checks.
- **Version everything**: eval set, prompt, model identifier, parameters and judge, so a result can be reproduced.
- **Gate changes**: define a threshold and block merges that fall below it; re-run the evals when the model provider updates a model alias.
- **Watch production**: sample live traffic into the eval pipeline and review failures regularly. Do not put personal data into eval sets without the privacy controls the project requires.

## Expected output

An eval report comparing baseline and candidate on a versioned set, with the grading method, variance, slices and a pass/fail decision.
