---
name: Python Project Layout
description: Project layout, packaging and dependency-locking conventions for Python. Use when starting a project or changing its build or dependencies.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli, pi-dev]
tags: [python, packaging, build]
---
## Purpose

Make a Python project installable and reproducible from a clean checkout with one command.

## When to use it

When creating a project, adding or upgrading dependencies, or fixing 'works on my machine' environment drift.

## Checklist

- **Layout**: `src/<package>/` for libraries and services, `tests/` beside it; one `pyproject.toml` as the single source of metadata and tool config.
- **Lock**: a committed lockfile for applications; libraries declare compatible ranges and test against the lowest and highest supported versions.
- **Groups**: separate runtime, dev, test and docs dependencies (dependency groups or extras).
- **Interpreter**: pin the supported Python range in `requires-python` and make CI run at least the floor.
- **Entry points**: expose commands through `[project.scripts]`, not `python path/to/file.py`.
- **CI**: install strictly from the lockfile and fail if it is out of date.
- **Hygiene**: no `requirements.txt` that duplicates `pyproject.toml` unless it is generated from it.

## Expected output

A repository where `clone`, one install command and one test command give a working environment, and a dependency bump is a reviewable lockfile diff.
