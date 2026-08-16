"""Tests for the local companion server used by the web UI's Import page."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from myace_cli.local_server import build_app

ALLOWED_ORIGIN = "https://myace.example.com"


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app(ALLOWED_ORIGIN))


@pytest.fixture
def skill_dir(tmp_path: Path) -> Path:
    skill = tmp_path / "skills" / "example-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: An example\n---\n\nDo the thing.\n"
    )
    return tmp_path


def test_health_reports_allowed_origin(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "server": ALLOWED_ORIGIN}


def test_health_reflects_cors_header_for_allowed_origin(client: TestClient) -> None:
    res = client.get("/health", headers={"Origin": ALLOWED_ORIGIN})
    assert res.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_scan_succeeds_with_correct_origin_and_header(client: TestClient, skill_dir: Path) -> None:
    res = client.post(
        "/scan",
        json={"path": str(skill_dir), "framework": "opencode"},
        headers={"Origin": ALLOWED_ORIGIN, "X-MyACE-Companion": "1"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["artifact_count"] == 1
    assert data["artifacts"][0]["name"] == "example-skill"


def test_scan_rejects_missing_companion_header(client: TestClient, skill_dir: Path) -> None:
    res = client.post(
        "/scan",
        json={"path": str(skill_dir), "framework": "opencode"},
        headers={"Origin": ALLOWED_ORIGIN},
    )
    assert res.status_code == 400


def test_scan_rejects_wrong_origin(client: TestClient, skill_dir: Path) -> None:
    res = client.post(
        "/scan",
        json={"path": str(skill_dir), "framework": "opencode"},
        headers={"Origin": "https://evil.example.com", "X-MyACE-Companion": "1"},
    )
    assert res.status_code == 403


def test_scan_rejects_missing_origin(client: TestClient, skill_dir: Path) -> None:
    res = client.post(
        "/scan",
        json={"path": str(skill_dir), "framework": "opencode"},
        headers={"X-MyACE-Companion": "1"},
    )
    assert res.status_code == 403


def test_preflight_allows_matching_origin_and_sets_private_network_header(
    client: TestClient,
) -> None:
    res = client.options(
        "/scan",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Private-Network": "true",
        },
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert res.headers["access-control-allow-private-network"] == "true"


def test_preflight_rejects_mismatched_origin(client: TestClient) -> None:
    res = client.options(
        "/scan",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.status_code == 403


def test_scan_missing_directory_returns_404(client: TestClient, tmp_path: Path) -> None:
    res = client.post(
        "/scan",
        json={"path": str(tmp_path / "does-not-exist"), "framework": "opencode"},
        headers={"Origin": ALLOWED_ORIGIN, "X-MyACE-Companion": "1"},
    )
    assert res.status_code == 404


def test_audit_succeeds_with_correct_origin_and_header(client: TestClient, skill_dir: Path) -> None:
    res = client.post(
        "/audit",
        json={"path": str(skill_dir)},
        headers={"Origin": ALLOWED_ORIGIN, "X-MyACE-Companion": "1"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "score" in data
    assert "targets" in data
    assert "gaps" in data
    assert "duplicates" in data


def test_audit_rejects_missing_companion_header(client: TestClient, skill_dir: Path) -> None:
    res = client.post(
        "/audit",
        json={"path": str(skill_dir)},
        headers={"Origin": ALLOWED_ORIGIN},
    )
    assert res.status_code == 400


def test_audit_rejects_wrong_origin(client: TestClient, skill_dir: Path) -> None:
    res = client.post(
        "/audit",
        json={"path": str(skill_dir)},
        headers={"Origin": "https://evil.example.com", "X-MyACE-Companion": "1"},
    )
    assert res.status_code == 403


def test_audit_rejects_missing_origin(client: TestClient, skill_dir: Path) -> None:
    res = client.post(
        "/audit",
        json={"path": str(skill_dir)},
        headers={"X-MyACE-Companion": "1"},
    )
    assert res.status_code == 403


def test_audit_missing_directory_returns_404(client: TestClient, tmp_path: Path) -> None:
    res = client.post(
        "/audit",
        json={"path": str(tmp_path / "does-not-exist")},
        headers={"Origin": ALLOWED_ORIGIN, "X-MyACE-Companion": "1"},
    )
    assert res.status_code == 404


def test_audit_preflight_allows_matching_origin_and_sets_private_network_header(
    client: TestClient,
) -> None:
    res = client.options(
        "/audit",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Private-Network": "true",
        },
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert res.headers["access-control-allow-private-network"] == "true"
