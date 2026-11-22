# CLI

`myace` is a Typer-based CLI that pulls compiled profiles from a MyACE
server and can scan a local config directory to import it as a collection.
It authenticates with a long-lived Bearer API token (create one from the
web UI's Settings → Account page), not a browser session — see
[architecture.md](architecture.md#components).

## Installing

### Quick install (binary, no Python required)

Download the binary for your platform from the
[latest release](https://github.com/niels-emmer/myace/releases):

```bash
# Linux (x86_64)
curl -fsSL https://github.com/niels-emmer/myace/releases/latest/download/myace-linux-x86_64 -o myace
chmod +x ./myace
sudo mv ./myace /usr/local/bin/

# macOS (Intel)
curl -fsSL https://github.com/niels-emmer/myace/releases/latest/download/myace-macos-x86_64 -o myace
chmod +x ./myace
sudo mv ./myace /usr/local/bin/

# macOS (Apple Silicon)
curl -fsSL https://github.com/niels-emmer/myace/releases/latest/download/myace-macos-arm64 -o myace
chmod +x ./myace
sudo mv ./myace /usr/local/bin/
```

**Windows:** Download `myace-windows-x86_64.exe` from the
[releases page](https://github.com/niels-emmer/myace/releases) and place it
somewhere in your `PATH`.

> **macOS only — the binary is unsigned.** Neither macOS build is signed with
> an Apple Developer certificate, so the first run can be blocked by
> Gatekeeper. In case you get **"Apple could not verify … is free of malware
> that may harm your Mac"**, **"… cannot be opened because the developer
> cannot be verified"**, or a bare `Killed: 9`, execute the following,
> pointing it at the file you actually downloaded:
>
> ```bash
> # Still in the download directory, before moving it:
> xattr -cr ./myace-macos-x86_64     # or ./myace-macos-arm64
>
> # Or, if it was already moved into place:
> xattr -cr /usr/local/bin/myace
> ```
>
> `xattr -cr` clears the file's extended attributes (including the
> `com.apple.quarantine` flag Gatekeeper sets on downloads); `xattr -d
> com.apple.quarantine <path>` removes just that one flag. If it is still
> blocked, approve it once in **System Settings → Privacy & Security** →
> **Allow Anyway** next to the `myace` entry. This does not affect Linux or
> Windows, where the binary runs without any of this.

### Via pip

Requires Python 3.12+:

```bash
cd cli
pip install -e .
myace login --server http://localhost:8000 --token <your-api-token>
myace --help
```

### Authenticate

```bash
myace login --server <your-server-url> --token <your-api-token>
myace --help
```

Create an API token from the web UI's Settings → Account page — its "CLI Setup" panel
interpolates the exact command above with your server URL and a freshly
created token.

## Command reference

| Command | Description |
|---------|-------------|
| `myace login --server <url> --token <key>` | Store API credentials |
| `myace logout` | Remove stored credentials |
| `myace status` | Show auth status |
| `myace pull --profile <name> --target <fw> [--path <dir>]` | Fetch and write compiled profile; also writes a `.myace/<target>.manifest.json` sync manifest |
| `myace list-profiles` | List profiles from server |
| `myace import --path <dir> --name <name> [--push]` | Scan local config dir and convert to canonical artifacts |
| `myace check [--target <fw> \| --all] [--json] [--report]` | Check a pulled target for local hand-edits or server-side staleness |
| `myace watch [--target <fw> \| --all] [--interval <secs>] [--auto-pull] [--report]` | Continuously watch pulled output for drift |
| `myace serve [--port <port>] [--allow-apply]` | Run a local companion server so the web UI can scan this machine, and with `--allow-apply` install compiled files directly (needs `pip install "myace-cli[serve]"`) |

## Import command

`myace import` scans an existing local configuration directory (e.g.,
`~/.config/opencode`, `~/.claude`, `~/.cursor`) and converts everything to
Canonical IR:

```bash
# Scan and export to a local directory
myace import --path ~/.config/opencode --name "my-config" --output ./my-collection

# Scan and push to the MyACE server
myace login --server http://localhost:8000 --token <token>
myace import --path ~/.config/opencode --name "my-config" --push
```

**What it discovers:**

| Source | Artifact type |
|--------|--------------|
| `skills/<name>/SKILL.md` | `skill` |
| `agents/<name>.md` | `agent` |
| `commands/<name>.md` | `workflow` |
| `AGENTS.md` (## sections) | `rule` |
| `opencode.json` (models + MCP) | `model_config` |

(The web UI's Import page additionally supports scanning a GitHub
repository directly — see [architecture.md](architecture.md#import-and-export-are-symmetric-on-purpose).)

## Sync and drift detection (check and watch)

Every `myace pull` writes a `.myace/<target>.manifest.json` file recording
a hash of each file it wrote plus the server's compiled-output hash at that
moment. `myace check` and `myace watch` use it to answer two questions
without re-downloading anything: has this pulled output been hand-edited
locally (`locally_modified`), and has the source profile changed on the
server since (`stale`)? See
[ADR-0009](adr/0009-manifest-based-drift-detection.md) for the full design
and [`AGENTS.md` rule
33](../AGENTS.md#33-cli-sync-manifest-format-and-the-compile-status-endpoints-cost-trade-off)
for the manifest format.

```bash
# One-shot check of a specific target, or every manifest in the cwd
myace check --target claude-code
myace check --all --json          # machine-readable, for CI (see below)

# Continuously watch: reacts to local file changes immediately, and
# polls the server at least once every --interval seconds
myace watch --all --interval 300

# Automatically re-pull a target when it's stale on the server.
# Locally hand-edited files are NEVER auto-pulled over, regardless of
# this flag — they're always left alone and only warned about.
myace watch --all --auto-pull
```

`.myace/` is created next to whatever `pull` just wrote. It's local
tooling state, not something you're required to commit — `pull` suggests
adding it to `.gitignore` after writing it — with one exception: a repo
that deliberately vendors a compiled snapshot (see the [CI drift-check
Action](ci-drift-check.md)) should commit `.myace/` on purpose, since that's
exactly what CI diffs against.

Both `check` and `watch` accept `--report`, which is **opt-in only** —
nothing is ever sent to the server otherwise. With `--report`, each check's
result is POSTed to `/api/v1/sync/report` and shows up on your own sync
report (`/machine?tab=sync` in the web UI) under a machine label (defaults to your
hostname). Reports are always scoped to the reporting user — nobody else
can see them, not even admins.

## Local companion server (`myace serve`)

The web UI's Import page can't read your filesystem directly — a browser
has no API to silently walk `~/.claude`, `~/.cursor`, etc. To scan your own
machine from the browser (rather than running `myace import` by hand), run:

```bash
# Binary users (serve is already included):
myace login --server <your-myace-server-url> --token <token-from-Settings>
myace serve

# pip users (need the serve extras):
# pip install "myace-cli[serve]"
# myace login --server <your-myace-server-url> --token <token-from-Settings>
# myace serve
```

The Import page auto-detects it (polling `http://127.0.0.1:8765/health`)
and switches to a live scan-and-select flow once it's running. It binds to
loopback only and only accepts requests from the exact origin you logged
into — see [`cli/myace_cli/local_server.py`](../cli/myace_cli/local_server.py)
and [`AGENTS.md`](../AGENTS.md#24-local-companion-server-myace-serve-security-model)
for the full security model.

### Direct install (`myace serve --allow-apply`)

Scanning is read-only. To let a web UI install step write a compiled profile
to this machine, opt in explicitly:

```bash
myace serve --allow-apply
# or the equivalent environment variable:
MYACE_COMPANION_ALLOW_APPLY=1 myace serve
```

Without the flag (or variable) the companion never exposes a write route.
This CLI PR ships the companion side only; the browser install step that
consumes these routes lands separately (and uses `apply.supported` to hide
the option when it is off):

```json
{ "status": "ok", "server": "https://your-server", "apply": { "supported": true, "targets": ["aider", "claude-code", "..."], "machine_targets": ["claude-code", "..."] } }
```

Two routes are added when enabled, both behind the same loopback bind,
exact-`Origin` check, required `X-MyACE-Companion` header, and Private
Network Access preflight as `/scan`:

- `POST /apply/preview` — `{profile_id, target, location, project_root?}`.
  Fetches the compiled profile with your stored `myace login` credentials
  and returns a per-file diff (`added`/`changed`/`unchanged`, bytes, sha256)
  plus a short-lived, single-use `preview_id`. It writes nothing.
- `POST /apply` — the same body plus `preview_id` and `confirm: true`.
  Re-fetches and re-diffs the profile, refuses (`409`) if anything changed
  since the preview (including a local edit to a destination file), backs up
  every file it will overwrite, writes atomically, then records a
  `.myace/<target>.manifest.json` so `myace check`/`watch` see the install
  just like a `myace pull`. It never deletes files.

Safety properties worth knowing:

- `location: "project"` confines writes to an absolute, existing
  `project_root` (default: the companion's working directory).
  `location: "machine"` confines them to that framework's home root
  (`~/.claude`, `~/.config/opencode`, `~/.cursor`, …). Targets whose output
  is project-only (`aider`, `goose`, `cline`, `copilot-cli`) reject
  `location: "machine"` with `400` rather than confining writes to the
  whole home directory; `machine_targets` in `/health` lists the ones that
  support it.
- Paths are rejected if they would escape the root lexically or through a
  symlink, and if they target the companion's own `.myace/` or
  `.myace-backups/` directories. Overwritten files are copied to
  `<root>/.myace-backups/<UTC timestamp>/` before the write.
- Preview tokens are held in memory for five minutes and consumed on first
  use. Request bodies are capped at 64 KiB by `Content-Length` (a chunked
  request is not counted — the browser install path always sends a length),
  and compiled profiles at 500 files / 5 MiB.
- There is no automatic rollback if a write fails partway through, and
  backup directories are not pruned automatically; the timestamped backup
  directory is the recovery path and a retention policy is a documented
  follow-up. See [ADR-0016](adr/0016-companion-direct-apply.md) for the
  full rationale and known limits.
