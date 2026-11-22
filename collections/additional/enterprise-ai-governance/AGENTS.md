# Enterprise AI Governance

## Classify Before You Send

Classify data as PUBLIC, INTERNAL, CONFIDENTIAL, or REGULATED before it reaches any model or external service. When a payload is ambiguous, treat it as the higher class, send the minimum data needed, and never reclassify data merely to fit an available route.

## Confirm Before Production Or Publication

Any action against a protected target requires explicit confirmation first: a name containing `prod` or `production`, shared routing or network configuration, a migration, an IAM or firewall change, or a publish, push to a protected branch, or deletion. State the blast radius and the rollback before proceeding.

## Keep A Zero-Egress Path

Maintain at least one inference route that makes no third-party network calls, and keep CONFIDENTIAL work on it. REGULATED data never goes to a cloud model, regardless of the provider's terms.

## Attribute AI-Authored Changes

Every change records what it did, why, and whether it was AI-authored, human-authored, or AI-assisted. Mark AI-authored commits in the body, state attribution in the PR, and never present an agent's assumption as a verified fact.
