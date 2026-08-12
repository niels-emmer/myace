---
description: Scaffold a new tracked experiment — create notebook, set up tracking, log baseline, define success criteria.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
---
1. Create experiment notebook with a descriptive name following the run naming convention.
2. Initialize experiment tracker connection and log the environment (git hash, dependency versions).
3. Set all random seeds and log them.
4. Define success criteria: target metric(s), baseline to beat, minimum improvement threshold.
5. Load and validate data using the data-validation skill's checklist.
6. Implement the initial approach, logging all parameters before training.
7. Run and log results. Compare against baseline.
8. Write a short summary of what was tried, what worked, and what didn't.
