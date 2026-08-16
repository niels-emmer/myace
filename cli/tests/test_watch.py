"""Tests for `myace watch`'s check-then-maybe-pull decision logic.

Deliberately does not exercise the real `watchfiles` event loop end-to-end
(per the project's stated preference) — only `decide_watch_action()` (pure)
and `run_watch_iteration()` (one full cycle, network mocked) are tested
directly.
"""

from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from myace_cli import main as main_module
from myace_cli.auth import AuthManager
from myace_cli.main import app
from myace_cli.sync import decide_watch_action, run_watch_iteration, write_manifest

runner = CliRunner()

PROFILE_ID = "12345678-1234-5678-1234-567812345678"


def _result(*, locally_modified=None, stale=None, error=None) -> dict:
    return {
        "target": "claude-code",
        "profile_id": PROFILE_ID,
        "profile_name": "demo-profile",
        "locally_modified": locally_modified or [],
        "stale": stale,
        "in_sync": not (locally_modified or stale or error),
        "error": error,
    }


class TestDecideWatchAction:
    def test_in_sync_returns_in_sync(self) -> None:
        assert decide_watch_action(_result(stale=False), auto_pull=False) == "in_sync"
        assert decide_watch_action(_result(stale=False), auto_pull=True) == "in_sync"

    def test_error_always_wins(self) -> None:
        r = _result(stale=True, error="boom")
        assert decide_watch_action(r, auto_pull=True) == "error"

    def test_locally_modified_never_auto_pulls(self) -> None:
        r = _result(locally_modified=["CLAUDE.md"], stale=True)
        # Even with auto_pull=True, a locally-modified file must never be
        # silently overwritten.
        assert decide_watch_action(r, auto_pull=True) == "locally_modified"
        assert decide_watch_action(r, auto_pull=False) == "locally_modified"

    def test_locally_modified_wins_even_without_staleness(self) -> None:
        r = _result(locally_modified=["CLAUDE.md"], stale=False)
        assert decide_watch_action(r, auto_pull=True) == "locally_modified"

    def test_stale_with_auto_pull_returns_auto_pull(self) -> None:
        r = _result(stale=True)
        assert decide_watch_action(r, auto_pull=True) == "auto_pull"

    def test_stale_without_auto_pull_returns_stale_notify(self) -> None:
        r = _result(stale=True)
        assert decide_watch_action(r, auto_pull=False) == "stale_notify"


@pytest.fixture
def project_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    workdir = tmp_path / "project"
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    return workdir


def _seed_manifest(base: Path, compiled_hash: str = "hash-v1") -> Path:
    (base / "CLAUDE.md").write_text("hello world")
    return write_manifest(
        base,
        profile_id=PROFILE_ID,
        profile_name="demo-profile",
        target="claude-code",
        compiled_hash=compiled_hash,
        files={"CLAUDE.md": "hello world"},
    )


def _mock_compile_status(httpx_mock: HTTPXMock, compiled_hash: str) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"http://testserver/api/v1/profiles/{PROFILE_ID}/compile-status?target=claude-code",
        json={"compiled_hash": compiled_hash, "updated_at": "2026-08-16T00:00:00Z"},
    )


def test_run_watch_iteration_in_sync_takes_no_action(
    httpx_mock: HTTPXMock, project_dir: Path
) -> None:
    manifest_path = _seed_manifest(project_dir, compiled_hash="hash-v1")
    _mock_compile_status(httpx_mock, compiled_hash="hash-v1")

    results = run_watch_iteration(
        project_dir, [manifest_path], "http://testserver", "tok", auto_pull=True,
    )

    assert results[0]["action"] == "in_sync"
    assert (project_dir / "CLAUDE.md").read_text() == "hello world"


def test_run_watch_iteration_locally_modified_never_calls_compile_endpoint_to_overwrite(
    httpx_mock: HTTPXMock, project_dir: Path
) -> None:
    manifest_path = _seed_manifest(project_dir, compiled_hash="hash-v1")
    (project_dir / "CLAUDE.md").write_text("hand-edited!")
    _mock_compile_status(httpx_mock, compiled_hash="hash-v2")
    # No /profiles/compile mock registered — if auto-pull tried to fetch and
    # write over the local edit, pytest-httpx would raise on the unmatched
    # request.

    results = run_watch_iteration(
        project_dir, [manifest_path], "http://testserver", "tok", auto_pull=True,
    )

    assert results[0]["action"] == "locally_modified"
    assert (project_dir / "CLAUDE.md").read_text() == "hand-edited!"


def test_run_watch_iteration_auto_pull_writes_new_content(
    httpx_mock: HTTPXMock, project_dir: Path
) -> None:
    manifest_path = _seed_manifest(project_dir, compiled_hash="hash-v1")
    _mock_compile_status(httpx_mock, compiled_hash="hash-v2")
    httpx_mock.add_response(
        method="POST",
        url="http://testserver/api/v1/profiles/compile",
        json={
            "profile_id": PROFILE_ID,
            "profile_name": "demo-profile",
            "target": "claude-code",
            "artifact_count": 1,
            "files": {"CLAUDE.md": "updated server content"},
            "warnings": [],
            "compiled_hash": "hash-v2",
        },
    )

    results = run_watch_iteration(
        project_dir, [manifest_path], "http://testserver", "tok", auto_pull=True,
    )

    assert results[0]["action"] == "auto_pull"
    assert results[0]["pulled"] is True
    assert (project_dir / "CLAUDE.md").read_text() == "updated server content"

    # Manifest itself is refreshed too, not left pointing at the old hash.
    import json
    manifest = json.loads((project_dir / ".myace" / "claude-code.manifest.json").read_text())
    assert manifest["compiled_hash"] == "hash-v2"


def test_run_watch_iteration_stale_without_auto_pull_does_not_write(
    httpx_mock: HTTPXMock, project_dir: Path
) -> None:
    manifest_path = _seed_manifest(project_dir, compiled_hash="hash-v1")
    _mock_compile_status(httpx_mock, compiled_hash="hash-v2")
    # No /profiles/compile mock — must not be called without --auto-pull.

    results = run_watch_iteration(
        project_dir, [manifest_path], "http://testserver", "tok", auto_pull=False,
    )

    assert results[0]["action"] == "stale_notify"
    assert (project_dir / "CLAUDE.md").read_text() == "hello world"


def test_watch_requires_auth(
    project_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth = AuthManager()
    auth.config_dir = tmp_path / "no-creds-home"
    auth.credentials_path = auth.config_dir / "credentials.json"
    monkeypatch.setattr(main_module, "auth_manager", auth)

    result = runner.invoke(app, ["watch", "--target", "claude-code"])
    assert result.exit_code == 1
    assert "authenticated" in result.stdout.lower()


def test_watch_requires_target_or_all(
    project_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth = AuthManager()
    auth.config_dir = tmp_path / "credhome"
    auth.credentials_path = auth.config_dir / "credentials.json"
    auth.store_credentials("http://testserver", "test-token-12345")
    monkeypatch.setattr(main_module, "auth_manager", auth)

    result = runner.invoke(app, ["watch"])
    assert result.exit_code == 1
    assert "--target" in result.stdout or "--all" in result.stdout


def test_watch_missing_manifest_exits_nonzero(
    project_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth = AuthManager()
    auth.config_dir = tmp_path / "credhome2"
    auth.credentials_path = auth.config_dir / "credentials.json"
    auth.store_credentials("http://testserver", "test-token-12345")
    monkeypatch.setattr(main_module, "auth_manager", auth)

    result = runner.invoke(app, ["watch", "--all"])
    assert result.exit_code == 1
