# First-run wizard and setup lifecycle (Phase 2)

Phase 2 of the v2.0 onboarding/usage revamp is **frontend-only**. It adds the
five-step first-run wizard, folds pack acquisition into one import branch, and
turns the setup page and install panel into the place that answers *"what is
installed, and is it current?"*. The design proposal is recorded in
[`plans/v2.0-onboarding-revamp.md`](plans/v2.0-onboarding-revamp.md) and the
accepted review artifact's sections 4.3, 6.2, 6.2b, 6.6, 6.7, 7.2, and Phase 2
of section 9; this file records what was actually built and the rules that must
survive future edits.

Vocabulary follows AGENTS.md rule 42: **Pack** (`Collection`), **Setup**
(`Profile`), **Install** (compile + pull/apply), **Item** (`Artifact`).

## Routes and files

| Path | Component | Purpose |
|---|---|---|
| `/onboarding` | `pages/Onboarding.tsx` | Five-step wizard |
| `/packs/import` | `pages/ImportPage.tsx` | Three source cards + existing scan/import flow |
| `/setups/:id` | `pages/ProfileDetail.tsx` | Packs, warnings, framework matrix, advanced |
| `/setups/:id/install` | `pages/TargetExporter.tsx` | Target/location + install methods |

Supporting modules created by this phase, kept out of the Phase 5 hotspots
(`lib/api.ts`, `types/index.ts`):

- `lib/setupApi.ts` — onboarding completion, install claims, companion
  `/health` + `/audit` + `/apply/*`, and the localStorage draft.
- `types/setup.ts` — install/claim types, framework paths, matrix building,
  the owner-scoped `pack_unavailable` helpers.
- `components/InstallMethodPanel.tsx` — the per-target methods shared by the
  wizard's final step and the install page, so the two cannot drift.

## The five steps

1. **What do you use?** Multi-select of enabled adapters (`GET /adapters`).
   When the local companion answers, `POST /audit {path:"~"}` marks frameworks
   it detected ("detected on this machine") and preselects them *only when the
   draft has no framework selection yet*. Detection is optional; the step works
   without a companion.
2. **What should your agent know?** The four curated bundles from
   `lib/bundles.ts`, plus every add-on pack, plus a *Browse all packs* link.
   The escape hatch **"I already have configs — import them"** goes to
   `/packs/import?return=onboarding`.
3. **Review and name.** Chosen packs with kind labels, deduplicated item counts
   by type, name (default "My setup") and optional description. *Customize
   items* is a collapsed explainer: item toggles live on the setup page after
   creation, so no toggle is hidden behind an unfinished step.
4. **Where should it go?** One row per selected framework with **This project**
   and **This machine**, resolved paths shown, and machine disabled for
   project-only outputs. Machine is the default because the shipped companion
   does not report a project root; if a companion ever adds `project_root` to
   `/health`, the default becomes project.
5. **Install.** Per-framework rows with the location and an install claim
   status, and the shared `InstallMethodPanel` for the selected framework:
   **Download .zip**, **CLI**, and **Install directly** only when the
   companion reports `apply.supported` for that target and location. The
   wizard's primary button then reads **Finish**.

Creating the setup happens on the step 4 → 5 transition:
`POST /profiles` with `target_frameworks` (and `base_collection_id` +
`additional_collection_ids`). Moving back and re-advancing uses
`PUT /profiles/{id}` so the draft does not leave orphan profiles behind.

## Resume and skip

- The draft lives in `localStorage` under `myace.onboarding.v1`
  (`loadDraft`/`saveDraft`/`clearDraft`).
- Step and pack also live in the URL: `/onboarding?step=3&pack=<collection id>`.
  The URL wins over a stored draft, which is what makes the import branch's
  return link work on any device.
- `?pack=` naming an add-on never silently becomes the base: the wizard clamps
  to step 2 and shows the pairing prompt.
- **Skip for now** (and **Finish**) call `PATCH /auth/me/onboarding
  {completed:true}`, clear the draft, refresh the user, and navigate — Home for
  a skip, `/setups/{id}` after a finish. `User.onboarding_completed_at` is
  cross-device; localStorage is only the draft.

## Add-on pairing

