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
    cursor = get_adapter("aider")
    warnings = _check_unenforced_permissions(cursor, [agent], "aider")  # type: ignore[arg-type]
    assert [w.code for w in warnings] == ["permissions_not_enforced"]
    assert "reviewer" in warnings[0].message and "edit=deny" in warnings[0].message
    # claude-code enforces deny but not ask; opencode enforces everything.
    claude = _check_unenforced_permissions(get_adapter("claude-code"), [agent], "claude-code")  # type: ignore[arg-type]
    assert "execute=ask" in claude[0].message and "edit=deny" not in claude[0].message
    assert _check_unenforced_permissions(get_adapter("opencode"), [agent], "opencode") == []  # type: ignore[arg-type]
    assert _check_unenforced_permissions(cursor, [_agent(None)], "aider") == []  # type: ignore[arg-type]


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


# --- Phase 2: global policy rules as sidecar files only ----------------------

POLICY_BODY = (
    '{"rules": [{"capability": "execute", "effect": "ask", "match": "git push *"},'
    ' {"capability": "network", "effect": "deny"},'
    ' {"capability": "execute", "effect": "allow", "match": "ls"},'
    ' {"capability": "edit", "effect": "ask", "match": "x"}]}'
)


def _policy() -> CanonicalArtifact:
    return CanonicalArtifact(
        artifact_type="model_config", name="permissions:default", version="1.0.0",
        target_compatibility=[], priority=50, tags=["permissions"], description="p",
        body=POLICY_BODY,
    )


def test_policy_never_reaches_any_adapters_normal_output() -> None:
    from app.adapters.base import translate_artifacts

    for adapter in list_adapters():
        files = translate_artifacts(adapter, [_policy()])
        text = "\n".join(files.values())
        assert "permissions:default" not in text, adapter.adapter_name()
        assert ".claude/settings.json" not in files and "opencode.json" not in files


def test_policy_sidecars_are_restrict_only_and_never_a_config_file() -> None:
    from app.adapters.base import translate_artifacts

    claude = translate_artifacts(get_adapter("claude-code"), [_policy()])  # type: ignore[arg-type]
    assert list(claude) == [".claude/myace.permissions.json"]
    import json

    perms = json.loads(claude[".claude/myace.permissions.json"])["permissions"]
    assert perms == {"ask": ["Bash(git push *)"], "deny": ["WebFetch"]}  # allow + bad edit-match dropped
    oc = translate_artifacts(get_adapter("opencode"), [_policy()])  # type: ignore[arg-type]
    assert list(oc) == [".opencode/myace.permissions.json"]
    assert json.loads(oc[".opencode/myace.permissions.json"]) == {
        "permission": {"bash": {"git push *": "ask"}, "webfetch": "deny"}
    }
    assert translate_artifacts(get_adapter("aider"), [_policy()]) == {}  # type: ignore[arg-type]


def test_policy_on_unsupported_target_warns() -> None:
    cursor = _check_unenforced_permissions(get_adapter("aider"), [_policy()], "aider")  # type: ignore[arg-type]
    assert [w.code for w in cursor] == ["permissions_not_enforced"]
    assert _check_unenforced_permissions(get_adapter("claude-code"), [_policy()], "claude-code") == []  # type: ignore[arg-type]


def test_permissions_json_round_trips_through_export_and_scan(tmp_path: Path) -> None:
    scanned_policy = scanner._parse_permissions_json(_write(tmp_path / "permissions.json", POLICY_BODY))
    assert [a["name"] for a in scanned_policy] == ["permissions:default"]
    art = CanonicalArtifact(**{**{k: scanned_policy[0][k] for k in (
        "artifact_type", "name", "version", "priority", "tags", "description", "body")},
        "target_compatibility": []})
    exported = artifacts_to_files([art])
    assert "permissions.json" in exported
    again = scanner._parse_permissions_json(_write(tmp_path / "again.json", exported["permissions.json"]))
    assert again[0]["body"] == scanned_policy[0]["body"]
    assert scanner._parse_permissions_json(_write(tmp_path / "bad.json", "not json")) == []


def _write(path: Path, text: str) -> Path:
    path.write_text(text)
    return path


def test_every_starter_pack_ships_the_shared_ask_rules() -> None:
    import json

    for slug in ("software-engineer", "vibecoder", "data-scientist", "devops-engineer"):
        arts = _scan_seeded_collection(REPO / "collections/base" / slug)
        policy = next(a for a in arts if a["name"] == "permissions:default")
        matches = {r["match"] for r in json.loads(policy["body"])["rules"]}
        assert {"git push *", "rm -rf *", "sudo *"} <= matches, slug
    devops = next(a for a in _scan_seeded_collection(REPO / "collections/base/devops-engineer")
                  if a["name"] == "permissions:default")
    assert "terraform apply *" in devops["body"]


# --- Codex: a real rules file (restrict-only by Codex's own semantics) --------


def test_codex_gets_a_rules_file_for_expressible_shell_rules_only() -> None:
    from app.adapters.base import translate_artifacts

    files = translate_artifacts(get_adapter("codex-cli"), [_policy()])  # type: ignore[arg-type]
    rules = files[".codex/rules/myace.rules"]
    assert 'pattern=["git", "push"], decision="prompt"' in rules
    assert "allow" not in rules.replace("never allow", "")
    assert "webfetch" not in rules.lower()  # network=deny has no Codex form
    # network=deny cannot be expressed: reported, not silently dropped.
    warnings = _check_unenforced_permissions(get_adapter("codex-cli"), [_policy()], "codex-cli")  # type: ignore[arg-type]
    assert [w.code for w in warnings] == ["permissions_not_enforced"]
    assert "network=deny" in warnings[0].message and "git push" not in warnings[0].message


