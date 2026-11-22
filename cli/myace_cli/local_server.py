"""Local companion server — lets the MyACE web UI scan this machine directly.

`myace pull`/`myace import` talk to the remote MyACE server; this instead runs
*on* the user's own machine so the web UI's Import page can trigger a real
filesystem scan without the browser needing any filesystem access of its own
(browsers can't silently walk `~/.claude`, `~/.cursor`, etc.).

Security model — why this isn't an open port any website can read from:
  1. Requires `myace login` to have already run; the allowed browser origin
     is whatever server you're logged into, not attacker-controlled.
  2. Binds to 127.0.0.1 only — never reachable off this machine.
  3. Only the logged-in server's origin is ever reflected in
     Access-Control-Allow-Origin — no wildcard, so no other page's JS can
     read a response even though the request can physically reach this port.
  4. `/scan` and `/audit` additionally require a custom `X-MyACE-Companion`
     header and an exact `Origin` match, checked server-side (not just via
     CORS response headers). A browser can't attach a custom header to a
     `no-cors` cross-origin request, so this also blocks the "blind POST
     that still causes a side effect" class of attack, not just response
     reading — and the server-side origin check means a non-browser client
     can't just skip the CORS dance to call it directly (the same crude
     defense as a CSRF token, sized to the actual threat: a malicious page
     open in the same browser, not a co-resident malicious process, which
     already has equivalent access to this user's files regardless).
     `/audit` (the Setup Audit page's cross-target coverage/duplicate scan
     — `myace_cli/audit.py`) reads more of the filesystem than `/scan` in
     one call (every known target's expected paths, not one caller-chosen
     directory), so it is not a weaker route than `/scan` — same gate,
     same origin/header requirements, no shortcuts.
  5. Implements Chrome's Private Network Access preflight
     (`Access-Control-Allow-Private-Network`) — without it, an HTTPS page
     fetching a loopback address is blocked outright in current Chrome.
  6. `/apply/preview` and `/apply` (writing a compiled profile to disk) are
     **opt-in and disabled by default**, behind `myace serve --allow-apply`
     (or `MYACE_COMPANION_ALLOW_APPLY=1`). `/health` reports whether they are
     enabled so the web UI can hide the option. They use the same
     origin/header gate as `/scan`, plus path confinement, a diff-first
     preview token, backups of overwritten files, and atomic writes. See
     docs/adr/0016-companion-direct-apply.md.
"""

import asyncio
import hashlib
import os
import secrets
import shutil
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from myace_cli.audit import audit_directory
from myace_cli.scanner import scan_directory
from myace_cli.sync import SyncEngine, safe_output_path

COMPANION_HEADER = "x-myace-companion"
DEFAULT_PORT = 8765
ALLOW_APPLY_ENV_VAR = "MYACE_COMPANION_ALLOW_APPLY"

# Machine-level install roots, as subdirectories of the user's home. Project
# installs use the caller's confirmed project root instead. Kept as a
# hand-maintained map (same pattern as audit.py's ADAPTER_EXPECTED_PATHS) —
# this CLI package deliberately does not import the backend adapters.
MACHINE_SUBDIRS: dict[str, tuple[str, ...]] = {
    "opencode": (".config", "opencode"),
    "claude-code": (".claude",),
    "cursor": (".cursor",),
    "codex-cli": (".codex",),
    "copilot-cli": (),
    "cline": (),
    "windsurf": (".windsurf",),
    "aider": (),
    "continue": (".continue",),
    "goose": (),
    "amazon-q": (".amazonq",),
    "pi-dev": (".pi",),
}
APPLY_TARGETS: tuple[str, ...] = tuple(sorted(MACHINE_SUBDIRS))

BACKUP_DIR_NAME = ".myace-backups"
PREVIEW_TTL_SECONDS = 300
MAX_PREVIEWS = 64
MAX_FILES = 500
MAX_TOTAL_BYTES = 5 * 1024 * 1024
MAX_REQUEST_BYTES = 64 * 1024
MAX_FILENAME_LENGTH = 4096
MAX_PROJECT_ROOT_LENGTH = 4096


