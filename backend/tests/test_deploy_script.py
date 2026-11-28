"""The deploy script's plan: which steps a change set needs.

`scripts/deploy.sh --plan-only` needs only git, so the classification that
decides whether a deploy rebuilds an image, migrates or reconciles can be tested
against a throwaway repository. The real run (docker, backups, reconcile) is
exercised on the server; what is tested here is the part that decides *what* to do.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "deploy.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash is required")


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _plan(tmp_path: Path, changed: list[str]) -> str:
    """Commit a baseline, then a commit touching `changed`, and return the plan text."""
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("base\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    before = _git(repo, "rev-parse", "HEAD")
    for name in changed:
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("changed\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "change")
    after = _git(repo, "rev-parse", "HEAD")

    result = subprocess.run(
        ["bash", str(SCRIPT), "--plan-only", "--from", before, "--to", after],
        env={"DEPLOY_REPO_DIR": str(repo), "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _steps(plan: str) -> dict[str, bool]:
    steps: dict[str, bool] = {}
    for line in plan.splitlines():
        line = line.strip()
        if line.startswith("[x] ") or line.startswith("[ ] "):
            steps[line[4:].split("  ")[0].strip()] = line.startswith("[x]")
    return steps


def test_docs_and_ci_only_changes_deploy_nothing(tmp_path: Path) -> None:
    plan = _plan(tmp_path, ["docs/guide.md", "CHANGELOG.md", ".github/workflows/ci.yml", "scripts/x.sh"])

    assert not any(_steps(plan).values())
    assert "Nothing to deploy beyond the pull" in plan


def test_backend_tests_only_do_not_restart_anything(tmp_path: Path) -> None:
    plan = _plan(tmp_path, ["backend/tests/test_x.py"])

    assert not any(_steps(plan).values())


def test_backend_code_restarts_the_backend_without_rebuilding(tmp_path: Path) -> None:
    steps = _steps(_plan(tmp_path, ["backend/app/api/collections.py"]))

    assert steps["backend restart"] is True
    assert steps["backend image rebuild"] is False
    assert steps["frontend image rebuild"] is False
    assert steps["reconcile seeded packs"] is False


def test_migration_is_planned_and_restarts_the_backend(tmp_path: Path) -> None:
    steps = _steps(_plan(tmp_path, ["backend/alembic/versions/abc123_x.py"]))

    assert steps["alembic upgrade head"] is True
    assert steps["backend restart"] is True


@pytest.mark.parametrize("path", ["backend/Dockerfile", "backend/pyproject.toml"])
def test_dependency_or_image_changes_rebuild_the_backend(tmp_path: Path, path: str) -> None:
    steps = _steps(_plan(tmp_path, [path]))

    assert steps["backend image rebuild"] is True
    assert steps["backend restart"] is True


def test_pack_content_restarts_and_reconciles(tmp_path: Path) -> None:
    steps = _steps(_plan(tmp_path, ["collections/additional/aws/AGENTS.md"]))

    # New packs seed on boot, so the backend restarts; existing packs need reconcile.
    assert steps["backend restart"] is True
    assert steps["reconcile seeded packs"] is True
    assert steps["frontend image rebuild"] is False


def test_the_registry_alone_triggers_reconcile(tmp_path: Path) -> None:
    steps = _steps(_plan(tmp_path, ["backend/app/services/seed_collections.py"]))

    assert steps["reconcile seeded packs"] is True
    assert steps["backend restart"] is True


def test_frontend_source_rebuilds_the_image_but_tests_do_not(tmp_path: Path) -> None:
    assert _steps(_plan(tmp_path / "a", ["frontend/src/pages/PackDetail.tsx"]))[
        "frontend image rebuild"
    ] is True
    assert _steps(_plan(tmp_path / "b", ["frontend/package.json"]))["frontend image rebuild"] is True
    assert _steps(_plan(tmp_path / "c", ["frontend/src/pages/PackDetail.test.tsx"]))[
        "frontend image rebuild"
    ] is False


def test_mcp_source_rebuilds_the_image_but_tests_do_not(tmp_path: Path) -> None:
    assert _steps(_plan(tmp_path / "a", ["mcp/backend.py"]))["mcp image rebuild"] is True
    assert _steps(_plan(tmp_path / "b", ["mcp/tests/test_backend.py"]))["mcp image rebuild"] is False


def test_compose_change_is_planned(tmp_path: Path) -> None:
    assert _steps(_plan(tmp_path, ["docker-compose.prod.yml"]))["compose up -d"] is True


def test_env_example_change_adds_a_note(tmp_path: Path) -> None:
    plan = _plan(tmp_path, [".env.example"])

    assert ".env.example changed" in plan


def test_a_release_commit_plans_every_image_and_a_reconcile(tmp_path: Path) -> None:
    steps = _steps(
        _plan(
            tmp_path,
            [
                "backend/pyproject.toml",
                "frontend/package.json",
                "backend/app/services/seed_collections.py",
                "collections/additional/python-developer/AGENTS.md",
                "mcp/server.py",
            ],
        )
    )

    assert all(steps[name] for name in (
        "backend image rebuild", "backend restart", "frontend image rebuild",
        "mcp image rebuild", "reconcile seeded packs",
    ))


def test_help_and_bad_options(tmp_path: Path) -> None:
    ok = subprocess.run(["bash", str(SCRIPT), "--help"], capture_output=True, text=True)
    assert ok.returncode == 0
    assert "--plan-only" in ok.stdout

    bad = subprocess.run(["bash", str(SCRIPT), "--nope"], capture_output=True, text=True)
    assert bad.returncode != 0
    assert "unknown option" in bad.stderr


def test_default_backup_dir_is_not_the_sidecars_root_owned_directory() -> None:
    """The first real deploy failed on `mkdir: Permission denied`: the default sat
    under ./backups, which the postgres-backup sidecar owns as root."""
    text = SCRIPT.read_text()
    default_line = next(line for line in text.splitlines() if line.startswith("BACKUP_DIR="))

    assert "$ROOT/backups" not in default_line
    assert "HOME" in default_line