def test_codex_patterns_only_trailing_wildcard_and_safe_tokens() -> None:
    from app.adapters.codex_cli import _codex_pattern

    assert _codex_pattern("rm -rf *") == ["rm", "-rf"]
    assert _codex_pattern("sudo *") == ["sudo"]
    assert _codex_pattern("az * delete") is None
    assert _codex_pattern("echo $(whoami)") is None
    assert _codex_pattern("*") is None
    assert _codex_pattern("") is None


def test_codex_agents_still_report_per_agent_permissions_unenforced() -> None:
    warnings = _check_unenforced_permissions(
        get_adapter("codex-cli"), [_agent({"edit": "deny"})], "codex-cli"  # type: ignore[arg-type]
    )
    assert "edit=deny" in warnings[0].message


# --- Cursor and Copilot: native agent files, added alongside the old output ---


def test_cursor_emits_a_native_subagent_alongside_the_rule_file() -> None:
    files = get_adapter("cursor").translate([_agent({"edit": "deny", "network": "deny"})])  # type: ignore[union-attr]
    assert ".cursor/rules/reviewer.mdc" in files  # unchanged existing output
    fm = _frontmatter(files[".cursor/agents/reviewer.md"])
    assert fm["readonly"] is True and fm["name"] == "reviewer"
    free = _frontmatter(get_adapter("cursor").translate([_agent(None)])[".cursor/agents/reviewer.md"])  # type: ignore[union-attr]
    assert "readonly" not in free  # restrict-only: never written as false
    warnings = _check_unenforced_permissions(
        get_adapter("cursor"), [_agent({"edit": "deny", "network": "deny"})], "cursor"  # type: ignore[arg-type]
    )
    assert "network=deny" in warnings[0].message and "edit=deny" not in warnings[0].message


def test_copilot_emits_a_native_agent_with_a_tools_allow_list_minus_denied() -> None:
    files = get_adapter("copilot-cli").translate(  # type: ignore[union-attr]
        [_agent({"edit": "deny", "read": "deny", "execute": "ask"})]
    )
    assert ".github/instructions/agent-reviewer.instructions.md" in files  # unchanged
    fm = _frontmatter(files[".github/agents/reviewer.agent.md"])
    assert fm["tools"] == ["execute", "agent", "web", "todo"]  # read also drops search
    free = _frontmatter(
        get_adapter("copilot-cli").translate([_agent(None)])[".github/agents/reviewer.agent.md"]  # type: ignore[union-attr]
    )
    assert "tools" not in free  # omitted = everything, so unrestricted stays unrestricted
    warnings = _check_unenforced_permissions(
        get_adapter("copilot-cli"), [_agent({"edit": "deny", "execute": "ask"})], "copilot-cli"  # type: ignore[arg-type]
    )
    assert "execute=ask" in warnings[0].message and "edit=deny" not in warnings[0].message


def test_agent_dot_agent_md_scans_back_to_the_agent_name(tmp_path: Path) -> None:
    f = tmp_path / "reviewer.agent.md"
    f.write_text("---\ndescription: d\n---\nBody\n")
    assert scanner._parse_agent_file(f)["name"] == "reviewer"  # type: ignore[index]


# --- Item counts exclude the permission policy (invariant 20) ------------------


def test_counts_toward_total_excludes_only_permission_policies() -> None:
    from app.models.artifact import counts_toward_total

    assert not counts_toward_total("model_config", "permissions:default")
    assert counts_toward_total("model_config", "model:claude-sonnet")
    assert counts_toward_total("model_config", "mcp:github")
    assert counts_toward_total("rule", "permissions:default")  # only model_config policies


def test_seeded_base_pack_counts_leave_out_the_policy() -> None:
    scanned = _scan_seeded_collection(REPO / "collections/base/vibecoder")
    assert any(a["name"] == "permissions:default" for a in scanned)
    from app.models.artifact import counts_toward_total

    assert sum(1 for a in scanned if counts_toward_total(a["artifact_type"], a["name"])) == len(
        scanned
    ) - 1


class TestPolicyCountsViaApi:
    @pytest.mark.asyncio
    async def test_bulk_import_and_single_create_do_not_count_the_policy(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_user(db_session, "count-owner@test.com")
        await _login(async_client, "count-owner@test.com")
        policy = {
            "artifact_type": "model_config", "name": "permissions:default",
            "body": '{"rules": []}', "file_path": "permissions.json",
        }
        rule = {"artifact_type": "rule", "name": "r", "body": "b", "file_path": "AGENTS.md"}
        res = await async_client.post(
            "/api/v1/collections/import",
            json={"collection_name": "counted", "artifacts": [rule, policy]},
        )
        assert res.status_code == 201
        cid = res.json()["collection_id"] if "collection_id" in res.json() else res.json()["id"]
        got = await async_client.get(f"/api/v1/collections/{cid}")
        assert got.json()["artifact_count"] == 1  # two stored, one counted

        extra = await async_client.post(
            f"/api/v1/collections/{cid}/artifacts",
            json={**policy, "name": "permissions:other"},
        )
        assert extra.status_code == 201
        assert (await async_client.get(f"/api/v1/collections/{cid}")).json()["artifact_count"] == 1
        listed = await async_client.get(f"/api/v1/collections/{cid}/artifacts")
        assert len(listed.json()) == 3  # still stored and listed
