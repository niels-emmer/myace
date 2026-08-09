# PLAN: CLI Sidecar Binary Release

## Goal

Deliver `myace` as a standalone, cross-platform binary (Linux x86_64, macOS
x86_64 + arm64, Windows x86_64) so users can download and run it without
Python, venv, pip, or git.

## Acceptance criteria

1. A user on any of the 4 target platforms can download a single file, make it
   executable, and run `myace --help` without any prior setup.
2. All existing commands (`login`, `logout`, `status`, `pull`, `list-profiles`,
   `import`, `serve`) work identically in the binary.
3. The binary is built automatically by CI when a tag matching `cli-v*` is
   pushed, and attached to the corresponding GitHub Release.
4. The existing venv+pip install path continues to work unchanged.
5. Bootstrap scripts (`bootstrap-import.sh`, `bootstrap-import.ps1`) detect the
   user's platform and download the binary when available, falling back to the
   venv path otherwise.
6. `README.md` documents both install paths (binary and venv).

## Epics

### Epic 1: Build infrastructure (build.spec + pyproject.toml)

**Files to create/modify:**
- `cli/build.spec` — PyInstaller spec file (NEW)
- `cli/pyproject.toml` — add `pyinstaller` to dev deps (MODIFY)

**Tasks:**
1. Create `cli/build.spec` with:
   - `Analysis` pointing at `myace_cli/main.py`
   - `hiddenimports` for fastapi, uvicorn.*, starlette.*, pydantic
   - `datas` with `copy_metadata('rich')` and `copy_metadata('typer')`
   - `excludes` for unnecessary packages (tkinter, matplotlib, numpy, etc.)
   - `EXE` with `onefile=True`, `console=True`, `upx=True`
2. Add `pyinstaller>=6.0` to `[project.optional-dependencies] dev` in
   `cli/pyproject.toml`
3. Move `fastapi` and `uvicorn` from `[project.optional-dependencies] serve`
   into `dev` as well (so CI can install everything in one shot)

**Verification:**
- `pyinstaller cli/build.spec --clean` completes without error
- The resulting `dist/myace` binary runs and shows `myace --help`
- `myace login`, `myace status`, `myace serve` all work

### Epic 2: Release CI workflow

**File to create:**
- `.github/workflows/release-cli.yml` (NEW)

**Tasks:**
1. Trigger on `push` with tag pattern `cli-v*`
2. Matrix build across 4 platform targets:
   - `ubuntu-latest` → `myace-linux-x86_64`
   - `macos-13` (Intel) → `myace-macos-x86_64`
   - `macos-latest` (ARM) → `myace-macos-arm64`
   - `windows-latest` → `myace-windows-x86_64.exe`
3. Each job: checkout, setup Python 3.12, install deps + pyinstaller, run
   `pyinstaller build.spec`, rename artifact, upload to release
4. Use `softprops/action-gh-release@v2` to attach binaries

**Verification:**
- Workflow is syntactically valid (can be checked with `act` or manual review)
- On a tag push, all 4 binaries are built and attached to the release

### Epic 3: README documentation

**File to modify:**
- `README.md` (MODIFY)

**Tasks:**
1. Add a "Quick install (binary)" section before the existing "CLI setup"
   section
2. Document download + chmod +x for each platform
3. Add a download badge linking to latest release
4. Keep existing venv+pip instructions intact

**Verification:**
- README renders correctly on GitHub
- Both install paths are documented
- No broken links

### Epic 4: Bootstrap script updates

**Files to modify:**
- `scripts/bootstrap-import.sh` (MODIFY)
- `scripts/bootstrap-import.ps1` (MODIFY)

**Tasks:**
1. In each script, detect the platform (OS + arch)
2. Check if a binary exists for that platform in the latest GitHub release
3. If yes: download it, make executable, place in `~/.myace/bin/myace`
4. If no: fall back to the existing venv+pip path
5. Add `~/.myace/bin` to PATH guidance

**Verification:**
- Script downloads binary on supported platforms
- Script falls back to venv on unsupported platforms
- Binary from script works identically to manually-downloaded binary

### Epic 5: `__main__.py` (bonus)

**File to create:**
- `cli/myace_cli/__main__.py` (NEW)

**Tasks:**
1. Create `__main__.py` that calls `app()` from `main.py`
2. This enables `python -m myace_cli` as an alternative entry point

**Verification:**
- `python -m myace_cli --help` works from the `cli/` directory

## Build-test-audit-document cycle

Each epic follows this pattern:

1. **Build** — implement the changes
2. **Test** — run the verification steps listed above
3. **Audit** — review for security, correctness, and compliance
4. **Document** — update any docs that the epic touches
5. **Continue** — commit and move to the next epic

## Risk register

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Binary fails on platform without Python | Low | Test on clean CI runner (no Python in PATH) |
| Hidden import missed for fastapi/uvicorn | Medium | Comprehensive hiddenimports list from research; test `serve` command in binary |
| macOS Gatekeeper blocks unsigned binary | High | Document the "right-click → Open" workaround; add signing later |
| Windows SmartScreen flags unsigned .exe | Medium | Document the "Run anyway" workaround; add signing later |
| Binary size too large (>50 MB) | Low | UPX compression; exclude unnecessary packages |
| Bootstrap script can't detect arch on some platforms | Low | Fall back to venv path; `uname -m` is reliable on Linux/macOS |

## Handoff criteria

- All 5 epics are complete and verified
- All changes are committed to `feat/cli-sidecar-binary`
- A `/handoff` summary is produced
