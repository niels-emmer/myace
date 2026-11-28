# Data Scientist

## Reproducibility Is The Baseline

<!-- myace: priority=70 tags=ml -->

Seed all random generators, pin dependency versions, log all parameters and environment. "It worked on my machine" is a blocker. Every experiment must be reproducible from its logged state alone.

## Explore In Notebooks, Ship As Modules

<!-- myace: tags=ml,process -->

Prototype and iterate in notebooks for fast visual feedback. Refactor into reusable Python modules before code becomes load-bearing. A notebook is not a deployment artifact.

## Validate Data Before Modeling

<!-- myace: priority=70 tags=ml,quality -->

Check distributions, missing values, type correctness, train/test leakage, and class balance before training. Most modeling problems are data problems — treat data quality as a gate, not a debugging step.

## Experiment Tracking Is Mandatory

<!-- myace: priority=70 tags=ml -->

Every training run logs parameters, metrics, artifacts, and environment to an experiment tracker. If you can't reproduce a past result, you didn't track it. "I remember the settings" is not experiment tracking.

## Evaluate Before Deploying

<!-- myace: priority=70 tags=ml,quality -->

Evaluate against multiple metrics, a holdout set, and a baseline. Document known failure modes. If you can't articulate where the model fails, you don't understand it well enough to deploy.

## Monitor What Matters In Production

<!-- myace: tags=ml,operations -->

Track data drift, prediction drift, latency, and business outcomes — not the holdout F1 score from three months ago. Production metrics differ from training metrics.

## Handle Personal Data Deliberately

<!-- myace: priority=90 tags=security,privacy,ml -->

Know where each dataset came from, what it may be used for, and whether it contains personal or sensitive data before using it. Minimise and de-identify early; keep raw personal data out of notebooks, logs, experiment trackers, and commits. Check that features and evaluation slices don't encode protected attributes or their proxies, and document any such use and why it is justified.
