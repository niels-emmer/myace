"""Profile sync engine — fetch, validate, and write compiled profiles."""

import hashlib
import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

# Local sync-manifest primitives — see docs/adr/0009-manifest-based-drift-detection.md.
#
# `pull` writes one manifest per target directory it writes into
# (`<base>/.myace/<target>.manifest.json`); `check`/`watch` (myace_cli/main.py)
# read it back to detect local hand-edits and server-side staleness without
# any new server-side state. Nothing here talks to the network.

MANIFEST_DIR_NAME = ".myace"


def sha256_text(content: str) -> str:
    """sha256 hex digest of a text file's content — same primitive used
    server-side for compiled_hash (backend/app/services/compiler.py)."""
    return hashlib.sha256(content.encode()).hexdigest()


def manifest_dir(base: Path) -> Path:
    """The `.myace/` directory for a given pulled-output base directory."""
    return base / MANIFEST_DIR_NAME


def manifest_file_path(base: Path, target: str) -> Path:
    """Path to a specific target's manifest file under `base/.myace/`."""
    return manifest_dir(base) / f"{target}.manifest.json"


def write_manifest(
    base: Path,
    *,
    profile_id: str,
    profile_name: str,
    target: str,
    compiled_hash: str,
    files: dict[str, str],
) -> Path:
    """Write (overwriting, never appending) `.myace/<target>.manifest.json`
    under `base`, recording a sha256 per file. Creates `.myace/` if absent.

    `files` must map filename -> the actual final on-disk content for that
    path (not necessarily the raw server response) — callers should hash
    what was *actually written*, so a file the user chose not to overwrite
    (still holding its old content) is correctly recorded with its old
    hash rather than a hash implying it matches the server.
    """
    target_dir = manifest_dir(base)
    target_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "profile_id": profile_id,
        "profile_name": profile_name,
        "target": target,
        "compiled_hash": compiled_hash,
        "pulled_at": datetime.now(UTC).isoformat(),
        "files": {filename: sha256_text(content) for filename, content in files.items()},
    }

    path = manifest_file_path(base, target)
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return path


def read_manifest(path: Path) -> dict[str, Any] | None:
    """Load a manifest file, returning None if missing or unreadable."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def find_manifests(base: Path) -> list[Path]:
    """All `.myace/*.manifest.json` files directly under `base`, sorted for
    stable output ordering."""
    directory = manifest_dir(base)
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.manifest.json"))


def compute_local_file_hashes(base: Path, filenames: Iterable[str]) -> dict[str, str | None]:
    """Hash each manifest-tracked file as it currently exists on disk under
    `base`. A filename missing from disk maps to None (treated as locally
    modified/deleted by callers) rather than being silently omitted."""
    hashes: dict[str, str | None] = {}
    for filename in filenames:
        file_path = base / filename
        if not file_path.exists():
            hashes[filename] = None
            continue
        try:
            hashes[filename] = sha256_text(file_path.read_text())
        except (OSError, UnicodeDecodeError):
            hashes[filename] = None
    return hashes


def check_target(
    base: Path,
    manifest: dict[str, Any],
    server: str,
    token: str,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Diff one manifest against local disk state and the server's current
    compile-status. Pure-ish (one network call) and side-effect-free beyond
    that, so it's directly unit-testable without exercising `check`'s or
    `watch`'s CLI/loop plumbing.

    Returns a dict shaped:
        {
            "target": str,
            "profile_id": str,
            "profile_name": str,
            "locally_modified": list[str],
            "stale": bool | None,   # None if the server couldn't be reached
            "in_sync": bool,
            "error": str | None,
        }
    """
    target = manifest.get("target", "")
    profile_id = manifest.get("profile_id", "")
    profile_name = manifest.get("profile_name", "")
    manifest_files: dict[str, str] = manifest.get("files", {})

    local_hashes = compute_local_file_hashes(base, manifest_files.keys())
    locally_modified = sorted(
        filename
        for filename, stored_hash in manifest_files.items()
        if local_hashes.get(filename) != stored_hash
    )

    stale: bool | None = None
    error: str | None = None
    try:
        url = f"{server}/api/v1/profiles/{profile_id}/compile-status"
        headers = {"Authorization": f"Bearer {token}"}
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers, params={"target": target})
            response.raise_for_status()
            server_hash = response.json().get("compiled_hash")
            stale = server_hash != manifest.get("compiled_hash")
    except httpx.HTTPStatusError as e:
        error = f"Server returned {e.response.status_code}"
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        error = f"Could not reach server: {e}"

    in_sync = not locally_modified and stale is False and error is None

    return {
        "target": target,
        "profile_id": profile_id,
        "profile_name": profile_name,
        "locally_modified": locally_modified,
        "stale": stale,
        "in_sync": in_sync,
        "error": error,
    }


def decide_watch_action(result: dict[str, Any], auto_pull: bool) -> str:
    """Pure decision function for one `myace watch` iteration, given a
    `check_target()` result. Deliberately side-effect-free and easy to unit
    test directly, per the project's stated preference for testing this
    decision rather than the real `watchfiles` event loop end-to-end.

    Returns one of:
      - "in_sync": nothing to do.
      - "error": the server couldn't be reached; warn only.
      - "locally_modified": local hand-edits exist. Always wins over
        staleness and is *never* auto-pulled, regardless of `auto_pull` —
        `watch --auto-pull` must never silently overwrite a local edit.
      - "auto_pull": stale on the server, no local edits, and the caller
        asked for --auto-pull — safe to re-pull automatically.
      - "stale_notify": stale on the server, no local edits, but
        --auto-pull was not requested — warn only.
    """
    if result.get("error"):
        return "error"
    if result.get("locally_modified"):
        return "locally_modified"
    if result.get("stale"):
        return "auto_pull" if auto_pull else "stale_notify"
    return "in_sync"


