"""Tests for `myace pull`'s local sync-manifest writing (.myace/<target>.manifest.json)."""

import json
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from myace_cli import main as main_module
from myace_cli.auth import AuthManager
from myace_cli.main import app
from myace_cli.sync import manifest_file_path, sha256_text

runner = CliRunner()

PROFILE_ID = "12345678-1234-5678-1234-567812345678"


@pytest.fixture
def logged_in(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the CLI's module-level auth_manager at a throwaway credentials file."""
    auth = AuthManager()
    auth.config_dir = tmp_path
    auth.credentials_path = tmp_path / "credentials.json"
    auth.store_credentials("http://testserver", "test-token-12345")
    monkeypatch.setattr(main_module, "auth_manager", auth)


def _compile_response(files: dict[str, str], compiled_hash: str = "abc123") -> dict:
    return {
        "profile_id": PROFILE_ID,
        "profile_name": "demo-profile",
        "target": "claude-code",
        "artifact_count": len(files),
        "files": files,
        "warnings": [],
        "compiled_hash": compiled_hash,
    }


def test_pull_writes_manifest_matching_written_files(
    httpx_mock: HTTPXMock, logged_in: None, tmp_path: Path
) -> None:
    # Flat filenames only — pull's existing path-traversal guard rejects any
    # filename containing "/", including legitimate adapter subdirectory
    # output (a separate, pre-existing bug outside this feature's scope).
    files = {"CLAUDE.md": "hello world", "AGENTS.md": "an agent"}
    httpx_mock.add_response(
        method="POST",
        url="http://testserver/api/v1/profiles/compile",
        json=_compile_response(files, compiled_hash="hash-v1"),
    )
    out_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "pull", "--profile", PROFILE_ID, "--target", "claude-code",
            "--path", str(out_dir), "--force",
        ],
    )

    assert result.exit_code == 0

    manifest_path = manifest_file_path(out_dir, "claude-code")
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())

    assert manifest["profile_id"] == PROFILE_ID
    assert manifest["profile_name"] == "demo-profile"
    assert manifest["target"] == "claude-code"
    assert manifest["compiled_hash"] == "hash-v1"
    assert "pulled_at" in manifest
    assert manifest["files"] == {
        filename: sha256_text(content) for filename, content in files.items()
    }


def test_pull_manifest_records_actual_disk_content_for_declined_overwrite(
    httpx_mock: HTTPXMock, logged_in: None, tmp_path: Path
) -> None:
    """If the user declines to overwrite an existing file, the manifest must
    record the *old* on-disk content's hash, not the new server content's
    hash — otherwise a real local/server mismatch would look in-sync."""
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    existing_file = out_dir / "CLAUDE.md"
    existing_file.write_text("old local content")

    files = {"CLAUDE.md": "new server content"}
    httpx_mock.add_response(
        method="POST",
        url="http://testserver/api/v1/profiles/compile",
        json=_compile_response(files, compiled_hash="hash-v2"),
    )

    # No --force: confirm prompt appears for the existing file; answer "n".
    result = runner.invoke(
        app,
        ["pull", "--profile", PROFILE_ID, "--target", "claude-code", "--path", str(out_dir)],
        input="n\n",
    )

    assert result.exit_code == 0
    assert existing_file.read_text() == "old local content"

    manifest_path = manifest_file_path(out_dir, "claude-code")
    manifest = json.loads(manifest_path.read_text())
    assert manifest["files"]["CLAUDE.md"] == sha256_text("old local content")


def test_pull_manifest_excludes_unsafe_filenames(
    httpx_mock: HTTPXMock, logged_in: None, tmp_path: Path
) -> None:
    files = {"CLAUDE.md": "hello", "../../etc/passwd": "malicious"}
    httpx_mock.add_response(
        method="POST",
        url="http://testserver/api/v1/profiles/compile",
        json=_compile_response(files, compiled_hash="hash-v3"),
    )
    out_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "pull", "--profile", PROFILE_ID, "--target", "claude-code",
            "--path", str(out_dir), "--force",
        ],
    )

    assert result.exit_code == 0
    manifest = json.loads(manifest_file_path(out_dir, "claude-code").read_text())
    assert list(manifest["files"].keys()) == ["CLAUDE.md"]


def test_pull_rerunning_overwrites_manifest_without_appending(
    httpx_mock: HTTPXMock, logged_in: None, tmp_path: Path
) -> None:
    out_dir = tmp_path / "out"

    httpx_mock.add_response(
        method="POST",
        url="http://testserver/api/v1/profiles/compile",
        json=_compile_response({"CLAUDE.md": "v1 content"}, compiled_hash="hash-v1"),
    )
    result1 = runner.invoke(
        app,
        [
            "pull", "--profile", PROFILE_ID, "--target", "claude-code",
            "--path", str(out_dir), "--force",
        ],
    )
    assert result1.exit_code == 0

    httpx_mock.add_response(
        method="POST",
        url="http://testserver/api/v1/profiles/compile",
        json=_compile_response(
            {"CLAUDE.md": "v2 content", "AGENTS.md": "brand new"}, compiled_hash="hash-v2"
        ),
    )
    result2 = runner.invoke(
        app,
        [
            "pull", "--profile", PROFILE_ID, "--target", "claude-code",
            "--path", str(out_dir), "--force",
        ],
    )
    assert result2.exit_code == 0

    manifest = json.loads(manifest_file_path(out_dir, "claude-code").read_text())
    assert manifest["compiled_hash"] == "hash-v2"
    assert set(manifest["files"].keys()) == {"CLAUDE.md", "AGENTS.md"}


def test_pull_without_compiled_hash_skips_manifest(
    httpx_mock: HTTPXMock, logged_in: None, tmp_path: Path
) -> None:
    """An older server response with no compiled_hash field must not produce
    a manifest that `check` couldn't meaningfully diff against."""
    response = _compile_response({"CLAUDE.md": "hello"})
    del response["compiled_hash"]
    httpx_mock.add_response(
        method="POST",
        url="http://testserver/api/v1/profiles/compile",
        json=response,
    )
    out_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "pull", "--profile", PROFILE_ID, "--target", "claude-code",
            "--path", str(out_dir), "--force",
        ],
    )

    assert result.exit_code == 0
    assert not manifest_file_path(out_dir, "claude-code").exists()
