"""The permission merge is additive, tighten-only, tracked and reversible (ADR-0019)."""

import json
from pathlib import Path

from myace_cli.permissions_merge import apply_plan, plan_merge, remove_applied

CLAUDE_SIDECAR = json.dumps(
    {"permissions": {"ask": ["Bash(git push *)", "Bash(sudo *)"], "deny": ["WebFetch"]}}
)
OC_SIDECAR = json.dumps({"permission": {"bash": {"git push *": "ask"}, "webfetch": "deny"}})


def _claude(tmp_path: Path, config: dict | None) -> tuple[Path, Path]:
    path = tmp_path / ".claude" / "settings.json"
    if config is not None:
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(config))
    return tmp_path, path


def test_claude_merge_adds_only_missing_entries_and_keeps_the_users_own(tmp_path: Path) -> None:
    base, path = _claude(
        tmp_path,
        {"model": "opus", "permissions": {"allow": ["Bash(ls)"], "ask": ["Bash(git push *)"]}},
    )
    plan = plan_merge(CLAUDE_SIDECAR, "claude-code", path)
    assert plan.added == {"ask": ["Bash(sudo *)"], "deny": ["WebFetch"]}
    apply_plan(plan, base)
    data = json.loads(path.read_text())
    assert data["model"] == "opus" and data["permissions"]["allow"] == ["Bash(ls)"]
    assert data["permissions"]["ask"] == ["Bash(git push *)", "Bash(sudo *)"]
    assert (path.parent / "settings.json.myace-bak").exists()


def test_never_overrides_a_user_allow_and_never_writes_allow(tmp_path: Path) -> None:
    base, path = _claude(tmp_path, {"permissions": {"allow": ["Bash(sudo *)"]}})
    plan = plan_merge(CLAUDE_SIDECAR, "claude-code", path)
    assert "Bash(sudo *)" not in plan.added.get("ask", [])
    assert any("explicitly allow" in s for s in plan.skipped)
    apply_plan(plan, base)
    assert json.loads(path.read_text())["permissions"]["allow"] == ["Bash(sudo *)"]


def test_remove_takes_back_only_what_was_added(tmp_path: Path) -> None:
    own = {"permissions": {"ask": ["Bash(git push *)"], "deny": ["Bash(curl *)"]}}
    base, path = _claude(tmp_path, own)
    apply_plan(plan_merge(CLAUDE_SIDECAR, "claude-code", path), base)
    removed = remove_applied(base, "claude-code")
    assert sorted(removed) == ["ask Bash(sudo *)", "deny WebFetch"]
    assert json.loads(path.read_text()) == own
    assert remove_applied(base, "claude-code") == []  # record is gone


def test_missing_config_is_created_and_removal_cleans_up(tmp_path: Path) -> None:
    base, path = _claude(tmp_path, None)
    apply_plan(plan_merge(CLAUDE_SIDECAR, "claude-code", path), base)
    assert json.loads(path.read_text())["permissions"]["deny"] == ["WebFetch"]
    remove_applied(base, "claude-code")
    assert json.loads(path.read_text()) == {}


def test_refuses_a_config_that_is_not_strict_json(tmp_path: Path) -> None:
    path = tmp_path / "opencode.json"
    original = '{\n  // my comment\n  "theme": "dark"\n}\n'
    path.write_text(original)
    plan = plan_merge(OC_SIDECAR, "opencode", path)
    assert plan.error and not plan.has_changes
    apply_plan(plan, tmp_path)
    assert path.read_text() == original


def test_opencode_merge_respects_user_values(tmp_path: Path) -> None:
    path = tmp_path / "opencode.json"
    path.write_text(json.dumps(
        {"permission": {"bash": {"git push *": "allow", "ls": "allow"}, "webfetch": "allow"}}
    ))
    plan = plan_merge(OC_SIDECAR, "opencode", path)
    assert plan.added == {} and len(plan.skipped) == 2  # kept the user's allow for both
    path.write_text(json.dumps({"permission": {"bash": {"ls": "allow"}}}))
    plan = plan_merge(OC_SIDECAR, "opencode", path)
    assert plan.added == {"bash": {"git push *": "ask"}, "webfetch": "deny"}
    apply_plan(plan, tmp_path)
    bash = json.loads(path.read_text())["permission"]["bash"]
    assert bash == {"ls": "allow", "git push *": "ask"}
    remove_applied(tmp_path, "opencode")
    assert json.loads(path.read_text()) == {"permission": {"bash": {"ls": "allow"}}}
