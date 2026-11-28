"""Tracked, additive, tighten-only merge of a pack's permission sidecar into a
framework's own config (ADR-0019, phase 2).

The compiled download never touches a user's `settings.json` / `opencode.json`;
it only ships a sidecar the framework ignores. This module is the one place
that writes user config, and only when asked (`myace pull --apply-permissions`):

- it adds `ask`/`deny` entries and nothing else — never an `allow`;
- it never edits or removes an entry it did not add, and never overrides a
  value the user set;
- it refuses a file that is not strict JSON (`opencode.json` may carry
  comments; rewriting it would silently strip them);
- it records exactly what it added in `.myace/<target>.permissions.json`, so
  `remove_applied()` can take back only that;
- it keeps a one-time `<file>.myace-bak` before the first write.

`plan_merge()` is pure (no I/O beyond reading the target) so the diff can be
shown and confirmed before `apply_plan()` writes anything.
"""

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# sidecar path (relative to the pulled output dir) -> (framework, project config path)
SIDECARS: dict[str, tuple[str, str]] = {
    ".claude/myace.permissions.json": ("claude-code", ".claude/settings.json"),
    ".opencode/myace.permissions.json": ("opencode", "opencode.json"),
}
USER_CONFIGS: dict[str, Path] = {
    "claude-code": Path.home() / ".claude" / "settings.json",
    "opencode": Path.home() / ".config" / "opencode" / "opencode.json",
}
RECORD_DIR = ".myace"


@dataclass
class MergePlan:
    framework: str
    config_path: Path
    added: dict[str, Any] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    error: str | None = None
    merged: dict[str, Any] | None = None  # the full config to write

    @property
    def has_changes(self) -> bool:
        return bool(self.added) and self.error is None


def _load_strict(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return {}, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, (
            f"{path} is not strict JSON (comments or a syntax error), so it will not "
            "be rewritten. Merge the sidecar into it by hand."
        )
    if not isinstance(data, dict):
        return None, f"{path} is not a JSON object; leaving it alone."
    return data, None


def _merge_claude(sidecar: dict[str, Any], config: dict[str, Any], plan: MergePlan) -> None:
    perms = config.setdefault("permissions", {})
    if not isinstance(perms, dict):
        plan.error = "`permissions` in the target config is not an object; leaving it alone."
        return
    allow = {e for e in perms.get("allow", []) if isinstance(e, str)}
    for kind in ("deny", "ask"):  # deny first so ask can see it
        current = perms.get(kind, [])
        if not isinstance(current, list):
            plan.skipped.append(f"{kind}: existing value is not a list")
            continue
        for entry in sidecar.get("permissions", {}).get(kind, []):
            if not isinstance(entry, str) or entry in current:
                continue
            if entry in allow:
                plan.skipped.append(f"{kind} {entry}: you explicitly allow this; kept your rule")
            elif kind == "ask" and entry in perms.get("deny", []):
                plan.skipped.append(f"ask {entry}: already denied (stricter)")
            else:
                current = [*current, entry]
                plan.added.setdefault(kind, []).append(entry)
        if kind in plan.added:
            perms[kind] = current


def _merge_opencode(sidecar: dict[str, Any], config: dict[str, Any], plan: MergePlan) -> None:
    permission = config.setdefault("permission", {})
    if not isinstance(permission, dict):
        plan.skipped.append("permission: existing value is a blanket setting; left alone")
        return
    for key, wanted in sidecar.get("permission", {}).items():
        have = permission.get(key)
        if have is None:
            permission[key] = copy.deepcopy(wanted)
            plan.added[key] = copy.deepcopy(wanted)
        elif isinstance(wanted, dict) and isinstance(have, dict):
            for pattern, effect in wanted.items():
                if pattern not in have:
                    have[pattern] = effect
                    plan.added.setdefault(key, {})[pattern] = effect
                elif have[pattern] != effect:
                    plan.skipped.append(f"{key} '{pattern}': you set {have[pattern]}; kept yours")
        else:
            plan.skipped.append(f"{key}: you already set a value; kept yours")


def plan_merge(sidecar_text: str, framework: str, config_path: Path) -> MergePlan:
    plan = MergePlan(framework=framework, config_path=config_path)
    try:
        sidecar = json.loads(sidecar_text)
    except json.JSONDecodeError:
        plan.error = "The pack's permission sidecar is not valid JSON."
        return plan
    config, error = _load_strict(config_path)
    if config is None:
        plan.error = error
        return plan
    merged = copy.deepcopy(config)
    if framework == "claude-code":
        _merge_claude(sidecar, merged, plan)
    else:
        _merge_opencode(sidecar, merged, plan)
    if plan.error is None and plan.added:
        plan.merged = merged
    return plan


def record_path(base: Path, framework: str) -> Path:
    return base / RECORD_DIR / f"{framework}.permissions.json"


def apply_plan(plan: MergePlan, base: Path) -> None:
    """Write the merged config and record exactly what was added."""
    if not plan.has_changes or plan.merged is None:
        return
    path = plan.config_path
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = path.with_name(path.name + ".myace-bak")
    if path.exists() and not backup.exists():
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.write_text(json.dumps(plan.merged, indent=2) + "\n", encoding="utf-8")

    record = record_path(base, plan.framework)
    record.parent.mkdir(parents=True, exist_ok=True)
    previous: dict[str, Any] = {}
    if record.exists():
        try:
            previous = json.loads(record.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = {}
    entries = previous.get("added", {}) if previous.get("config") == str(path) else {}
    for key, value in plan.added.items():
        if isinstance(value, list):
            entries[key] = [*entries.get(key, []), *value]
        elif isinstance(value, dict) and isinstance(entries.get(key), dict):
            entries[key] = {**entries[key], **value}
        else:
            entries[key] = value
    record.write_text(
        json.dumps({"config": str(path), "added": entries}, indent=2) + "\n", encoding="utf-8"
    )


def remove_applied(base: Path, framework: str) -> list[str]:
    """Take back exactly what `apply_plan` added; leave everything else alone."""
    record = record_path(base, framework)
    if not record.exists():
        return []
    data = json.loads(record.read_text(encoding="utf-8"))
    path = Path(data["config"])
    config, error = _load_strict(path)
    if config is None:
        return [error or "config unreadable"]
    removed: list[str] = []
    added: dict[str, Any] = data.get("added", {})
    if framework == "claude-code":
        perms = config.get("permissions", {})
        for kind, entries in added.items():
            keep = [e for e in perms.get(kind, []) if e not in entries]
            removed += [f"{kind} {e}" for e in perms.get(kind, []) if e in entries]
            if keep:
                perms[kind] = keep
            else:
                perms.pop(kind, None)
        if not perms:
            config.pop("permissions", None)
    else:
        permission = config.get("permission", {})
        for key, value in added.items():
            have = permission.get(key)
            if isinstance(value, dict) and isinstance(have, dict):
                for pattern in value:
                    if have.get(pattern) == value[pattern]:
                        del have[pattern]
                        removed.append(f"{key} {pattern}")
                if not have:
                    permission.pop(key, None)
            elif have == value:
                permission.pop(key, None)
                removed.append(key)
        if not permission:
            config.pop("permission", None)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    record.unlink()
    return removed
