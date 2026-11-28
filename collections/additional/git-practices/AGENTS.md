# Git Practices

## Never Commit Secrets

<!-- myace: priority=90 tags=git,secrets -->

Secrets, tokens, keys, passwords, and environment files never enter a commit. Commit the example env file with safe defaults, keep the real file gitignored, and scan the staged diff before every commit. If a secret is already tracked, treat removing it and rotating it as the same task.

## Commit One Concern At A Time

<!-- myace: priority=50 tags=git,process -->

Each commit should do one thing and explain why. Use a conventional `<type>(<scope>): <summary>` subject, put the reasoning in the body, and keep unrelated edits out of the same commit so a revert can undo exactly one change.

## Protect Shared Branches

<!-- myace: priority=70 tags=git,safety -->

Never force-push a shared branch or one with an open pull request. Rebase or merge the latest default branch before opening a PR, and resolve conflicts locally rather than rewriting history others may already have.

## Green Before Merge

<!-- myace: priority=70 tags=git,quality -->

A change merges only when the pipeline is green and the diff matches its stated intent. Do not merge with failing required checks, and do not treat a passing suite as proof the feature works if the running app was never exercised.
