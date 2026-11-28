# Shared governance core (authoring source — never seeded)

The four base packs under `collections/base/` each ship **self-contained**.
This directory is only the single place the rules they have in common are
written, so they can't drift apart. Nothing here is seeded, listed, or visible
in the product.

- `rules/<slug>.md` — the canonical body of a core rule.
- `rules/<slug>.<pack>.md` — an optional per-pack wording of the same rule
  (same name and intent, adapted to that pack).
- `packs.json` — the rule list (slug, heading name, `priority`, `tags`, and an
  optional `packs` list limiting it to some packs), the shared `skills`, pack
  titles, and an optional per-pack `exclude` list.
- `skills/<slug>.md` (and `<slug>.<pack>.md`) — a whole SKILL.md generated into
  each listed pack's `skills/<slug>/SKILL.md`.

Each pack's own rules live in `collections/base/<pack>/AGENTS.pack.md`. The
shipped `AGENTS.md` is **generated** from that file plus this core — don't edit
it by hand:

```bash
python scripts/sync_shared_core.py          # regenerate all four AGENTS.md
python scripts/sync_shared_core.py --check  # CI: fail if any is out of date
```

`permissions.json` here holds the shared global ask/deny rules (ADR-0019,
phase 2); a pack adds its own in `permissions.pack.json`. Both are merged into
each pack's generated `permissions.json`.
