---
name: Data Validation
description: Data quality checks to run before modeling — distribution summaries, leakage detection, class balance.
version: "1.0.0"
priority: 55
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [ml, data, validation]
---
## Purpose

Catch data problems before they waste training time or produce misleading models.

## When to use it

Before every modeling pass, especially when working with new or updated data.

## Checklist

- **Shape and type check**: confirm columns, dtypes, and row counts match expectations.
- **Null distribution**: count and visualize missing values per column; decide on imputation strategy.
- **Value ranges**: check min/max/unique values for each feature; flag out-of-domain values.
- **Train/test distribution**: compare feature distributions across splits (KS test or visualization); flag drift.
- **Target leakage scan**: check for time-based leakage, ID columns, future-looking features in training data.
- **Class imbalance**: quantify target distribution; plan for stratification or weighting if needed.
- **Temporal ordering**: for time-series data, confirm no future data leaks into training windows.

## Expected output

A data validation report with PASS/FAIL per check, attached to the experiment tracker entry.
