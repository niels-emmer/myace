# Documentation Editor

Rules for anyone keeping READMEs, agent-facing instruction files, and other project docs accurate and readable. Layer this on top of a base rule set — it adds documentation discipline, it doesn't replace general engineering judgment.

## Docs Ship With The Code They Describe

A change isn't complete when the code works — it's complete when the docs that describe it are updated in the same commit or pull request. "I'll document it in a follow-up" is how docs quietly stop matching reality: the follow-up gets deprioritized, the next person reads stale instructions, and nobody notices until something breaks or an agent acts on outdated guidance.

This applies to both audiences at once: human-facing docs (README, CONTRIBUTING, docs/) and agent-facing instruction files (AGENTS.md, CLAUDE.md, or similar). A behavior change that only updates one of the two is half done. If a change genuinely has no doc surface — a pure refactor with no observable behavior change — that's fine, but say so explicitly rather than skipping the question.

## One Source Of Truth Per Topic

Every fact — a setup command, a config default, an architectural decision — should live in exactly one canonical place. When the same fact is written out separately in two documents, the two copies will eventually disagree, because someone will update one and forget the other. Nobody will know which one is current.

Pick the most natural home for each fact (usually the doc closest to the code it describes) and have every other mention link or reference back to it instead of repeating it. If you find a fact duplicated in the wild, that's worth flagging and consolidating, not just adding a third copy.

## Write For A Reader Who Wasn't There

Docs are read by people (and agents) with no memory of the conversation, PR discussion, or incident that produced them. Avoid references that only make sense to someone who was in the room: "the fix for the thing we discussed," "as done in the auth PR," "like we talked about." A reader who wasn't there has no way to resolve those.

Every claim in a doc should stand on its own: state what the thing is, why it's done this way if that's non-obvious, and where to look for more detail if needed. If you're tempted to reference an external conversation, pull the actual reason into the doc instead — the conversation will be gone long before the doc is.

## Check For Doc Drift Before Release

Agent-facing instruction docs (AGENTS.md, CLAUDE.md-style files) are especially prone to drift because nothing forces them to change when the underlying code does — they're read by agents, not exercised by tests. Before a release, or on a regular cadence, deliberately re-read these docs against the actual current code and configuration, not against what you remember it doing.

Look specifically for: commands that no longer exist or changed their flags, file paths that moved, described behavior that was since changed or removed, and rules that reference a mechanism that's since been replaced. Flag every mismatch found — don't silently let drift accumulate until someone (or some agent) is misled by it.

## Concise Over Exhaustive

A short doc that people and agents actually read beats a comprehensive one that gets skipped because it's too long to scan. Default to stating the essential facts plainly and linking out to deeper detail (a dedicated doc, a code comment, an ADR) rather than inlining everything into one file.

When editing an existing doc, look for opportunities to cut restated context, redundant examples, or explanations of things that are obvious from the code itself. Cutting words is worth doing even when nothing factual changes — the doc that says the same thing in fewer words is strictly better for the next reader.
