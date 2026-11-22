"""Tests for the companion server's opt-in direct-apply path.

Every test uses `tmp_path` and a fake compiled-profile fetcher — nothing
reaches the network and nothing is written outside the temporary root.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from myace_cli import local_server
from myace_cli.local_server import build_app

ALLOWED_ORIGIN = "https://myace.example.com"
HEADERS = {"Origin": ALLOWED_ORIGIN, "X-MyACE-Companion": "1"}
PROFILE_ID = "00000000-0000-0000-0000-000000000001"


def files_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


class FakeFetcher:
    """Stand-in for the server call that returns a compiled profile."""

    def __init__(
        self,
        files: dict[str, str],
        *,
        profile_name: str = "Test Profile",
        warnings: list[dict[str, str]] | None = None,
    ) -> None:
        self.files = dict(files)
        self.profile_name = profile_name
        self.warnings = warnings or []
        self.calls: list[tuple[str, str]] = []

    def __call__(
        self, credentials: dict[str, str], profile_id: str, target: str
    ) -> dict[str, Any]:
        self.calls.append((profile_id, target))
        return {
            "files": dict(self.files),
            "profile_id": profile_id,
            "profile_name": self.profile_name,
            "target": target,
            "compiled_hash": "deadbeef",
            "warnings": list(self.warnings),
        }


def make_client(fetcher: Any, *, allow_apply: bool = True) -> TestClient:
    return TestClient(
        build_app(
            ALLOWED_ORIGIN,
            allow_apply=allow_apply,
            credentials={"server": "https://srv.example", "token": "test-token"},
            fetch_compiled=fetcher,
        )
    )


def preview_body(
    project_root: Path | None,
    *,
    target: str = "claude-code",
    location: str = "project",
) -> dict[str, Any]:
    return {
        "profile_id": PROFILE_ID,
        "target": target,
        "location": location,
        "project_root": str(project_root) if project_root is not None else None,
    }


def apply_body(
    preview: dict[str, Any],
    *,
    confirm: bool = True,
    project_root: Path | None,
) -> dict[str, Any]:
    body = preview_body(
        project_root, target=preview["target"], location=preview["location"]
    )
    body["preview_id"] = preview["preview_id"]
    body["confirm"] = confirm
    return body


def post_preview(client: TestClient, body: dict[str, Any]) -> Any:
    return client.post("/apply/preview", json=body, headers=HEADERS)


def post_apply(client: TestClient, body: dict[str, Any]) -> Any:
    return client.post("/apply", json=body, headers=HEADERS)


def files_by_relative(preview: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["relative_path"]: entry for entry in preview["files"]}


# ── /health capability discovery ──────────────────────────────────────────


def test_health_reports_apply_disabled_by_default(tmp_path: Path) -> None:
    client = TestClient(build_app(ALLOWED_ORIGIN))
    data = client.get("/health").json()
    assert data["apply"]["supported"] is False
    assert data["apply"]["targets"] == list(local_server.APPLY_TARGETS)


def test_health_reports_apply_enabled(tmp_path: Path) -> None:
    client = make_client(FakeFetcher({}))
    data = client.get("/health").json()
    assert data["apply"]["supported"] is True
    assert "opencode" in data["apply"]["targets"]
    assert "claude-code" in data["apply"]["targets"]
    # Flat targets are project-only, not machine-installable.
    assert "claude-code" in data["apply"]["machine_targets"]
    assert "aider" not in data["apply"]["machine_targets"]


# ── Preview diff ──────────────────────────────────────────────────────────


def test_preview_reports_added_changed_unchanged(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "CLAUDE.md").write_text("old\n")
    skill = root / ".claude" / "skills" / "s" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("same\n")

    fetcher = FakeFetcher(
        {
            "CLAUDE.md": "new\n",
            ".claude/agents/x.md": "agent\n",
            ".claude/skills/s/SKILL.md": "same\n",
        }
    )
    client = make_client(fetcher)

    res = post_preview(client, preview_body(root))
    assert res.status_code == 200, res.text
    preview = res.json()

    assert preview["root"] == str(root.resolve())
    assert preview["profile_name"] == "Test Profile"
    assert preview["preview_id"]
    assert preview["diff_hash"]

    entries = files_by_relative(preview)
    assert entries["CLAUDE.md"]["action"] == "changed"
    assert entries["CLAUDE.md"]["exists"] is True
    assert entries[".claude/agents/x.md"]["action"] == "added"
    assert entries[".claude/agents/x.md"]["exists"] is False
    assert entries[".claude/skills/s/SKILL.md"]["action"] == "unchanged"
    assert entries["CLAUDE.md"]["bytes"] == len("new\n")
    assert len(entries["CLAUDE.md"]["sha256"]) == 64


def test_preview_does_not_write_anything(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(FakeFetcher({"CLAUDE.md": "new\n"}))
    res = post_preview(client, preview_body(root))
    assert res.status_code == 200
    assert not (root / "CLAUDE.md").exists()


# ── Confirmation gate ─────────────────────────────────────────────────────


def test_apply_refuses_without_confirm(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(FakeFetcher({"CLAUDE.md": "new\n"}))
    preview = post_preview(client, preview_body(root)).json()

    res = post_apply(client, apply_body(preview, confirm=False, project_root=root))
    assert res.status_code == 400
    assert "confirm" in res.json()["detail"]
    assert not (root / "CLAUDE.md").exists()

    # The refused attempt must not consume the preview token.
    res = post_apply(client, apply_body(preview, confirm=True, project_root=root))
    assert res.status_code == 200, res.text
    assert (root / "CLAUDE.md").read_text() == "new\n"


def test_apply_requires_preview_id(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(FakeFetcher({"CLAUDE.md": "new\n"}))
    body = preview_body(root)
    body["confirm"] = True
    res = post_apply(client, body)
    assert res.status_code == 422


def test_apply_rejects_unknown_preview_id(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(FakeFetcher({"CLAUDE.md": "new\n"}))
    body = preview_body(root)
    body["preview_id"] = "not-a-real-preview"
    body["confirm"] = True
    res = post_apply(client, body)
    assert res.status_code == 400


def test_preview_token_is_single_use(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(FakeFetcher({"CLAUDE.md": "new\n"}))
    preview = post_preview(client, preview_body(root)).json()

    first = post_apply(client, apply_body(preview, project_root=root))
    assert first.status_code == 200

    second = post_apply(client, apply_body(preview, project_root=root))
    assert second.status_code == 400


def test_expired_preview_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    monkeypatch.setattr(local_server, "PREVIEW_TTL_SECONDS", 0)
    client = make_client(FakeFetcher({"CLAUDE.md": "new\n"}))
    preview = post_preview(client, preview_body(root)).json()

    res = post_apply(client, apply_body(preview, project_root=root))
    assert res.status_code == 400
    assert not (root / "CLAUDE.md").exists()


# ── Writing + backups ─────────────────────────────────────────────────────


def test_apply_writes_files(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(
        FakeFetcher({"CLAUDE.md": "new\n", ".claude/agents/x.md": "agent\n"})
    )
    preview = post_preview(client, preview_body(root)).json()

    res = post_apply(client, apply_body(preview, project_root=root))
    assert res.status_code == 200, res.text
    result = res.json()

    assert (root / "CLAUDE.md").read_text() == "new\n"
    assert (root / ".claude" / "agents" / "x.md").read_text() == "agent\n"
    written = {Path(path) for path in result["written"]}
    assert (root / "CLAUDE.md").resolve() in {p.resolve() for p in written}
    assert result["backup_dir"] is None


def test_apply_backs_up_overwritten_file_before_writing(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "CLAUDE.md").write_text("original\n")

    client = make_client(FakeFetcher({"CLAUDE.md": "replacement\n"}))
    preview = post_preview(client, preview_body(root)).json()
    assert files_by_relative(preview)["CLAUDE.md"]["action"] == "changed"

    res = post_apply(client, apply_body(preview, project_root=root))
    assert res.status_code == 200, res.text
    result = res.json()

    assert (root / "CLAUDE.md").read_text() == "replacement\n"
    assert result["backup_dir"] is not None
    backup_dir = Path(result["backup_dir"])
    assert backup_dir.is_relative_to(root)
    assert (backup_dir / "CLAUDE.md").read_text() == "original\n"
    assert re.fullmatch(r"\d{8}T\d{12,}Z(-\d+)?", backup_dir.name)


def test_apply_never_deletes_unrelated_files(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "keep.txt").write_text("keep\n")

    client = make_client(FakeFetcher({"CLAUDE.md": "new\n"}))
    preview = post_preview(client, preview_body(root)).json()
    post_apply(client, apply_body(preview, project_root=root))

    assert (root / "keep.txt").read_text() == "keep\n"


def test_apply_writes_sync_manifest(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(FakeFetcher({"CLAUDE.md": "new\n"}))
    preview = post_preview(client, preview_body(root)).json()
    res = post_apply(client, apply_body(preview, project_root=root))
    assert res.status_code == 200, res.text

    manifest_file = root / ".myace" / "claude-code.manifest.json"
    assert res.json()["manifest"] == str(manifest_file)
    assert manifest_file.exists()

    manifest = json.loads(manifest_file.read_text())
    assert manifest["profile_id"] == PROFILE_ID
    assert manifest["target"] == "claude-code"
    assert manifest["compiled_hash"] == "deadbeef"
    assert manifest["files"]["CLAUDE.md"] == files_hash("new\n")


def test_apply_leaves_no_temporary_files(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(FakeFetcher({"CLAUDE.md": "new\n"}))
    preview = post_preview(client, preview_body(root)).json()
    post_apply(client, apply_body(preview, project_root=root))

    assert not list(root.rglob(".myace-tmp-*"))


def test_apply_refuses_when_diff_changed_since_preview(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    fetcher = FakeFetcher({"CLAUDE.md": "new\n"})
    client = make_client(fetcher)
    preview = post_preview(client, preview_body(root)).json()

    fetcher.files = {"CLAUDE.md": "changed-after-preview\n"}
    res = post_apply(client, apply_body(preview, project_root=root))
    assert res.status_code == 409
    assert not (root / "CLAUDE.md").exists()


def test_apply_refuses_when_local_file_changed_since_preview(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "CLAUDE.md").write_text("original\n")

    client = make_client(FakeFetcher({"CLAUDE.md": "replacement\n"}))
    preview = post_preview(client, preview_body(root)).json()

    # A local hand-edit after the preview must invalidate it even though the
    # server's compiled content has not changed.
    (root / "CLAUDE.md").write_text("user edit after preview\n")
    res = post_apply(client, apply_body(preview, project_root=root))
    assert res.status_code == 409
    assert (root / "CLAUDE.md").read_text() == "user edit after preview\n"


# ── Path confinement ──────────────────────────────────────────────────────


def test_preview_rejects_path_traversal(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(FakeFetcher({"../escape.txt": "x\n"}))
    res = post_preview(client, preview_body(root))
    assert res.status_code == 400
    assert not (tmp_path / "escape.txt").exists()


def test_preview_rejects_absolute_path(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(FakeFetcher({"/etc/passwd-escape": "x\n"}))
    res = post_preview(client, preview_body(root))
    assert res.status_code == 400


def test_preview_rejects_symlinked_directory_escape(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / ".claude").symlink_to(outside)

    client = make_client(FakeFetcher({".claude/agents/x.md": "agent\n"}))
    res = post_preview(client, preview_body(root))
    assert res.status_code == 400
    assert "outside the install root" in res.json()["detail"]


def test_preview_rejects_symlinked_file_escape(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "CLAUDE.md").symlink_to(outside / "secret.md")

    client = make_client(FakeFetcher({"CLAUDE.md": "x\n"}))
    res = post_preview(client, preview_body(root))
    assert res.status_code == 400


def test_preview_rejects_directory_in_the_way(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "CLAUDE.md").mkdir()
    client = make_client(FakeFetcher({"CLAUDE.md": "x\n"}))
    res = post_preview(client, preview_body(root))
    assert res.status_code == 400


def test_preview_rejects_backup_directory_target(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(FakeFetcher({".myace-backups/evil.txt": "x\n"}))
    res = post_preview(client, preview_body(root))
    assert res.status_code == 400


def test_preview_rejects_manifest_directory_target(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(FakeFetcher({".myace/evil.txt": "x\n"}))
    res = post_preview(client, preview_body(root))
    assert res.status_code == 400


def test_preview_rejects_colliding_machine_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(local_server, "_home", lambda: tmp_path / "home")
    client = make_client(
        FakeFetcher({"CLAUDE.md": "a\n", ".claude/CLAUDE.md": "b\n"})
    )
    res = post_preview(client, preview_body(None, location="machine"))
    assert res.status_code == 400


def test_preview_rejects_normalized_path_collision(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(
        FakeFetcher({"a/b.txt": "one\n", "a/./b.txt": "two\n"})
    )
    res = post_preview(client, preview_body(root))
    assert res.status_code == 400


# ── Target + root validation ──────────────────────────────────────────────


def test_unknown_target_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(FakeFetcher({"x": "y"}))
    res = post_preview(client, preview_body(root, target="not-a-target"))
    assert res.status_code == 400
    assert "Unknown target" in res.json()["detail"]


def test_relative_project_root_is_rejected(tmp_path: Path) -> None:
    client = make_client(FakeFetcher({"CLAUDE.md": "x\n"}))
    body = preview_body(None)
    body["project_root"] = "relative/path"
    res = post_preview(client, body)
    assert res.status_code == 400
    assert "absolute" in res.json()["detail"]


def test_nonexistent_project_root_is_rejected(tmp_path: Path) -> None:
    client = make_client(FakeFetcher({"CLAUDE.md": "x\n"}))
    res = post_preview(client, preview_body(tmp_path / "does-not-exist"))
    assert res.status_code == 400
    assert "does not exist" in res.json()["detail"]


# ── Machine location ──────────────────────────────────────────────────────


def test_machine_location_rebases_onto_home_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(local_server, "_home", lambda: tmp_path / "home")
    client = make_client(
        FakeFetcher({".claude/agents/x.md": "agent\n", "CLAUDE.md": "instructions\n"})
    )

    res = post_preview(client, preview_body(None, location="machine"))
    assert res.status_code == 200, res.text
    preview = res.json()
    assert preview["root"] == str(tmp_path / "home" / ".claude")

    entries = files_by_relative(preview)
    assert set(entries) == {"agents/x.md", "CLAUDE.md"}

    applied = post_apply(client, apply_body(preview, project_root=None))
    assert applied.status_code == 200, applied.text
    assert (tmp_path / "home" / ".claude" / "agents" / "x.md").read_text() == "agent\n"
    assert (tmp_path / "home" / ".claude" / "CLAUDE.md").read_text() == "instructions\n"


@pytest.mark.parametrize("target", ["aider", "goose", "cline", "copilot-cli"])
def test_machine_location_rejected_for_project_only_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    monkeypatch.setattr(local_server, "_home", lambda: tmp_path / "home")
    client = make_client(FakeFetcher({"AGENTS.md": "x\n"}))
    res = post_preview(
        client, preview_body(None, target=target, location="machine")
    )
    assert res.status_code == 400
    assert "machine-level install root" in res.json()["detail"]
    assert not (tmp_path / "home").exists()


# ── Opt-in / security gate ────────────────────────────────────────────────

def test_apply_endpoints_are_disabled_by_default(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(FakeFetcher({"CLAUDE.md": "x\n"}), allow_apply=False)

    preview_res = post_preview(client, preview_body(root))
    assert preview_res.status_code == 403
    assert "disabled" in preview_res.json()["detail"]

    body = preview_body(root)
    body["preview_id"] = "whatever"
    body["confirm"] = True
    assert post_apply(client, body).status_code == 403


@pytest.mark.parametrize("path", ["/apply/preview", "/apply"])
def test_apply_routes_require_companion_header(tmp_path: Path, path: str) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(FakeFetcher({"CLAUDE.md": "x\n"}))
    body = preview_body(root)
    body["preview_id"] = "whatever"
    body["confirm"] = True
    res = client.post(path, json=body, headers={"Origin": ALLOWED_ORIGIN})
    assert res.status_code == 400
    assert "X-MyACE-Companion" in res.json()["detail"]


@pytest.mark.parametrize("path", ["/apply/preview", "/apply"])
@pytest.mark.parametrize(
    "origin",
    ["https://evil.example.com", None],
)
def test_apply_routes_require_exact_origin(
    tmp_path: Path, path: str, origin: str | None
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(FakeFetcher({"CLAUDE.md": "x\n"}))
    body = preview_body(root)
    body["preview_id"] = "whatever"
    body["confirm"] = True
    headers = {"X-MyACE-Companion": "1"}
    if origin is not None:
        headers["Origin"] = origin
    res = client.post(path, json=body, headers=headers)
    assert res.status_code == 403


def test_apply_preflight_allows_matching_origin() -> None:
    client = make_client(FakeFetcher({}))
    res = client.options(
        "/apply/preview",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Private-Network": "true",
        },
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert res.headers["access-control-allow-private-network"] == "true"


def test_oversized_request_body_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(FakeFetcher({"CLAUDE.md": "x\n"}))
    body = preview_body(root)
    body["project_root"] = "x" * (local_server.MAX_REQUEST_BYTES + 1)
    res = client.post("/apply/preview", json=body, headers=HEADERS)
    assert res.status_code == 413


def test_project_root_defaults_to_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "cwd-project"
    project.mkdir()
    monkeypatch.chdir(project)
    client = make_client(FakeFetcher({"CLAUDE.md": "x\n"}))

    body = preview_body(None)
    res = post_preview(client, body)
    assert res.status_code == 200, res.text
    assert res.json()["root"] == str(project.resolve())


# ── Upstream fetch error mapping ──────────────────────────────────────────


def status_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://srv.example/api/v1/profiles/compile")
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError(f"status {status}", request=request, response=response)


def raising_fetcher(error: Exception) -> Any:
    def fetch(credentials: dict[str, str], profile_id: str, target: str) -> dict:
        raise error

    return fetch


@pytest.mark.parametrize(
    ("upstream_status", "expected"),
    [(404, 404), (401, 502), (403, 502), (500, 502)],
)
def test_fetch_http_status_errors_are_mapped(
    tmp_path: Path, upstream_status: int, expected: int
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    client = make_client(raising_fetcher(status_error(upstream_status)))
    res = post_preview(client, preview_body(root))
    assert res.status_code == expected


def test_fetch_connect_error_maps_to_502(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    request = httpx.Request("POST", "https://srv.example/api/v1/profiles/compile")
    client = make_client(raising_fetcher(httpx.ConnectError("refused", request=request)))
    res = post_preview(client, preview_body(root))
    assert res.status_code == 502
    assert "Could not reach" in res.json()["detail"]

