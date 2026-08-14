---
name: Experiment Tracking
description: How to properly set up experiment logging — what to log, how to name runs, how to compare and recover results.
version: "1.0.0"
priority: 60
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [ml, experiments, tracking]
---
## Purpose

Ensure every experiment is reproducible from its logged state alone.

## When to use it

Every training run, every data transformation, every evaluation.

## Checklist

- **Run naming**: `{date}-{objective}-{attempt}` (e.g. `2026-08-12-classifier-lr-search-03`).
- **Seed everything**: numpy, python `random`, torch, tensorflow — log which seeds were used.
- **Log parameters**: hyperparameters, data splits, preprocessing choices, model architecture.
- **Log metrics**: final metrics per split (train/val/test), per-epoch metrics if relevant.
- **Log artifacts**: model weights, predictions, feature importance plots, confusion matrices.
- **Log environment**: Python version, dependency versions (lockfile or `pip freeze`), git commit hash.
- **Compare runs**: use the tracker's comparison view or export to a structured format.
- **Recover**: from a logged run, you should be able to reproduce the exact result.

## Expected output

A tracked run that another person or agent can reproduce without asking the original author for details.
