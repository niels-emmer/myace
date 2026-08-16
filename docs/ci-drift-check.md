# CI Drift Check

`.github/actions/myace-check` is a distributable composite GitHub Action for
**other repositories** that consume MyACE-compiled output — it installs
`myace-cli`, runs `myace check --all --json` against a directory of
previously-`myace pull`-ed files, and fails the job if anything has drifted:
a file was hand-edited locally after the pull, or the server's compiled
output has changed since (`stale`). See
[ADR-0009](adr/0009-manifest-based-drift-detection.md) for the manifest/hash
mechanism this is built on, and [`AGENTS.md` rule
33](../AGENTS.md#33-cli-sync-manifest-format-and-the-compile-statuss-cost-trade-off)
for the manifest file format.

This action is **not** wired into MyACE's own CI. This repository's
[`collections/`](../collections/) directory is canonical hand-authored
source, not compiled output — there's nothing here to check for drift
against. It exists purely for repos on the other side of a `myace pull`:
somewhere that vendors a compiled `.claude/`, `.opencode/`, etc. directory
and wants CI to catch it if that directory silently stops matching what the
MyACE server would compile today.

## Prerequisites

1. The target directory (wherever `myace pull` writes files) must be
   committed to the repo, **including its `.myace/` manifest** — the
   manifest is what this check diffs against, so if `.myace/` is
   `.gitignore`d, there's nothing for CI to compare. This is the opposite of
   the suggestion `myace pull` prints for personal/local use (rule 33):
   for a repo whose whole point is dogfooding a specific compiled snapshot,
   commit `.myace/` deliberately.
2. A MyACE API token with read access to the profile being checked (create
   one from the web UI's Settings → CLI Setup panel, or `myace login`
   locally to generate one), stored as a repository secret.

## Usage

Add a workflow (e.g. `.github/workflows/myace-drift-check.yml`) to the
*consuming* repository — not this one:

```yaml
name: MyACE Drift Check

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    # Catches server-side changes even with no local commits — the fs-event
    # half of drift (hand-edited files) is already caught by push/PR above.
    - cron: "0 6 * * *"

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check for drift against the MyACE server
        uses: niels-emmer/myace/.github/actions/myace-check@main
        with:
          server-url: ${{ vars.MYACE_SERVER_URL }}
          token: ${{ secrets.MYACE_API_TOKEN }}
          working-directory: .claude   # wherever `myace pull` wrote files
```

Pin `@main` to a tagged release (e.g. `@v1.6.0`) once MyACE starts cutting
release tags for this action, the same way you'd pin any third-party
Action — `@main` tracks whatever's newest, which is convenient while
adopting this but not what you want long-term for a CI gate.

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `server-url` | yes | — | MyACE API server URL |
| `token` | yes | — | MyACE API token (from a repository secret — never hardcode it) |
| `working-directory` | no | `.` | Directory containing `.myace/*.manifest.json` (i.e. what `myace pull` wrote into) |
| `target` | no | *(all)* | Check only this target's manifest instead of every manifest in `working-directory` |
| `python-version` | no | `3.12` | Python version used to install `myace-cli` |
| `myace-cli-version` | no | *(latest)* | Version constraint, e.g. `==1.6.0` |

## Outputs

| Output | Description |
|---|---|
| `result` | `"in-sync"` or `"drift"` |

## What a failure looks like

The job fails (non-zero exit) whenever `myace check` reports either
`locally_modified` files or a `stale` target, and prints the same
machine-readable JSON `myace check --json` would print locally, so you can
reproduce the failure by running the same command yourself:

```bash
myace login --server <url> --token <token>
cd <working-directory>
myace check --all --json
```

A `locally_modified` failure means someone (or something) edited the
checked-out compiled output directly instead of going through the source
profile/collections — the fix is almost always to revert that edit and make
the underlying change upstream instead. A `stale` failure means the source
profile changed on the server since the last `myace pull` — the fix is to
re-run `myace pull` and commit the result (including the refreshed
`.myace/` manifest).
