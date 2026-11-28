# Design & Scaffold

## Decide Before Building

<!-- myace: priority=50 tags=process,design -->

For anything under-specified, hard to reverse, or shaped more than one reasonable way, settle the design before writing code. Turn the problem into a tree of decisions, ask the questions that are answerable now, and do not start implementation while a load-bearing choice is still silently assumed.

## Scaffold Complete On Day One

<!-- myace: priority=50 tags=process,scaffold -->

A new repository ships its contract, tests, docs, environment template, container definition, and CI in the first commit — not as later cleanup. `AGENTS.md` comes first because it is the only artifact a fresh contributor or agent reads before doing anything.

## Verify Dependency Provenance

<!-- myace: priority=90 tags=security,dependencies -->

Before adding a dependency, confirm its license, maintenance status, known vulnerabilities, and that the package comes from the expected registry and source. Pin an exact version, and never adopt a package whose license or provenance you could not confirm.
