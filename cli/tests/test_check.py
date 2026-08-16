"""Tests for `myace check` drift detection."""

import json
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from myace_cli import main as main_module
from myace_cli.auth import AuthManager
from myace_cli.main import app
from myace_cli.sync import write_manifest

runner = CliRunner()

PROFILE_ID = "12345678-1234-5678-1234-567812345678"


@pytest.fixture
def logged_in(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    auth = AuthManager()
    auth.config_dir = tmp_path / "credhome"
    auth.credentials_path = auth.config_dir / "credentials.json"
    auth.store_credentials("http://testserver", "test-token-12345")
    monkeypatch.setattr(main_module, "auth_manager", auth)


@pytest.fixture
def project_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    workdir = tmp_path / "project"
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    return workdir


def _seed_manifest(base: Path, target: str = "claude-code", compiled_hash: str = "hash-v1") -> None:
    (base / "CLAUDE.md").write_text("hello world")
    write_manifest(
        base,
        profile_id=PROFILE_ID,
        profile_name="demo-profile",
        target=target,
        compiled_hash=compiled_hash,
        files={"CLAUDE.md": "hello world"},
    )


def _mock_compile_status(httpx_mock: HTTPXMock, compiled_hash: str = "hash-v1") -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"http://testserver/api/v1/profiles/{PROFILE_ID}/compile-status?target=claude-code",
        json={"compiled_hash": compiled_hash, "updated_at": "2026-08-16T00:00:00Z"},
    )


def test_check_in_sync_exits_zero(
    httpx_mock: HTTPXMock, logged_in: None, project_dir: Path
) -> None:
    _seed_manifest(project_dir)
    _mock_compile_status(httpx_mock, compiled_hash="hash-v1")

    result = runner.invoke(app, ["check", "--target", "claude-code"])

    assert result.exit_code == 0
    assert "in sync" in result.stdout


def test_check_locally_modified_file_exits_nonzero(
    httpx_mock: HTTPXMock, logged_in: None, project_dir: Path
) -> None:
    _seed_manifest(project_dir)
    (project_dir / "CLAUDE.md").write_text("hand-edited content")
    _mock_compile_status(httpx_mock, compiled_hash="hash-v1")

    result = runner.invoke(app, ["check", "--target", "claude-code", "--json"])

    assert result.exit_code == 1
    body = json.loads(result.stdout)
    assert body[0]["locally_modified"] == ["CLAUDE.md"]


def test_check_stale_when_server_hash_changed_exits_nonzero(
    httpx_mock: HTTPXMock, logged_in: None, project_dir: Path
) -> None:
    _seed_manifest(project_dir, compiled_hash="hash-v1")
    _mock_compile_status(httpx_mock, compiled_hash="hash-v2")

    result = runner.invoke(app, ["check", "--target", "claude-code", "--json"])

    assert result.exit_code == 1
    body = json.loads(result.stdout)
    assert body[0]["stale"] is True
    assert body[0]["locally_modified"] == []


def test_check_report_flag_calls_report_endpoint(
    httpx_mock: HTTPXMock, logged_in: None, project_dir: Path
) -> None:
    _seed_manifest(project_dir)
    _mock_compile_status(httpx_mock, compiled_hash="hash-v1")
    httpx_mock.add_response(
        method="POST",
        url="http://testserver/api/v1/sync/report",
        json={"id": "abc", "in_sync": True},
    )

    result = runner.invoke(app, ["check", "--target", "claude-code", "--report"])

    assert result.exit_code == 0
    requests = httpx_mock.get_requests(url="http://testserver/api/v1/sync/report")
    assert len(requests) == 1


def test_check_without_report_flag_never_calls_report_endpoint(
    httpx_mock: HTTPXMock, logged_in: None, project_dir: Path
) -> None:
    _seed_manifest(project_dir)
    _mock_compile_status(httpx_mock, compiled_hash="hash-v1")
    # No mock registered for /sync/report — if it's called unexpectedly,
    # pytest-httpx raises for the unmatched request.

    result = runner.invoke(app, ["check", "--target", "claude-code"])

    assert result.exit_code == 0


def test_check_requires_target_or_all(logged_in: None, project_dir: Path) -> None:
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 1
    assert "--target" in result.stdout or "--all" in result.stdout


def test_check_all_finds_every_manifest(
    httpx_mock: HTTPXMock, logged_in: None, project_dir: Path
) -> None:
    _seed_manifest(project_dir, target="claude-code", compiled_hash="hash-a")
    _seed_manifest(project_dir, target="opencode", compiled_hash="hash-b")
    httpx_mock.add_response(
        method="GET",
        url=f"http://testserver/api/v1/profiles/{PROFILE_ID}/compile-status?target=claude-code",
        json={"compiled_hash": "hash-a", "updated_at": "2026-08-16T00:00:00Z"},
    )
    httpx_mock.add_response(
        method="GET",
        url=f"http://testserver/api/v1/profiles/{PROFILE_ID}/compile-status?target=opencode",
        json={"compiled_hash": "hash-b", "updated_at": "2026-08-16T00:00:00Z"},
    )

    result = runner.invoke(app, ["check", "--all", "--json"])

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert {r["target"] for r in body} == {"claude-code", "opencode"}


def test_check_missing_manifest_reports_error_and_exits_nonzero(
    logged_in: None, project_dir: Path
) -> None:
    result = runner.invoke(app, ["check", "--target", "claude-code"])
    assert result.exit_code == 1


def test_check_requires_auth(
    project_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No stored credentials — isolate from any real ~/.myace/credentials.json
    # on the machine running this test.
    auth = AuthManager()
    auth.config_dir = tmp_path / "no-creds-home"
    auth.credentials_path = auth.config_dir / "credentials.json"
    monkeypatch.setattr(main_module, "auth_manager", auth)

    result = runner.invoke(app, ["check", "--target", "claude-code"])
    assert result.exit_code == 1
    assert "authenticated" in result.stdout.lower()
