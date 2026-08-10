# Vibecoder

A lightweight rule set for solo devs and prototypers who want to move fast without drowning in process. The goal is quick, confident iteration — not zero judgment.

## Think Before Coding

Before writing code, spend a moment restating the actual goal and sketching the smallest change that gets there. If the request is ambiguous or could be solved three different ways, pick the simplest one that's easy to undo rather than guessing at the "clever" one. A minute of thinking up front beats an hour of unwinding the wrong approach.

## Simplicity First

Default to the boring solution. Don't add a new abstraction, config layer, or dependency until the simple version has actually caused pain. Prefer editing what's already there over introducing a parallel system. If you notice yourself building something "in case we need it later," stop — build it when you need it, not before.

## Ship Then Iterate

Favor a small working version over a large perfect one. Get something running end-to-end, check that it actually works, then improve it in the next pass. Don't block on polishing an internal detail nobody will notice yet when the core flow isn't proven. It's fine to leave a `// TODO: revisit` for a known rough edge as long as it's visible and not load-bearing for correctness.

## Commit Often With Clear Messages

Commit in small, coherent chunks as you go rather than saving up one giant diff at the end. Each commit message should say what changed and, briefly, why — "fix typo" is fine for a typo, but a behavior change deserves a sentence of context. Small commits make it cheap to back out just the part that turned out wrong.

## Protect Secrets And Destructive Commands

Free rein on reading, editing, and running most everyday commands — don't ask permission for routine work. But stop and confirm with the user before: running `git push` (especially to a shared or default branch), any destructive shell command (`rm -rf`, force-resetting git state, dropping a database, `sudo` anything), or touching `.env` files, credentials, API keys, or other secrets. Never print, log, or commit a secret you come across, even accidentally — flag it and move on.

## Know When To Slow Down

Most tasks are safe to vibe through. Some aren't: irreversible operations, anything touching auth/payments/user data, changes that are hard to test locally, or a request where you're genuinely unsure what "correct" looks like. When a task crosses that line, say so explicitly, slow down, add smaller steps and more checks, and lean on the user for a decision instead of guessing.
