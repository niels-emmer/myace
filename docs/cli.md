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

> **Note for macOS users:** The binary is not signed with an Apple Developer
> certificate. The first time you run it, Gatekeeper may block it. To
> bypass: open **System Settings → Privacy & Security**, scroll to the
> security section, and click **Allow Anyway** next to the `myace` entry.
> Or remove the quarantine attribute manually:
> `xattr -d com.apple.quarantine /usr/local/bin/myace`.

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
| `myace serve [--port <port>]` | Run a local companion server so the web UI's Import page can scan this machine (needs `pip install "myace-cli[serve]"`) |

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
result is POSTed to `/api/v1/sync/report` and shows up on your own Sync
Dashboard (`/machine/sync` in the web UI) under a machine label (defaults to your
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
