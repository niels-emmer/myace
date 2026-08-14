---
description: Create or update the project's constitution — the small set of non-negotiable product/architecture principles every spec, plan, and implementation must be checked against.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
---
1. Read `docs/constitution.md` if it exists; otherwise this is a first-time setup.
2. Gather principles from the user's request and, on first setup, from the codebase itself — recurring invariants already enforced in code or docs (e.g., an existing "never hard-delete user data" rule) are candidates for promotion to a constitution principle, not just a comment.
3. Write each principle as a short, checkable MUST/SHOULD statement with a one-line rationale — not a vague value statement. "All external API responses MUST be versioned" is checkable; "we care about API stability" is not.
4. Keep the set small — five to ten principles. A constitution that tries to cover everything stops functioning as a filter; it should list the things that are expensive to get wrong and easy to accidentally violate.
5. Version the document: bump the major segment on a principle removed or redefined, minor on a principle added, patch on a wording clarification with no behavioral change. Record the bump and what changed at the top of the file.
6. Save to `docs/constitution.md`. This is a different document from `AGENTS.md` — it governs what the product is allowed to do, not how an agent behaves while working in the repo.
7. Report which principles were added, changed, or removed, so the user can catch an unintended change before it becomes the standard every future spec is checked against.
