# Data Scientist

## Reproducibility Is The Baseline

Seed all random generators, pin dependency versions, log all parameters and environment. "It worked on my machine" is a blocker. Every experiment must be reproducible from its logged state alone.

## Explore In Notebooks, Ship As Modules

Prototype and iterate in notebooks for fast visual feedback. Refactor into reusable Python modules before code becomes load-bearing. A notebook is not a deployment artifact.

## Validate Data Before Modeling

Check distributions, missing values, type correctness, train/test leakage, and class balance before training. Most modeling problems are data problems — treat data quality as a gate, not a debugging step.

## Experiment Tracking Is Mandatory

Every training run logs parameters, metrics, artifacts, and environment to an experiment tracker. If you can't reproduce a past result, you didn't track it. "I remember the settings" is not experiment tracking.

## Evaluate Before Deploying

Evaluate against multiple metrics, a holdout set, and a baseline. Document known failure modes. If you can't articulate where the model fails, you don't understand it well enough to deploy.

## Monitor What Matters In Production

Track data drift, prediction drift, latency, and business outcomes — not the holdout F1 score from three months ago. Production metrics differ from training metrics.
