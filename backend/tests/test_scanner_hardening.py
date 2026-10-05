"""Scanner confinement: path traversal, symlink escape, git SSRF/subdirectory."""

from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.services import scanner


@pytest.fixture
def scan_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "home"
    root.mkdir()
    monkeypatch.setattr(settings, "scan_root", str(root))
    return root


def test_dotdot_cannot_escape_scan_root(scan_root: Path, tmp_path: Path) -> None:
    (tmp_path / "outside").mkdir()
    with pytest.raises(PermissionError):
        scanner.scan_directory(f"{scan_root}/../outside")


def test_symlinked_agent_pointing_outside_scan_root_is_skipped(
    scan_root: Path, tmp_path: Path
) -> None:
    secret = tmp_path / "secret.md"
    secret.write_text("TOP SECRET")
    agents = scan_root / "cfg" / "agents"
    agents.mkdir(parents=True)
    (agents / "leak.md").symlink_to(secret)
    (agents / "ok.md").write_text("fine")

    names = [a["name"] for a in scanner.scan_directory(scan_root / "cfg")]
    assert names == ["ok"]


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1/x.git",
        "https://169.254.169.254/latest",
        "https://10.0.0.5/x.git",
        "https://[::1]/x.git",
        "git://192.168.1.1/x.git",
    ],
)
def test_git_url_to_non_public_host_is_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        scanner._validate_git_url(url)


def test_git_url_rejects_bad_scheme_and_missing_host() -> None:
    with pytest.raises(ValueError):
        scanner._validate_git_url("file:///etc/passwd")
    with pytest.raises(ValueError):
        scanner._validate_git_url("https:///nohost")


def _fake_clone(populate):  # type: ignore[no-untyped-def]
    def clone_from(url: str, to_path: str, **kwargs: object) -> None:
        populate(Path(to_path), kwargs)

    return clone_from


def test_git_scan_works_despite_scan_root_and_skips_escaping_symlinks(
    scan_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = tmp_path / "secret.md"
    secret.write_text("TOP SECRET")
    seen: dict[str, object] = {}

    def populate(dest: Path, kwargs: dict[str, object]) -> None:
        seen.update(kwargs)
        (dest / "agents").mkdir()
        (dest / "agents" / "real.md").write_text("hello")
        (dest / "agents" / "leak.md").symlink_to(secret)

    monkeypatch.setattr(scanner, "_assert_public_host", lambda h, p: None)
    monkeypatch.setattr(scanner.git.Repo, "clone_from", _fake_clone(populate))

    artifacts = scanner.scan_git_repository("https://example.com/r.git")
    assert [a["name"] for a in artifacts] == ["real"]
    assert seen["kill_after_timeout"] == settings.git_clone_timeout_seconds
    assert seen["env"]["GIT_CONFIG_VALUE_0"] == "false"  # type: ignore[index]


@pytest.mark.parametrize("subdir", ["..", "../..", "/etc", "sub/../.."])
def test_git_subdirectory_cannot_leave_clone(
    subdir: str, scan_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scanner, "_assert_public_host", lambda h, p: None)
    monkeypatch.setattr(
        scanner.git.Repo, "clone_from", _fake_clone(lambda dest, kw: (dest / "sub").mkdir())
    )
    with pytest.raises(PermissionError):
        scanner.scan_git_repository("https://example.com/r.git", subdirectory=subdir)


def test_git_subdirectory_inside_clone_is_scanned(
    scan_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def populate(dest: Path, kwargs: dict[str, object]) -> None:
        (dest / "cfg" / "commands").mkdir(parents=True)
        (dest / "cfg" / "commands" / "go.md").write_text("run")

    monkeypatch.setattr(scanner, "_assert_public_host", lambda h, p: None)
    monkeypatch.setattr(scanner.git.Repo, "clone_from", _fake_clone(populate))
    artifacts = scanner.scan_git_repository("https://example.com/r.git", subdirectory="cfg")
    assert [a["name"] for a in artifacts] == ["go"]


@pytest.mark.asyncio
async def test_scan_route_rejects_internal_git_host(async_client: AsyncClient) -> None:
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "scan@example.com", "password": "password123", "display_name": "S"},
    )
    assert reg.status_code == 201
    res = await async_client.post(
        "/api/v1/collections/scan",
        json={"source_type": "git", "git_url": "https://169.254.169.254/x.git"},
    )
    assert res.status_code == 400


def test_real_gitpython_accepts_clone_hardening_kwargs(tmp_path: Path) -> None:
    """The fake clone above can't catch GitPython rejecting an option, so run
    the exact kwargs scan_git_repository() passes against a real local repo."""
    import subprocess

    src = tmp_path / "src"
    subprocess.run(["git", "init", "-q", str(src)], check=True)
    subprocess.run(
        ["git", "-c", "user.email=a@b", "-c", "user.name=n", "-C", str(src),
         "commit", "-q", "--allow-empty", "-m", "x"],
        check=True,
    )
    dest = tmp_path / "dest"
    repo = scanner.git.Repo.clone_from(
        f"file://{src}", str(dest), depth=1, single_branch=True,
        env={"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "http.followRedirects",
             "GIT_CONFIG_VALUE_0": "false"},
        kill_after_timeout=settings.git_clone_timeout_seconds,
    )
    assert repo.working_tree_dir
