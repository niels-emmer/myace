"""Agent-level permissions compile into agent frontmatter only (ADR-0019)."""

from pathlib import Path

import pytest
import yaml
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import get_adapter, list_adapters
from app.adapters.base import restricting_permissions
from app.models.artifact import CanonicalArtifact
from app.services import scanner
from app.services.compiler import _check_unenforced_permissions
from app.services.github_export import artifacts_to_files
from app.services.seed_collections import _scan_seeded_collection
from tests.test_artifact_create import _create_collection, _create_user, _login

REPO = Path(__file__).resolve().parents[2]


def _agent(permissions: dict[str, str] | None, name: str = "reviewer") -> CanonicalArtifact:
    return CanonicalArtifact(
        artifact_type="agent", name=name, version="1.0.0", target_compatibility=[],
        priority=50, tags=["mode:subagent"], description="d", body="Body.",
        permissions=permissions,  # type: ignore[arg-type]
    )


def _frontmatter(content: str) -> dict:
    return yaml.safe_load(content.split("---\n")[1])


def test_allow_is_never_compiled() -> None:
    assert restricting_permissions(_agent({"edit": "allow", "execute": "ask"})) == {"execute": "ask"}
    assert restricting_permissions(_agent(None)) == {}


def test_claude_code_denies_become_disallowed_tools_only() -> None:
    files = get_adapter("claude-code").translate([_agent({"edit": "deny", "execute": "ask"})])  # type: ignore[union-attr]
    fm = _frontmatter(files[".claude/agents/reviewer.md"])
    assert fm["disallowedTools"] == ["Edit", "Write", "NotebookEdit"]
    assert "tools" not in fm  # never an allow-list: unrestricted agents keep inheriting
    assert "execute" not in str(fm)


def test_unrestricted_agent_gets_no_permission_keys() -> None:
    for target in ("claude-code", "opencode"):
        files = get_adapter(target).translate([_agent(None), _agent({"edit": "allow"}, "other")])  # type: ignore[union-attr]
        for content in files.values():
            assert "disallowedTools" not in content
            assert "permission:" not in content


def test_opencode_writes_permission_frontmatter_and_no_config_file() -> None:
    files = get_adapter("opencode").translate(  # type: ignore[union-attr]
        [_agent({"edit": "deny", "execute": "ask", "network": "deny"})]
    )
    fm = _frontmatter(files[".opencode/agents/reviewer.md"])
    assert fm["permission"] == {"edit": "deny", "bash": "ask", "webfetch": "deny"}
    assert "opencode.json" not in files, "permissions must never reach a shared config file"


def test_no_adapter_ever_emits_a_shared_settings_file() -> None:
    artifact = _agent({"edit": "deny", "execute": "deny"})
    for adapter in list_adapters():
        files = adapter.translate([artifact])
        assert ".claude/settings.json" not in files
        assert "settings.json" not in files
        assert not any(f.endswith("opencode.json") for f in files)


def test_unenforced_warning_names_agent_and_target() -> None:
    agent = _agent({"edit": "deny", "execute": "ask"})
    cursor = get_adapter("cursor")
    warnings = _check_unenforced_permissions(cursor, [agent], "cursor")  # type: ignore[arg-type]
    assert [w.code for w in warnings] == ["permissions_not_enforced"]
    assert "reviewer" in warnings[0].message and "edit=deny" in warnings[0].message
    # claude-code enforces deny but not ask; opencode enforces everything.
    claude = _check_unenforced_permissions(get_adapter("claude-code"), [agent], "claude-code")  # type: ignore[arg-type]
    assert "execute=ask" in claude[0].message and "edit=deny" not in claude[0].message
    assert _check_unenforced_permissions(get_adapter("opencode"), [agent], "opencode") == []  # type: ignore[arg-type]
    assert _check_unenforced_permissions(cursor, [_agent(None)], "cursor") == []  # type: ignore[arg-type]


def test_permissions_survive_export_and_scan(tmp_path: Path) -> None:
    files = artifacts_to_files([_agent({"edit": "deny", "network": "ask"})])
    root = tmp_path.resolve()
    for rel, content in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(content, encoding="utf-8")
    scanned = {a["name"]: a for a in scanner._scan_tree(root, confine_to=root)}
    assert scanned["reviewer"]["permissions"] == {"edit": "deny", "network": "ask"}


def test_scanner_drops_unknown_keys_and_distinguishes_absent_from_empty(tmp_path: Path) -> None:
    agent = tmp_path / "a.md"
    agent.write_text("---\npermissions: {edit: deny, bogus: deny, bash: maybe}\n---\nBody\n")
    assert scanner._parse_agent_file(agent)["permissions"] == {"edit": "deny"}  # type: ignore[index]
    agent.write_text("---\npermissions: {}\n---\nBody\n")
    assert scanner._parse_agent_file(agent)["permissions"] == {}  # type: ignore[index]
    agent.write_text("---\ndescription: x\n---\nBody\n")
    assert scanner._parse_agent_file(agent)["permissions"] is None  # type: ignore[index]


def test_starter_reviewers_cannot_edit_and_builders_are_unrestricted() -> None:
    swe = {a["name"]: a for a in _scan_seeded_collection(REPO / "collections/base/software-engineer")}
    for name in ("code-reviewer", "security-auditor", "verifier", "orchestrator"):
        assert swe[name]["permissions"]["edit"] == "deny", name
    assert swe["orchestrator"]["permissions"]["execute"] == "deny"
    assert swe["builder"]["permissions"] is None
    assert "delegate" not in (swe["orchestrator"]["permissions"] or {})  # must still route work
    adapter = get_adapter("claude-code")
    reviewer = CanonicalArtifact(**{k: swe["code-reviewer"][k] for k in (
        "artifact_type", "name", "version", "priority", "tags", "description", "body", "permissions")},
        target_compatibility=[])  # type: ignore[arg-type]
    out = adapter.translate([reviewer])[".claude/agents/code-reviewer.md"]  # type: ignore[union-attr]
    assert "disallowedTools" in out and "Edit" in out


class TestPermissionsApi:
    @pytest.mark.asyncio
    async def test_create_round_trips_and_rejects_bad_values(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, "perm-owner@test.com")
        await _login(async_client, "perm-owner@test.com")
        cid = await _create_collection(async_client, name="perms")
        url = f"/api/v1/collections/{cid}/artifacts"
        base = {"artifact_type": "agent", "name": "ro", "body": "b", "file_path": "agents/ro.md"}

        ok = await async_client.post(url, json={**base, "permissions": {"edit": "deny"}})
        assert ok.status_code == 201 and ok.json()["permissions"] == {"edit": "deny"}
        listed = await async_client.get(url)
        assert next(a for a in listed.json() if a["name"] == "ro")["permissions"] == {"edit": "deny"}

        for bad in ({"edit": "sometimes"}, {"teleport": "deny"}):
            res = await async_client.post(url, json={**base, "name": "bad", "permissions": bad})
            assert res.status_code == 422, bad

        aid = ok.json()["id"]
        cleared = await async_client.patch(f"{url}/{aid}", json={"permissions": None})
        assert cleared.status_code == 200 and cleared.json()["permissions"] is None
