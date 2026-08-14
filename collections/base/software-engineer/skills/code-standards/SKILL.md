---
name: Code Standards
description: Naming, structure, and consistency conventions for keeping a codebase readable and predictable as it grows.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [style, consistency, readability]
---
## Purpose

Consistency lowers the cost of reading code more than any individual stylistic choice does. A codebase where every module solves the same kind of problem the same way is faster to work in than one where each file reflects whoever wrote it last, even if some of those individual choices were locally "better." This skill is about matching what's already there before introducing something new.

## When to use it

Every time you write or modify code — this isn't a one-off pass, it's the default posture. Reach for it explicitly when starting work in an unfamiliar part of a codebase, or when you notice you're about to introduce a naming or structural pattern that doesn't obviously match its neighbors.

## Steps / checklist

1. **Read before writing.** Before adding a function, class, or module, look at 2-3 existing examples of the same kind of thing nearby. Match their naming style, argument order, error-handling approach, and level of abstraction rather than picking your own.
2. **Names describe what, not how.** A function name should tell a reader what it accomplishes (`validate_user_email`) not the mechanism (`check_regex_match`) unless the mechanism is the point. Avoid abbreviations that aren't already established in the codebase.
3. **One level of abstraction per function.** If a function mixes high-level orchestration with low-level detail (looping, string parsing) in the same block, that's usually a sign it should be split — not because smaller is always better, but because mixed levels are harder to read at a glance.
4. **Match the project's actual conventions, not a generic style guide.** If the codebase uses `snake_case` for functions and you're working in a section that already does that, don't introduce `camelCase` because it's "more standard" elsewhere. Check for a linter config or existing style doc first — it's authoritative over personal preference.
5. **Keep related things together.** A function and the tests that exercise it, a type and the code that constructs it, a constant and the logic that depends on its value — colocate where the existing project structure allows it, rather than scattering by category (all constants in one file regardless of what they're for) if that's not already the established pattern.
6. **Prefer explicit over clever.** A slightly longer, obvious version of something beats a dense one-liner that needs a comment to explain what it does. If you need the comment, that's a signal to simplify the code instead of just documenting the cleverness.
7. **Don't reformat unrelated code.** Whitespace-only or style-only changes to lines you didn't otherwise touch bloat the diff and make the real change harder to review — leave them alone unless the task is specifically a formatting pass.

## Expected output

Code that a reviewer familiar with the codebase could plausibly mistake for having been written by whoever wrote the surrounding code — not because individuality is bad, but because at review time, "does this look like it belongs here" is a fast, reliable proxy for "did the author actually understand the existing system before extending it."
