"""Base adapter interface for target framework translation."""

import json
import re
from abc import ABC, abstractmethod

import yaml

from app.models.artifact import CanonicalArtifact


def safe_path_component(name: str) -> str:
    """Make an artifact name safe to use as one path segment in a compiled
    file path.

    Artifact names are user-controlled (and public collections are readable
    by other users), so a name like `../../.bashrc` or `a/b` would otherwise
    become a traversing or unexpectedly nested path in the zip/`myace pull`
    output. Path separators and control characters become `-`, leading dots
    are stripped (no `..`, no hidden files), and an empty result falls back
    to `unnamed`. Ordinary names — including spaces — are unchanged.
    """
    cleaned = re.sub(r"[\x00-\x1f/\\]", "-", name).strip().lstrip(".").strip()
    return cleaned or "unnamed"


def yaml_scalar(value: str) -> str:
    """Render a string as a YAML scalar for a hand-written `key: value` line.

    Plain when that round-trips to the same string (so ordinary names and
    descriptions are emitted unchanged); otherwise a double-quoted JSON
    string, which is valid YAML. Without this, a description like
    `Use when: x`, `# note` or `true`, or one containing a newline, produced
    invalid or differently-typed frontmatter.
    """
    if value and value == value.strip() and "\n" not in value:
        try:
            if yaml.safe_load(f"k: {value}") == {"k": value}:
                return value
        except yaml.YAMLError:
            pass
    return json.dumps(value, ensure_ascii=False)


def restricting_permissions(artifact: CanonicalArtifact) -> dict[str, str]:
    """The `ask`/`deny` entries an agent declares, in declaration order.

    `allow` is accepted in the canonical IR for readability but is never
    compiled: a per-agent `allow` could override a stricter setting the user
    already has, and permissions here are restrict-only by design (ADR-0019).
    """
    if artifact.artifact_type != "agent" or not artifact.permissions:
        return {}
    return {cap: eff for cap, eff in artifact.permissions.items() if eff in ("ask", "deny")}


PERMISSION_POLICY_PREFIX = "permissions:"
_POLICY_CAPABILITIES = ("read", "edit", "execute", "network", "delegate")


def is_permission_policy(artifact: CanonicalArtifact) -> bool:
    """A `model_config` named `permissions:<x>` holds a pack's global
    permission rules (ADR-0019, phase 2). It is filtered out before any
    adapter's `translate()` runs — see `translate_artifacts()` — so no adapter
    has to know to skip it, unlike `mcp:<name>`."""
    return artifact.artifact_type == "model_config" and artifact.name.startswith(
        PERMISSION_POLICY_PREFIX
    )


def policy_rules(policies: list[CanonicalArtifact]) -> list[dict[str, str]]:
    """Validated, de-duplicated `ask`/`deny` rules from policy artifacts.

    Body shape: `{"rules": [{"capability", "effect", "match"?}]}`. Restrict-only
    like agent permissions: `allow` is dropped, `match` is honoured only for
    `execute`, and anything malformed is ignored (the body is user-supplied).
    """
    import json

    seen: set[tuple[str, str, str]] = set()
    rules: list[dict[str, str]] = []
    for policy in policies:
        try:
            raw = json.loads(policy.body).get("rules", [])
        except (ValueError, AttributeError):
            continue
        for item in raw if isinstance(raw, list) else []:
            if not isinstance(item, dict):
                continue
            cap, eff, match = item.get("capability"), item.get("effect"), item.get("match", "")
            if cap not in _POLICY_CAPABILITIES or eff not in ("ask", "deny"):
                continue
            if not isinstance(match, str) or len(match) > 200 or (match and cap != "execute"):
                continue
            key = (cap, eff, match)
            if key not in seen:
                seen.add(key)
                rules.append({"capability": cap, "effect": eff, "match": match})
    return rules


class BaseAdapter(ABC):
    """Abstract base class for all target adapters."""

    def permission_policy_files(self, policies: list[CanonicalArtifact]) -> dict[str, str]:
        """Sidecar file(s) carrying a pack's global permission rules.

        Default: none. Only adapters whose framework has a permissions config
        override this, and they must write a file the framework never loads on
        its own (never `settings.json` / `opencode.json`) — the user, or the
        CLI's tracked merge, applies it (ADR-0019).
        """
        return {}

    def unenforced_permissions(self, artifact: CanonicalArtifact) -> dict[str, str]:
        """Declared restrictions this target cannot express (ADR-0019).

        The default is "all of them": a target with no per-agent permission
        system keeps the prose and the compiler warns. Adapters that do
        enforce override this to return only what they cannot express.
        """
        return restricting_permissions(artifact)

    @abstractmethod
    def adapter_name(self) -> str:
        """Return the unique name of this adapter (e.g., 'claude-code')."""
        ...

    @abstractmethod
    def supported_targets(self) -> list[str]:
        """Return the list of target framework identifiers this adapter supports."""
        ...

    @abstractmethod
    def expected_paths(self) -> list[str]:
        """Return this adapter's conventional local file/directory names.

        Used by the local setup audit (companion-server `/audit` route,
        `cli/myace_cli/local_server.py`) to find where this framework's
        config would live on disk without hardcoding per-target knowledge
        there. Directory entries end with a trailing `/` (e.g.
        `.claude/agents/`); file entries don't (e.g. `CLAUDE.md`). Must
        match what `translate()` actually writes — keep the two in sync
        when either changes. The CLI's companion server hand-maintains a
        mirror of these values (`myace_cli.audit.ADAPTER_EXPECTED_PATHS`)
        since the CLI package doesn't depend on this backend package —
        the same kept-in-sync-by-hand pattern already used for the dual
        scanner implementations (AGENTS.md rule 8).
        """
        ...

    @abstractmethod
    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        """
        Translate canonical artifacts into target-specific files.

        Args:
            artifacts: List of CanonicalArtifact objects to translate.

        Returns:
            Dict mapping filenames to file contents for the target framework.
        """
        ...


def translate_artifacts(adapter: BaseAdapter, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
    """`adapter.translate()` plus permission-policy sidecars.

    The one place policies are split off, so no adapter sees a
    `permissions:*` model_config and none can mis-render it. Both compile
    routes and the public demo go through here.
    """
    policies = [a for a in artifacts if is_permission_policy(a)]
    files = adapter.translate([a for a in artifacts if not is_permission_policy(a)])
    if policies:
        files.update(adapter.permission_policy_files(policies))
    return files
