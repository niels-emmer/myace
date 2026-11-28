"""Runs the real `opencode` binary on our output — skipped where it isn't installed.

Unit tests prove we write what we *intend*; this proves OpenCode reads it as we
intend (v1-style `permission` frontmatter and config are translated and enforced
by OpenCode 2.x, ADR-0019). Isolated HOME so a developer's own config can't
leak in.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from app.adapters import get_adapter
from app.adapters.base import translate_artifacts
from app.models.artifact import CanonicalArtifact
from app.services.seed_collections import _scan_seeded_collection

REPO = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(shutil.which("opencode") is None, reason="opencode not installed")


def _resolved_agents(project: Path, home: Path) -> dict[str, list[tuple[str, str, str]]]:
    env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
           "XDG_DATA_HOME": str(home / ".local/share")}
    out = subprocess.run(
        ["opencode", "debug", "agents", "--standalone"],
        cwd=project, env=env, capture_output=True, text=True, timeout=120,
    ).stdout
    agents = json.loads(out[out.index("["):])
    return {
        a["id"]: [(p["action"], p["resource"], p["effect"]) for p in a["permissions"]]
        for a in agents
    }


def test_opencode_enforces_our_agent_permissions_and_sidecar(tmp_path: Path) -> None:
    scanned = _scan_seeded_collection(REPO / "collections/base/software-engineer")
    artifacts = [
        CanonicalArtifact(
            **{k: a.get(k) for k in (
                "artifact_type", "name", "version", "priority", "tags",
                "description", "body", "permissions",
            )},
            target_compatibility=[],
        )
        for a in scanned
    ]
    project = tmp_path / "proj"
    for rel, content in translate_artifacts(get_adapter("opencode"), artifacts).items():  # type: ignore[arg-type]
        (project / rel).parent.mkdir(parents=True, exist_ok=True)
        (project / rel).write_text(content)
    # What `myace pull --apply-permissions` writes for a user with no config.
    sidecar = json.loads((project / ".opencode/myace.permissions.json").read_text())
    (project / "opencode.json").write_text(json.dumps(sidecar))

    agents = _resolved_agents(project, tmp_path / "home")
    assert ("edit", "*", "deny") in agents["code-reviewer"]
    assert ("edit", "*", "deny") not in agents["builder"]
    assert {("edit", "*", "deny"), ("shell", "*", "deny")} <= set(agents["orchestrator"])
    assert ("shell", "git push *", "ask") in agents["builder"]  # global rule, v1 config key
