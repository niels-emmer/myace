"""Every shipped item's `compatibility` must name every adapter.

`compatibility` is descriptive (AGENTS.md rule 41), but the pack page's "Works
with" row is derived from it, so a list that stops at the adapters that existed
when it was written advertises fewer frameworks than the product compiles to.
"""

import re
from pathlib import Path

import pytest
import yaml

from app.adapters import list_adapters

COLLECTIONS = Path(__file__).resolve().parents[2] / "collections"
FILES = sorted(
    [*COLLECTIONS.glob("*/*/agents/*.md"), *COLLECTIONS.glob("*/*/skills/*/SKILL.md"),
     *COLLECTIONS.glob("*/*/commands/*.md")]
)


def _compat(path: Path) -> list[str] | None:
    match = re.match(r"---\n(.*?)\n---\n", path.read_text(), re.S)
    assert match, f"{path} has no frontmatter"
    data = yaml.safe_load(match.group(1)) or {}
    value = data.get("compatibility")
    return list(value) if value is not None else None


def test_there_are_items_to_check() -> None:
    assert FILES


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(COLLECTIONS)))
def test_item_compatibility_names_every_adapter(path: Path) -> None:
    compat = _compat(path)
    if compat is None:
        pytest.skip("item declares no compatibility (means every framework)")
    missing = [
        adapter.adapter_name()
        for adapter in list_adapters()
        if not ({adapter.adapter_name(), *adapter.supported_targets()} & set(compat))
    ]
    assert not missing, f"{path.name} does not list: {missing}"
