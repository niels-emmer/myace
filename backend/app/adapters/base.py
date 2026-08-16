"""Base adapter interface for target framework translation."""

from abc import ABC, abstractmethod

from app.models.artifact import CanonicalArtifact


class BaseAdapter(ABC):
    """Abstract base class for all target adapters."""

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
