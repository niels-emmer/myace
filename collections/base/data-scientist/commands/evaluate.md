---
description: Pre-deployment evaluation checklist — holdout eval, baseline comparison, leakage scan, failure mode documentation.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
---
1. Run the model against the held-out test set and log all metrics.
2. Compare results against the defined baseline — is the improvement meaningful and statistically significant.
3. Run a data leakage scan on the full pipeline (features → split → training).
4. Evaluate on slices/subgroups to identify failure pockets.
5. Document known failure modes: conditions where the model performs poorly, edge cases it doesn't handle.
6. Update the model registry entry with evaluation results and artifact location.
7. Flag any gap between training metrics and expected production performance.
