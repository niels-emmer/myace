---
name: Reproducibility Standards
description: Seeding, dependency pinning, environment capture, and data versioning for fully reproducible ML workflows.
version: "1.0.0"
priority: 60
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [ml, reproducibility, engineering]
---
## Purpose

Make every result reproducible from source control + logged state alone.

## When to use it

Setting up a new project, starting a new experiment, or preparing work for handoff.

## Checklist

- **Seed all random generators**: numpy, `random`, torch, tensorflow, and any other stochastic components. Log seeds.
- **Pin dependencies**: use lockfiles (`requirements.txt`, `poetry.lock`, `conda-lock`) — not loose version ranges.
- **Capture environment**: Dockerfile or conda env.yml that reproduces the exact runtime.
- **Version data**: use DVC, hash-based manifests, or snapshot the exact dataset version used.
- **Log transforms**: every preprocessing step (scaling, encoding, imputation) must be logged and reproducible.
- **Pipeline DAG**: capture the full pipeline graph with input/output hashes per step.

## Expected output

A project setup where `git clone → install → run` reproduces the same results, verified by comparing logged metrics.