class UnsafeInstallPathError(Exception):
    """A compiled filename would escape the resolved install root."""


def _home() -> Path:
    """Indirection so tests can substitute a temporary home directory."""
    return Path.home()


def _machine_root(target: str) -> Path:
    """The framework's conventional per-user config directory."""
    return _home().joinpath(*MACHINE_SUBDIRS[target])


def resolve_install_root(
    location: str,
    target: str,
    project_root: str | None,
) -> Path:
    """Resolve the directory all writes are confined to.

    `project`: the confirmed project root (default: the server's cwd). Must
    be absolute, existing, and a directory.
    `machine`: the target framework's home-root directory.
    """
    if location == "machine":
        return _machine_root(target)

    root = Path(project_root).expanduser() if project_root else Path.cwd()
    if not root.is_absolute():
        raise ValueError("project_root must be an absolute path")
    if not root.exists():
        raise ValueError(f"project_root does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"project_root is not a directory: {root}")
    return root.resolve()


def _relative_install_path(location: str, root: Path, filename: str) -> str:
    """Map a compiled filename to its install-root-relative path.

    Project installs use the adapter's filename unchanged (`.claude/agents/x.md`
    is already project-relative). Machine installs rebase onto the framework's
    home root and drop a leading framework directory that would otherwise be
    duplicated — e.g. `.claude/agents/x.md` under `~/.claude` becomes
    `agents/x.md`, and `.opencode/skills/x/SKILL.md` under `~/.config/opencode`
    becomes `skills/x/SKILL.md`.
    """
    if location == "project":
        return filename

    parts = filename.split("/")
    if parts and parts[0].lstrip(".") == root.name.lstrip("."):
        parts = parts[1:]
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise UnsafeInstallPathError(f"unsafe install path derived from {filename!r}")
    return "/".join(parts)


def _dest_for(root_real: Path, relative_path: str) -> Path:
    """`root_real / relative_path`, after lexical and symlink confinement.

    Lexical `safe_output_path()` already rejects absolute paths and `..`
    segments. `resolve(strict=False)` additionally walks existing symlinks in
    the parent chain (and the leaf), so a `~/.claude` or `project/.claude`
    symlinked outside the install root is refused rather than written
    through. This is deliberately stricter than `myace pull`, which allows a
    symlinked framework directory — apply writes on the user's behalf, so it
    refuses anything it cannot prove stays inside the previewed root.
    """
    first = relative_path.split("/", 1)[0]
    if first == BACKUP_DIR_NAME:
        raise UnsafeInstallPathError(
            f"{relative_path!r} targets the companion backup directory"
        )

    dest = safe_output_path(root_real, relative_path)
    if dest is None:
        raise UnsafeInstallPathError(f"unsafe install path: {relative_path!r}")

    resolved = dest.resolve(strict=False)
    if not resolved.is_relative_to(root_real):
        raise UnsafeInstallPathError(
            f"{relative_path!r} resolves outside the install root ({resolved})"
        )
    if dest.exists() and dest.is_dir():
        raise UnsafeInstallPathError(f"{relative_path!r} is a directory")
    return dest


def build_diff(
    files: dict[str, str],
    *,
    root: Path,
    location: str,
) -> tuple[list[dict[str, Any]], str, dict[str, str]]:
    """Compute the per-file install diff without touching disk.

    Returns `(entries, diff_hash, contents)` where `entries` is sorted by
    relative path, `diff_hash` is a stable digest of the whole diff, and
    `contents` maps relative path -> file content for the write phase.
    Raises `UnsafeInstallPathError` for any escaping or colliding path.
    """
    root_real = root.resolve()
    by_relative: dict[str, str] = {}
    seen_dest: dict[Path, str] = {}
    contents: dict[str, str] = {}
    prepared: list[tuple[str, Path]] = []

    for filename, content in files.items():
        relative_path = _relative_install_path(location, root, filename)
        if relative_path in by_relative:
            raise UnsafeInstallPathError(
                f"{filename!r} and {by_relative[relative_path]!r} both install to "
                f"{relative_path!r}"
            )
        dest = _dest_for(root_real, relative_path)
        if dest in seen_dest:
            raise UnsafeInstallPathError(
                f"{filename!r} and {seen_dest[dest]!r} both install to {dest}"
            )
        by_relative[relative_path] = filename
        seen_dest[dest] = filename
        contents[relative_path] = content
        prepared.append((relative_path, dest))

    entries: list[dict[str, Any]] = []
    for relative_path, dest in sorted(prepared, key=lambda item: item[0]):
        content = contents[relative_path]
        data = content.encode("utf-8")
        new_sha = hashlib.sha256(data).hexdigest()

        exists = dest.exists()
        if exists:
            old_sha = hashlib.sha256(dest.read_bytes()).hexdigest()
            action = "unchanged" if old_sha == new_sha else "changed"
        else:
            action = "added"

        entries.append(
            {
                "relative_path": relative_path,
                "path": str(dest),
                "exists": exists,
                "bytes": len(data),
                "sha256": new_sha,
                "action": action,
            }
        )

    digest = hashlib.sha256()
    for entry in entries:
        digest.update(f"{entry['relative_path']}\0{entry['sha256']}\n".encode())
    return entries, digest.hexdigest(), contents


def _atomic_write(dest: Path, content: str) -> None:
    """Write `content` to a temp file in the destination directory, then
    `os.replace()` it into place, so a reader never sees a truncated file."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=dest.parent, prefix=".myace-tmp-", suffix=".part")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if dest.exists():
            shutil.copymode(dest, tmp)
        else:
            os.chmod(tmp, 0o644)
        os.replace(tmp, dest)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def write_entries(
    entries: list[dict[str, Any]],
    contents: dict[str, str],
    *,
    root: Path,
) -> dict[str, Any]:
    """Back up every overwritten file, then atomically write added/changed files.

    Never deletes a file. Backups live under `<root>/.myace-backups/<UTC
    timestamp>/`, one directory per apply run. All backups are taken before
    any write, so a backup failure aborts without modifying the tree.
    """
    root_real = root.resolve()

    changed = [entry for entry in entries if entry["action"] == "changed"]
    writes = [entry for entry in entries if entry["action"] in ("added", "changed")]

    backup_dir: Path | None = None
    backups: list[str] = []
    if changed:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        backup_dir = root_real / BACKUP_DIR_NAME / stamp
        suffix = 0
        while backup_dir.exists():
            suffix += 1
            backup_dir = root_real / BACKUP_DIR_NAME / f"{stamp}-{suffix}"
        if not backup_dir.resolve(strict=False).is_relative_to(root_real):
            raise UnsafeInstallPathError("backup directory escapes the install root")

        for entry in changed:
            source = _dest_for(root_real, entry["relative_path"])
            backup = safe_output_path(backup_dir, entry["relative_path"])
            if backup is None:
                raise UnsafeInstallPathError(
                    f"unsafe backup path: {entry['relative_path']!r}"
                )
            if not backup.resolve(strict=False).is_relative_to(root_real):
                raise UnsafeInstallPathError(
                    f"backup for {entry['relative_path']!r} escapes the install root"
                )
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup)
            backups.append(str(backup))

    written: list[str] = []
    for entry in writes:
        dest = _dest_for(root_real, entry["relative_path"])
        _atomic_write(dest, contents[entry["relative_path"]])
        written.append(str(dest))

    return {
        "written": written,
        "backups": backups,
        "unchanged": [entry["path"] for entry in entries if entry["action"] == "unchanged"],
        "backup_dir": str(backup_dir) if backup_dir is not None else None,
    }


class _PreviewRegistry:
    """Short-lived, in-memory preview tokens — never persisted to disk."""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}

    def _prune(self) -> None:
        now = time.monotonic()
        for token in [t for t, item in self._items.items() if item["expires_at"] <= now]:
            self._items.pop(token, None)

    def add(self, record: dict[str, Any]) -> str:
        self._prune()
        token = secrets.token_urlsafe(32)
        created = time.monotonic()
        record["created_at"] = created
        record["expires_at"] = created + PREVIEW_TTL_SECONDS
        self._items[token] = record
        while len(self._items) > MAX_PREVIEWS:
            oldest = min(self._items, key=lambda key: self._items[key]["created_at"])
            self._items.pop(oldest, None)
        return token

    def pop(self, token: str) -> dict[str, Any] | None:
        """Consume a token. Single-use: a retry must request a new preview."""
        self._prune()
        record = self._items.pop(token, None)
        if record is None:
            return None
        if record["expires_at"] <= time.monotonic():
            return None
        return record


def _default_fetch_compiled(
    credentials: dict[str, str],
    profile_id: str,
    target: str,
) -> dict[str, Any] | None:
    """Fetch a compiled profile using the stored CLI credentials."""
    return SyncEngine().pull_profile(
        server=credentials["server"],
        token=credentials["token"],
        profile_name=profile_id,
        target=target,
    )


def _cors_headers(allowed_origin: str, private_network: bool) -> dict[str, str]:
    headers = {
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": f"Content-Type, {COMPANION_HEADER}",
        "Vary": "Origin",
    }
    if private_network:
        headers["Access-Control-Allow-Private-Network"] = "true"
    return headers


def build_app(
    allowed_origin: str,
    *,
    allow_apply: bool = False,
    credentials: dict[str, str] | None = None,
    fetch_compiled: Callable[[dict[str, str], str, str], dict[str, Any] | None] | None = None,
) -> Any:
    """Build the FastAPI app. Imported lazily so the base CLI install never
    needs fastapi/uvicorn — only `pip install "myace-cli[serve]"` does."""
    import httpx
    from fastapi import FastAPI, HTTPException, Request
    from pydantic import BaseModel, Field
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse, Response

    class ScanRequestBody(BaseModel):
        path: str
        framework: str = "opencode"

    class AuditRequestBody(BaseModel):
        path: str

    class ApplyPreviewBody(BaseModel):
        profile_id: str = Field(min_length=1, max_length=128)
        target: str = Field(min_length=1, max_length=64)
        location: Literal["project", "machine"] = "project"
        project_root: str | None = Field(default=None, max_length=MAX_PROJECT_ROOT_LENGTH)

    class ApplyBody(ApplyPreviewBody):
        preview_id: str = Field(min_length=1, max_length=256)
        confirm: bool = False

    registry = _PreviewRegistry()
    fetch = fetch_compiled or _default_fetch_compiled

    def _require_companion_request(request: Request) -> None:
        """Shared auth gate for every state-touching/data-reading route
        (`/scan`, `/audit`, `/apply/preview`, `/apply`) — a custom header
        (blocks blind `no-cors` cross-origin POSTs, which can't carry custom
        headers) plus a server-side Origin check (not just the CORS response
        header, so a non-browser client can't skip the dance). Defined once
        so a future security-relevant change here (e.g. a rate limit) can't
        land on only one route by accident — see AGENTS.md rule 24.
        Raises the same HTTPException every route already raised inline.
        """
        if request.headers.get(COMPANION_HEADER) != "1":
            raise HTTPException(status_code=400, detail="Missing X-MyACE-Companion header")
        if request.headers.get("origin") != allowed_origin:
            raise HTTPException(status_code=403, detail="Origin not allowed")

    def _require_apply_enabled() -> None:
        if not allow_apply:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Direct apply is disabled. Restart `myace serve` with "
                    "--allow-apply (or set MYACE_COMPANION_ALLOW_APPLY=1)."
                ),
            )

    def _require_known_target(target: str) -> None:
        if target not in MACHINE_SUBDIRS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unknown target {target!r}. Supported: "
                    f"{', '.join(APPLY_TARGETS)}"
                ),
            )

    def _resolve_body_root(body: ApplyPreviewBody) -> Path:
        try:
            return resolve_install_root(body.location, body.target, body.project_root)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    def _fetch_compiled(profile_id: str, target: str) -> dict[str, Any]:
        creds = credentials
        if creds is None:
            from myace_cli.auth import AuthManager

            creds = AuthManager().load_credentials()
        if not creds:
            raise HTTPException(
                status_code=503,
                detail="Companion is not authenticated. Run `myace login` first.",
            )
        try:
            result = fetch(creds, profile_id, target)
        except HTTPException:
            raise
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 404:
                raise HTTPException(status_code=404, detail="Profile not found") from exc
            if status in (401, 403):
                raise HTTPException(
                    status_code=502,
                    detail="The MyACE server rejected the stored credentials",
                ) from exc
            raise HTTPException(
                status_code=502,
                detail=f"The MyACE server returned status {status}",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Could not reach the MyACE server: {exc}",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Could not fetch the compiled profile: {exc}",
            ) from exc

        if not result or not isinstance(result.get("files"), dict):
            raise HTTPException(
                status_code=404,
                detail="Profile not found or the server returned no compiled files",
            )
        return result

    def _validated_files(document: dict[str, Any]) -> dict[str, str]:
        files = document["files"]
        if not files:
            raise HTTPException(status_code=502, detail="The server returned no compiled files")
        if len(files) > MAX_FILES:
            raise HTTPException(
                status_code=413,
                detail=f"Compiled profile has too many files (limit {MAX_FILES})",
            )

        total = 0
        checked: dict[str, str] = {}
        for filename, content in files.items():
            if not isinstance(filename, str) or not isinstance(content, str):
                raise HTTPException(
                    status_code=502,
                    detail="The compiled profile contained a non-text file entry",
                )
            if len(filename) > MAX_FILENAME_LENGTH:
                raise HTTPException(status_code=413, detail="A compiled filename is too long")
            total += len(content.encode("utf-8"))
            if total > MAX_TOTAL_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"Compiled profile exceeds the {MAX_TOTAL_BYTES} byte apply limit",
                )
            checked[filename] = content
        return checked

    class _CompanionCors(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Any) -> Response:
            origin = request.headers.get("origin")
            private_network = (
                request.headers.get("access-control-request-private-network") == "true"
            )

            if request.method == "OPTIONS":
                if origin == allowed_origin:
                    return Response(status_code=200, headers=_cors_headers(origin, private_network))
                return Response(status_code=403)

            content_length = request.headers.get("content-length", "")
            if content_length.isdigit() and int(content_length) > MAX_REQUEST_BYTES:
                headers = (
                    _cors_headers(origin, private_network)
                    if origin == allowed_origin
                    else None
                )
                return Response(status_code=413, headers=headers)

            response = await call_next(request)
            if origin == allowed_origin:
                for key, value in _cors_headers(origin, private_network).items():
                    response.headers[key] = value
            return response

    app = FastAPI(title="myace-companion", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(_CompanionCors)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "server": allowed_origin,
            "apply": {
                "supported": allow_apply,
                "targets": list(APPLY_TARGETS),
            },
        }

    @app.post("/scan")
    async def scan(request: Request, body: ScanRequestBody) -> JSONResponse:
        _require_companion_request(request)

        try:
            artifacts = scan_directory(body.path)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

        return JSONResponse(
            {
                "path": body.path,
                "framework": body.framework,
                "artifact_count": len(artifacts),
                "artifacts": artifacts,
            }
        )

    @app.post("/audit")
    async def audit(request: Request, body: AuditRequestBody) -> JSONResponse:
        """Cross-target local setup audit — same security gate as /scan
        (rule 24), enforced by the same shared `_require_companion_request`
        both routes call."""
        _require_companion_request(request)

        root = Path(body.path).expanduser()
        if not root.exists():
            try:
                resolved = root.resolve(strict=False)
                if resolved.exists():
                    root = resolved
            except (OSError, RuntimeError):
                pass
        if not root.exists():
            raise HTTPException(status_code=404, detail=f"Directory not found: {root}")
        if not root.is_dir():
            raise HTTPException(status_code=400, detail=f"Not a directory: {root}")

        result = audit_directory(root)
        return JSONResponse(result)

    @app.post("/apply/preview")
    async def apply_preview(request: Request, body: ApplyPreviewBody) -> JSONResponse:
        """Diff a compiled profile against the local install root.

        Read-only: computes per-file added/changed/unchanged status, the
        resolved root, and a short-lived `preview_id` for the confirming
        `/apply` call.
        """
        _require_companion_request(request)
        _require_apply_enabled()
        _require_known_target(body.target)
        root = _resolve_body_root(body)

        document = await asyncio.to_thread(_fetch_compiled, body.profile_id, body.target)
        files = _validated_files(document)

        try:
            entries, diff_hash, _ = build_diff(files, root=root, location=body.location)
        except UnsafeInstallPathError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        preview_id = registry.add(
            {
                "profile_id": body.profile_id,
                "target": body.target,
                "location": body.location,
                "root": str(root),
                "diff_hash": diff_hash,
            }
        )

        return JSONResponse(
            {
                "preview_id": preview_id,
                "profile_id": body.profile_id,
                "profile_name": document.get("profile_name", ""),
                "target": body.target,
                "location": body.location,
                "root": str(root),
                "diff_hash": diff_hash,
                "files": entries,
                "warnings": document.get("warnings") or [],
            }
        )

    @app.post("/apply")
    async def apply(request: Request, body: ApplyBody) -> JSONResponse:
        """Write a previously previewed profile after explicit confirmation.

        Consumes the preview token (single use), re-fetches and re-diffs the
        profile, refuses if the diff no longer matches what was previewed,
        backs up every overwritten file, and writes atomically. Never deletes.
        """
        _require_companion_request(request)
        _require_apply_enabled()
        _require_known_target(body.target)

        if not body.confirm:
            raise HTTPException(
                status_code=400,
                detail="confirm must be true to write files to this machine",
            )

        record = registry.pop(body.preview_id)
        if record is None:
            raise HTTPException(
                status_code=400,
                detail="Unknown, expired, or already-used preview_id; request a new preview",
            )

        root = _resolve_body_root(body)
        if (
            body.profile_id != record["profile_id"]
            or body.target != record["target"]
            or body.location != record["location"]
            or str(root) != record["root"]
        ):
            raise HTTPException(
                status_code=409,
                detail="Apply request does not match the preview; request a new preview",
            )

        document = await asyncio.to_thread(_fetch_compiled, body.profile_id, body.target)
        files = _validated_files(document)

        try:
            entries, diff_hash, contents = build_diff(
                files, root=root, location=body.location
            )
        except UnsafeInstallPathError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if diff_hash != record["diff_hash"]:
            raise HTTPException(
                status_code=409,
                detail="Files changed since the preview; request a new preview",
            )

        try:
            result = await asyncio.to_thread(
                write_entries, entries, contents, root=root
            )
        except UnsafeInstallPathError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return JSONResponse(
            {
                "profile_id": body.profile_id,
                "profile_name": document.get("profile_name", ""),
                "target": body.target,
                "location": body.location,
                "root": str(root),
                **result,
            }
        )

    return app


def apply_requested_by_env() -> bool:
    """True when MYACE_COMPANION_ALLOW_APPLY is set to a truthy value."""
    return os.environ.get(ALLOW_APPLY_ENV_VAR, "").strip().lower() in ("1", "true", "yes", "on")


def run(
    allowed_origin: str,
    port: int = DEFAULT_PORT,
    *,
    allow_apply: bool = False,
) -> None:
    import uvicorn

    app = build_app(allowed_origin, allow_apply=allow_apply)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
