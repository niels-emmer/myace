---
name: Model Evaluation
description: Evaluation methodology — split strategy, metric selection, baseline comparison, failure mode analysis.
version: "1.0.0"
priority: 55
compatibility: [opencode, claude-code, cursor]
tags: [ml, evaluation, metrics]
---
## Purpose

Ensure models are evaluated rigorously before deployment decisions are made.

## When to use it

After training, before declaring a model ready for deployment review.

## Checklist

- **Split strategy**: holdout for large datasets, k-fold or stratified for smaller ones.
- **Metric selection**: classification (precision/recall/F1/AUC-ROC/AUC-PR), regression (MAE/RMSE/MAPE/R²), ranking (NDCG/MAP). Pick metrics that match the business problem.
- **Baseline comparison**: compare against a simple heuristic, dummy classifier, or previous model version.
- **Confidence intervals**: report uncertainty around metrics, not just point estimates.
- **Calibration**: for probabilistic models, check calibration curves.
- **Per-slice evaluation**: evaluate on subgroups (by category, value range, data source) to find failure pockets.
- **Failure mode documentation**: list known failure cases, edge behaviors, and conditions where performance degrades.

## Expected output

An evaluation report with metrics, baseline comparison, and documented failure modes, logged to the experiment tracker.
