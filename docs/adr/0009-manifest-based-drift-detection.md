# ADR-0009: Local manifest file, not new server state, for drift detection

**Status:** Accepted

## Context

`myace pull` writes a compiled profile's files to disk and then never hears
from that directory again. Two related but distinct questions come up once
someone actually depends on that pulled output: has the *source* profile
changed on the server since the pull (**stale**), and has the *pulled
output itself* been hand-edited locally since (**locally modified**)? A
correct answer to the second question requires knowing, file by file, what
was actually written at pull time — the server has no visibility into a
user's local disk and never should.

This also needs to support three call sites with different needs: a
one-shot `myace check`, a continuous `myace watch`, and (optionally) a
web-UI Sync Dashboard aggregating reports across a user's machines. Sending
every local file's content to the server on every check to answer "did this
change" would be wasteful bandwidth for something a local hash comparison
already answers, and would mean the server needs to store a full copy of
every user's local disk state just to support a lightweight CLI check.

## Decision

`myace pull` writes `.myace/<target>.manifest.json` next to the files it
just wrote: `{profile_id, profile_name, target, compiled_hash,
pulled_at, files: {filename: sha256(content)}}` — a per-file hash of what
was *actually written* (not necessarily the server's raw response; a file
the user declined to overwrite keeps its old hash) plus the server's
whole-output `compiled_hash` at pull time.

`myace check`/`watch` do two independent diffs, entirely client-side except
for one small network call:

1. **Locally modified** — recompute each manifest-tracked file's hash from
   disk right now and compare against the stored hash. Zero network calls.
2. **Stale** — call the new `GET /profiles/{id}/compile-status?target=X`
   (Epic 2.1), which returns just `{compiled_hash, updated_at}`, and
   compare against the manifest's stored `compiled_hash`. This is
   *transfer*-cheap (no file content crosses the wire) but not
   *compute*-cheap — it still resolves the same artifacts and runs the same
   `translate()` as a full compile server-side, documented honestly on
   `compute_compile_status()` (`backend/app/services/compiler.py`) rather
   than oversold as free.

No server-side state is created by `pull`, `check`, or `watch` in their
default form. The only server-side table this phase adds
(`SyncStatus`) is fed exclusively by an explicit `--report` flag — nothing
is sent unless the user opts in, and reports are scoped to the reporting
user only (never cross-user visible), addressed further in
[invariants.md](../invariants.md).

## Alternatives considered

- **Server records what was pulled, at pull time, keyed by (user, profile,
  target)** — rejected. This still can't answer "was the local file
  hand-edited" (the server has no view into local disk state after the
  pull completes), so a local manifest would still be needed for that half
  regardless — making a server-side pull-record redundant with the
  manifest for the one thing it *could* do, and useless for the thing that
  actually motivated this feature.
- **No manifest; full recompile + full diff on every check** — rejected.
  Every `check`/`watch` tick would ship the entire compiled output back and
  forth (and `watch`'s interval-based polling would do this on a timer,
  indefinitely) purely to hash-compare it against local files that could be
  compared directly. The manifest replaces "ship the content to diff it"
  with "store the hash once, diff locally forever after."
- **Report drift status to the server by default** — rejected as a privacy
  regression: a CLI tool silently telling a server what a user has (or
  hasn't) hand-edited on their own machine, without being asked, is the
  kind of default this project explicitly avoids. `--report` is opt-in on
  both `check` and `watch`, every time.

## Consequences

- `.myace/*.manifest.json` becomes a de facto local file-format contract:
  the CLI's own `pull`/`check`/`watch` are the only readers/writers today,
  but the CI Action (Epic 2.6) and, in principle, other tooling can read it
  too. It's intentionally flat/unversioned for this first cut — a
  breaking format change later needs a compatibility story this ADR does
  not yet define.
- The web Sync Dashboard is only ever as complete as what users have
  explicitly reported. It is not, and is not intended to be, an
  authoritative live inventory of every machine a profile has been pulled
  onto — it shows exactly what `--report` has sent it, nothing more. A
  machine that never runs `check --report`/`watch --report` is invisible
  to it, by design.
- `compile-status`'s cost trade-off means `watch`'s interval polling still
  costs the server a full artifact-gather-and-translate per tick, per
  watched target, across every user running `watch`. If that becomes a
  real load concern, the natural next step is caching compiled output
  keyed by a hash of the profile's *resolved inputs* (collections +
  artifacts + adapter version) so `compute_compile_status()` can return a
  cached hash instead of recomputing — deliberately left as future work
  rather than solved speculatively here.
- A file the user declines to overwrite during `pull` is recorded in the
  manifest with its *old* on-disk hash, not the new server hash — otherwise
  the very next `check` would report "in sync" for a file that provably
  isn't.
