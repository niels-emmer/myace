"""Tests for `myace pull`'s compile-warning display and --strict flag."""

from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from myace_cli import main as main_module
from myace_cli.auth import AuthManager
from myace_cli.main import app

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


def _compile_response(warnings: list[dict[str, str]] | None = None) -> dict:
    return {
        "profile_id": PROFILE_ID,
        "profile_name": "demo-profile",
        "target": "claude-code",
        "artifact_count": 1,
        "files": {"CLAUDE.md": "hello"},
        "warnings": warnings or [],
    }


def test_pull_without_warnings_exits_zero(
    httpx_mock: HTTPXMock, logged_in: None, tmp_path: Path
) -> None:
    httpx_mock.add_response(
        method="POST",
        url="http://testserver/api/v1/profiles/compile",
        json=_compile_response(),
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
    assert "Warnings:" not in result.stdout
    assert (out_dir / "CLAUDE.md").exists()


def test_pull_with_warnings_prints_them_without_failing_by_default(
    httpx_mock: HTTPXMock, logged_in: None, tmp_path: Path
) -> None:
    httpx_mock.add_response(
        method="POST",
        url="http://testserver/api/v1/profiles/compile",
        json=_compile_response(
            warnings=[
                {
                    "level": "warning",
                    "code": "name_collision",
                    "message": "Artifact 'x' is defined in both 'a' and 'b'; 'b' wins.",
                },
            ]
        ),
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
    assert "Warnings:" in result.stdout
    assert "name_collision" in result.stdout
    assert (out_dir / "CLAUDE.md").exists()


def test_pull_strict_exits_nonzero_when_warnings_present(
    httpx_mock: HTTPXMock, logged_in: None, tmp_path: Path
) -> None:
    httpx_mock.add_response(
        method="POST",
        url="http://testserver/api/v1/profiles/compile",
        json=_compile_response(
            warnings=[{"level": "warning", "code": "name_collision", "message": "collision"}]
        ),
    )
    out_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "pull", "--profile", PROFILE_ID, "--target", "claude-code",
            "--path", str(out_dir), "--force", "--strict",
        ],
    )

    assert result.exit_code == 1
    # Strict mode flags the problem but still writes the (valid) compiled output.
    assert (out_dir / "CLAUDE.md").exists()


def test_pull_strict_exits_zero_when_no_warnings(
    httpx_mock: HTTPXMock, logged_in: None, tmp_path: Path
) -> None:
    httpx_mock.add_response(
        method="POST",
        url="http://testserver/api/v1/profiles/compile",
        json=_compile_response(),
    )
    out_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "pull", "--profile", PROFILE_ID, "--target", "claude-code",
            "--path", str(out_dir), "--force", "--strict",
        ],
    )

    assert result.exit_code == 0


def test_pull_dry_run_strict_exits_nonzero_when_warnings_present(
    httpx_mock: HTTPXMock, logged_in: None, tmp_path: Path
) -> None:
    """--strict still flags a problem in --dry-run mode, even though nothing
    is written either way — strict mode never *prevents* the operation, it
    only affects the exit code."""
    httpx_mock.add_response(
        method="POST",
        url="http://testserver/api/v1/profiles/compile",
        json=_compile_response(
            warnings=[{"level": "warning", "code": "name_collision", "message": "collision"}]
        ),
    )
    out_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "pull", "--profile", PROFILE_ID, "--target", "claude-code",
            "--path", str(out_dir), "--dry-run", "--strict",
        ],
    )

    assert result.exit_code == 1
    assert "Dry run complete" in result.stdout
    # Dry run means nothing is written, warnings or not.
    assert not out_dir.exists()


def test_pull_warning_message_with_rich_markup_characters_does_not_crash(
    httpx_mock: HTTPXMock, logged_in: None, tmp_path: Path
) -> None:
    """A collection/artifact name embedded in the warning message could
    contain text that looks like Rich markup (e.g. from a user-chosen
    collection name) — this must be escaped, not interpreted, or a message
    containing something bracket-shaped can corrupt output or crash rprint
    with a MarkupError."""
    dangerous_message = (
        "Artifact 'x' is defined in both '[/bold]injected' and 'b [weird]'; 'b [weird]' wins."
    )
    httpx_mock.add_response(
        method="POST",
        url="http://testserver/api/v1/profiles/compile",
        json=_compile_response(
            warnings=[{"level": "warning", "code": "name_collision", "message": dangerous_message}]
        ),
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
    assert result.exception is None
    # The literal message content survives (escaped, not swallowed/misparsed).
    assert "injected" in result.stdout
    assert "weird" in result.stdout
