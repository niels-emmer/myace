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
    def translate(self, artifacts: list[CanonicalArtifact]) -> dict[str, str]:
        """
        Translate canonical artifacts into target-specific files.

        Args:
            artifacts: List of CanonicalArtifact objects to translate.

        Returns:
            Dict mapping filenames to file contents for the target framework.
        """
        ...