def report_sync_status(
    server: str,
    token: str,
    *,
    profile_id: str,
    target: str,
    machine_label: str,
    in_sync: bool,
    locally_modified_files: list[str],
    timeout: float = 30.0,
) -> bool:
    """POST a `myace check --report` result to `/api/v1/sync/report`.

    Opt-in only — never called unless the user passes --report (see
    docs/adr/0009-manifest-based-drift-detection.md for why silent
    reporting-by-default would be a privacy regression). Returns True on
    success, False on any failure (never raises — a failed report must not
    fail the `check`/`watch` command that triggered it).
    """
    url = f"{server}/api/v1/sync/report"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "profile_id": profile_id,
        "target": target,
        "machine_label": machine_label,
        "in_sync": in_sync,
        "locally_modified_files": locally_modified_files,
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return True
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
        return False


class SyncEngine:
    """Fetches compiled profiles from the MyACE API and writes files locally."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def pull_profile(
        self,
        server: str,
        token: str,
        profile_name: str,
        target: str,
    ) -> dict | None:
        """
        Fetch a compiled profile from the server.

        Args:
            server: MyACE API server URL (e.g., https://api.myace.localhost)
            token: API token for authentication
            profile_name: Profile name or ID
            target: Target framework (e.g., opencode, claude-code, cursor)

        Returns:
            Dict with a 'files' key containing {filename: content} mappings
            and a 'warnings' key containing any compile-time ValidationIssue
            dicts the server reported (e.g. name collisions across composed
            collections — see AGENTS.md rule 32), or None if the request
            fails. 'warnings' is simply forwarded as-is from the server's
            JSON response; callers should use `.get("warnings", [])` since
            older servers predating this field won't send it.
        """
        # First, resolve profile name to ID if needed
        profile_id = self._resolve_profile_id(server, token, profile_name)
        if not profile_id:
            return None

        # Compile the profile
        url = f"{server}/api/v1/profiles/compile"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "profile_id": profile_id,
            "target": target,
            "include_disabled": False,
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    def list_profiles(self, server: str, token: str) -> list[dict]:
        """List available profiles from the server."""
        url = f"{server}/api/v1/profiles"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
            return []

    def _resolve_profile_id(
        self,
        server: str,
        token: str,
        profile_name: str,
    ) -> str | None:
        """
        Resolve a profile name or ID to a UUID.
        If the input looks like a UUID, return it directly.
        Otherwise, search profiles by name.
        """
        import uuid

        # Check if it's already a UUID
        try:
            uuid.UUID(profile_name)
            return profile_name
        except ValueError:
            pass

        # Search by name
        profiles = self.list_profiles(server, token)
        for profile in profiles:
            if profile.get("name") == profile_name:
                return str(profile["id"])

        # Try partial match
        for profile in profiles:
            if profile_name.lower() in profile.get("name", "").lower():
                return str(profile["id"])

        return None


def run_watch_iteration(
    base: Path,
    manifest_paths: Iterable[Path],
    server: str,
    token: str,
    *,
    auto_pull: bool,
    sync_engine: SyncEngine | None = None,
) -> list[dict[str, Any]]:
    """Run one full check-then-maybe-pull cycle over every given manifest —
    the unit tested "single iteration" of `myace watch`'s loop (see
    `decide_watch_action()` for the pure decision at its core). Never
    exercises the real `watchfiles` event loop; callers (the CLI's `watch`
    command) invoke this once per filesystem event or interval tick.

    Each result dict adds an `"action"` key (see `decide_watch_action()`)
    and, when `action == "auto_pull"`, a `"pulled"` bool for whether the
    re-pull actually happened.
    """
    engine = sync_engine or SyncEngine()
    results: list[dict[str, Any]] = []

    for path in manifest_paths:
        manifest = read_manifest(path)
        if manifest is None:
            results.append({
                "target": path.name.removesuffix(".manifest.json"),
                "profile_id": "",
                "profile_name": "",
                "locally_modified": [],
                "stale": None,
                "in_sync": False,
                "error": f"No readable manifest at {path}",
                "action": "error",
            })
            continue

        result = check_target(base, manifest, server, token)
        result["action"] = decide_watch_action(result, auto_pull)

        if result["action"] == "auto_pull":
            # Safe by construction: decide_watch_action() only returns
            # "auto_pull" when locally_modified is empty, so this can never
            # overwrite a hand-edited file.
            pulled = engine.pull_profile(server, token, manifest["profile_id"], manifest["target"])
            wrote = False
            if pulled and pulled.get("files"):
                for filename, content in pulled["files"].items():
                    if "/" in filename or "\\" in filename or ".." in filename:
                        continue
                    (base / filename).write_text(content)
                compiled_hash = pulled.get("compiled_hash")
                if compiled_hash:
                    write_manifest(
                        base,
                        profile_id=pulled.get("profile_id", manifest.get("profile_id", "")),
                        profile_name=pulled.get("profile_name", manifest.get("profile_name", "")),
                        target=manifest.get("target", ""),
                        compiled_hash=compiled_hash,
                        files=pulled["files"],
                    )
                wrote = True
            result["pulled"] = wrote

        results.append(result)

    return results
