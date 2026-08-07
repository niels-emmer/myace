"""Base adapter interface for CLI-side translation."""

from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    """Abstract base class for CLI-side target adapters."""

    @abstractmethod
    def adapter_name(self) -> str:
        ...

    @abstractmethod
    def supported_targets(self) -> list[str]:
        ...

    @abstractmethod
    def translate(self, artifacts: list[dict]) -> dict[str, str]:
        ...
