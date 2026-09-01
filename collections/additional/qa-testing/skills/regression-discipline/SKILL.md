---
name: Regression Discipline
description: The rule that every bug fix ships with a test that fails on the old code and passes on the new — and how to write that test well.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [testing, regression, bug-fixes]
---
## Purpose

A bug fix without a regression test isn't confirmed to have fixed anything — it's confirmed to compile. The regression test is what proves the fix works and what stops the bug from coming back. This skill is a checklist for writing regression tests that actually guard the behavior.

## When to use it

Every time a bug is fixed. Also when reviewing a fix to confirm the regression test is real, not a formality.

## Checklist

- **Write the test against the bug, not the fix.** The test should reproduce the reported failure mode — the input that triggered the bug, the behavior that was wrong. It should fail on the old code and pass on the new.
- **Confirm it fails first.** Run the test against the code before the fix and watch it fail. A regression test that passes on broken code isn't testing the bug.
- **Name it for the behavior.** The test name should say what behavior is guarded ("rejects empty input", "rolls back on partial failure"), not "test_fix_123".
- **Cover the boundary, not just the example.** If the bug was an off-by-one, test the boundary values, not just the one that happened to fail.
- **Check for related paths.** If the bug was a null dereference in one call site, the same root cause may exist elsewhere — a regression test on the shared path guards all of them.
- **Don't weaken assertions.** A regression test that asserts less than the bug demonstrated (e.g. "doesn't crash" instead of "returns the correct value") lets the bug half-return.

## Expected output

For every bug fix, a test that reproduces the reported failure, fails on the old code, passes on the new, and is named for the behavior it guards — so the fix is proven and the regression is caught if it ever returns.