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
