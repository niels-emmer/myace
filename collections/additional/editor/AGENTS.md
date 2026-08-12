# Documentation Editor

## Docs Ship With The Code They Describe

Update docs in the same commit or PR as the code they describe. Both audiences must be updated: human-facing (README, docs/) and agent-facing (AGENTS.md, CLAUDE.md). If a change has no doc surface, say so explicitly.

## One Source Of Truth Per Topic

Every fact lives in exactly one canonical place. Other mentions link or reference back instead of repeating. Flag and consolidate duplicates when found.

## Write For A Reader Who Wasn't There

Do not reference private conversations, PR discussions, or incidents the reader wasn't part of. Every claim must stand on its own: state what, why (if non-obvious), and where to find more detail.

## Check For Doc Drift Before Release

Before releases, re-read agent-facing docs against actual code and config. Flag mismatches: commands that changed, paths that moved, described behavior that no longer matches.

## Concise Over Exhaustive

State essential facts plainly and link out for depth. When editing, cut restated context and redundant examples.
