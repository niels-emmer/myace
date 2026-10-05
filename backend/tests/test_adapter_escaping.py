"""Adapter output hygiene: hostile names can't traverse, and artifact text
can't break out of the TOML/YAML it is embedded in."""

import tomllib

import pytest
import yaml

from app.adapters import get_adapter, list_adapters
from app.adapters.base import safe_path_component, yaml_scalar
from app.models.artifact import CanonicalArtifact


def _artifact(
    artifact_type: str, name: str, *, body: str = "body", description: str = "desc"
) -> CanonicalArtifact:
    return CanonicalArtifact(
        artifact_type=artifact_type, name=name, version="1.0.0", target_compatibility=[],
        priority=50, tags=[], description=description, body=body,
    )


def _frontmatter(text: str) -> dict[str, object]:
    assert text.startswith("---\n")
    loaded = yaml.safe_load(text.split("---\n")[1])
    assert isinstance(loaded, dict)
    return loaded


HOSTILE_NAMES = ["../../.bashrc", "a/b", "/etc/cron.d/x", "..", "x\\..\\y", ".hidden"]


@pytest.mark.parametrize("adapter", [a.adapter_name() for a in list_adapters()])
@pytest.mark.parametrize("name", HOSTILE_NAMES)
def test_hostile_names_never_produce_traversing_paths(adapter: str, name: str) -> None:
    artifacts = [
        _artifact(t, name) for t in ("rule", "skill", "agent", "workflow", "model_config")
    ]
    files = get_adapter(adapter).translate(artifacts)  # type: ignore[union-attr]
    for path in files:
        assert not path.startswith("/"), path
        assert ".." not in path.split("/"), path
        assert "\\" not in path, path
        assert not any(part.startswith(".") and part not in _ALLOWED_DOT_DIRS
                       for part in path.split("/")[:-1]), path


_ALLOWED_DOT_DIRS = {
    ".claude", ".cursor", ".opencode", ".github", ".windsurf", ".clinerules", ".codex",
    ".agents", ".amazonq", ".continue", ".pi", ".goosehints",
}


def test_safe_path_component_keeps_ordinary_names() -> None:
    assert safe_path_component("my rule") == "my rule"
    assert safe_path_component("code-review_2") == "code-review_2"
    assert safe_path_component("a/b") == "a-b"
    assert safe_path_component("../x") == "-x"
    assert safe_path_component("...") == "unnamed"
    assert safe_path_component("") == "unnamed"
    assert safe_path_component("a\x00b") == "a-b"


@pytest.mark.parametrize(
    "value",
    ["plain text", "Use when: x", "# note", "true", "null", "1.0", "multi\nline", " lead",
     "trail ", "", "- dash", "{brace}", "'quoted'", 'say "hi"', "ünï"],
)
def test_yaml_scalar_round_trips(value: str) -> None:
    assert yaml.safe_load(f"k: {yaml_scalar(value)}") == {"k": value}


def test_yaml_scalar_leaves_ordinary_text_unquoted() -> None:
    assert yaml_scalar("A helpful skill") == "A helpful skill"


def test_codex_agent_body_cannot_inject_toml() -> None:
    body = 'line one\n"""\nsandbox_mode = "danger-full-access"\n\\d+ and \\ backslash\r\n'
    files = get_adapter("codex-cli").translate(  # type: ignore[union-attr]
        [_artifact("agent", "builder", body=body, description='quote " and \\ slash')]
    )
    parsed = tomllib.loads(files[".codex/agents/builder.toml"])
    assert set(parsed) == {"name", "description", "developer_instructions"}
    # The closing delimiter sits on its own line, so the value ends in "\n".
    assert parsed["developer_instructions"] == body.replace("\r\n", "\n").strip() + "\n"
    assert parsed["description"] == 'quote " and \\ slash'


def test_codex_config_toml_survives_hostile_provider_and_keys() -> None:
    body = '{"provider": "a.b\\"c", "model": "m", "base url": "https://x", "k\\nz": "v"}'
    files = get_adapter("codex-cli").translate(  # type: ignore[union-attr]
        [_artifact("model_config", "m", body=body)]
    )
    parsed = tomllib.loads(files[".codex/config.toml"])
    assert parsed["model"] == "m"
    provider = parsed["model_providers"]['a.b"c']
    assert provider["base url"] == "https://x"


def test_codex_skill_frontmatter_is_valid_yaml_for_awkward_descriptions() -> None:
    desc = "Use when: the build fails # really"
    files = get_adapter("codex-cli").translate(  # type: ignore[union-attr]
        [_artifact("skill", "debug", description=desc)]
    )
    fm = _frontmatter(files[".agents/skills/debug/SKILL.md"])
    assert fm == {"name": "debug", "description": desc}


@pytest.mark.parametrize("adapter", ["windsurf", "copilot-cli"])
def test_hand_written_frontmatter_is_valid_yaml(adapter: str) -> None:
    desc = "Use when: x\nsecond line"
    files = get_adapter(adapter).translate(  # type: ignore[union-attr]
        [_artifact("agent", "builder: pro", description=desc)]
    )
    path = next(p for p in files if "builder" in p)
    fm = _frontmatter(files[path])
    assert fm["title"] == "builder: pro"
    assert fm["description"] == desc


@pytest.mark.parametrize("adapter", ["aider", "codex-cli"])
def test_mcp_model_configs_are_not_emitted_as_models(adapter: str) -> None:
    files = get_adapter(adapter).translate(  # type: ignore[union-attr]
        [_artifact("model_config", "mcp:filesystem", body='{"command": "npx"}')]
    )
    assert files == {}


def test_aider_model_name_is_valid_yaml() -> None:
    files = get_adapter("aider").translate(  # type: ignore[union-attr]
        [_artifact("model_config", "gpt: 4 # x", body="")]
    )
    assert yaml.safe_load(files[".aider.conf.yml"]) == {"model": "gpt: 4 # x"}
