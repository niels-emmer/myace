# Architecture Decision Records

An ADR is a short document that captures a decision, the context that
forced it, and what was given up to make it — so a future contributor (human
or agent) doesn't have to reverse-engineer the reasoning from a diff, and
doesn't accidentally re-litigate or undo a decision without knowing why it
was made.

## When to write one

Write an ADR when a change is **non-obvious and expensive to reverse** —
picking an auth strategy, a data model shape, a deployment topology, or
anything where a reasonable engineer could have gone a different direction
and you want the reasoning on record. Don't write one for routine features,
bug fixes, or anything where the code itself is the whole explanation.

## Format

Copy [`template.md`](template.md). Keep it short — a good ADR fits on one
screen. Number sequentially, never renumber or delete a past ADR even if it's
superseded; add a new one and mark the old one's status as `Superseded by
ADR-00XX`.

## Index

| # | Title | Status |
|---|---|---|
| [0001](0001-canonical-ir-as-markdown-with-frontmatter.md) | Canonical IR as Markdown with YAML frontmatter | Accepted |
| [0002](0002-session-cookie-auth.md) | Session cookies (not JWT/localStorage) for the web session | Accepted |
| [0003](0003-ownership-based-authorization.md) | Ownership + visibility authorization, not RBAC/teams | Accepted |
| [0004](0004-github-export-via-rest-api.md) | GitHub export via REST API, not a local git clone/push | Accepted |
| [0005](0005-email-password-baseline-auth.md) | Email+password as the baseline auth method, SSO optional | Accepted |
| [0006](0006-encrypted-admin-editable-secrets.md) | Encrypted admin-editable secrets in the database | Accepted |
| [0007](0007-additive-user-role-column.md) | Additive `role` column alongside `is_admin` | Accepted |
| [0008](0008-collection-moderation-state-machine.md) | Collection moderation state machine replaces self-serve publish | Accepted |
| [0009](0009-manifest-based-drift-detection.md) | Local manifest file, not new server state, for drift detection | Accepted |
| [0010](0010-structured-handoff-field.md) | `handoff_to` field on agent artifacts, not a new join table | Accepted |
| [0011](0011-public-demo-sandbox.md) | A stateless, rate-limited public demo endpoint | Accepted |