Choosing an add-on with no base selected opens *"Pair X with a starting
point"*. The base list is sorted by `download_count` and the most-used base is
preselected, but **nothing is chosen automatically** — the user confirms. Note
that `download_count` is advisory and tamperable (invariant 25 / ADR-0015): it
is only a default suggestion here, never a ranking or popularity claim.

## Install methods and claims

| Method | What happens | Claim `method` |
|---|---|---|
| Download `.zip` | `POST /profiles/compile/zip`, browser save | `zip` |
| CLI | Copies `myace pull --profile '<name>' --target <target>` (the name is POSIX single-quoted) | `cli` |
| Install directly | Companion `/apply/preview` → explicit diff confirm → `/apply` | `apply` |

Every successful action posts `POST /profiles/{id}/installs
{target, location, method}`. **A claim is not verification.** `SyncStatus`
(fed only by `myace check --report`) remains the sole verified source; a claim
only means the user said they installed it, and every surface labels it
"installed, not verified" in blue, never a green check. A failed claim request
is reported softly — the file operation already succeeded.

The setup matrix applies this precedence:

```
verified (SyncStatus in sync)
  > drift (SyncStatus out of sync, or locally modified files)
  > installed, not verified (claim, no SyncStatus)
  > not installed
```

`Verify` copies `myace check --target <target> --report`; `Install`/`Reinstall`
and `View files` open `/setups/:id/install?target=<target>`. Location on the
matrix comes from the install claim only — a sync report does not carry one, so
a verified row installed by the CLI may show `—`.

## Warnings, and the owner-scoped `pack_unavailable` notice

Compile warnings (`name_collision`, `dangling_handoff`, `pack_unavailable`) are
rendered amber and never block anything. The setup page obtains them from one
compile for the first configured framework; pack availability and cross-pack
collisions do not vary by target.

`pack_unavailable` copy **must branch on who is looking**, because the server's
freeze fallback is scoped to the setup owner (and admins):

- **Owner/admin, warning says a frozen copy was used:** "Pack X is no longer
  available" + "Your setup keeps using a frozen copy, so nothing breaks", with
  **Keep frozen** (dismisses the notice for the session; the frozen compile is
  already the behavior) and **Customize a copy** (opens the import branch so
  the user can create an owned pack from their current configs — the frozen
  pack itself is not readable as an artifact list).
- **Owner/admin, warning says the pack was skipped** (no snapshot was
  captured): the same skipped copy as a non-owner. The message, not the role
  alone, decides whether a frozen copy is claimed.
- **Non-owner viewing a public setup:** "Pack X is no longer available" +
  "It is skipped in this setup's compiled output." No frozen-copy claim, no
  frozen actions, and the word "frozen" must never appear. The compile really
  omits the pack for that viewer.

## Known limitations

- There is no "pack update available" API field, so the Packs section shows a
  frozen/unavailable badge (derived from warnings) and otherwise no update
  indicator. Do not invent a field for it.
- Warning display uses the first configured framework because warnings are
  target-independent today.
- `FRAMEWORK_PATHS` in `types/setup.ts` is a hand-maintained mirror of the
  adapters' `expected_paths()` and the companion's `MACHINE_SUBDIRS` — update it
  when either changes (same contract as AGENTS.md rule 35).
- Direct install depends on the companion being installed and started with
  `--allow-apply`; without it the method is absent, not disabled.
- Install claims are per user; another user's claims are never shown, even to
  admins.

## Tests

- `pages/Onboarding.test.tsx` — step transitions, back, skip completion, query
  and localStorage resume, add-on pairing + most-used base, profile creation
  with `target_frameworks`, claim recorded on download, finish navigation.
- `pages/ImportPage.test.tsx` — return-to-wizard path after import.
- `pages/ProfileDetail.test.tsx` — matrix precedence, warnings, owner vs.
  non-owner `pack_unavailable` copy.
- `pages/TargetExporter.test.tsx` — framework/location defaults, preview does
  not claim, download/CLI claims do, direct hidden without companion apply.
- `Home.test.tsx`, `CommandPalette.test.tsx`, `App.routes.test.tsx` — CTA and
  palette wiring, `/onboarding` route.
