"""MyACE CLI — Sync agentic coding environment profiles to your local machine."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version

try:
    __version__ = package_version("myace-cli")
except PackageNotFoundError:  # pragma: no cover - metadata absent (source or frozen)
    __version__ = "0.0.0+unknown"
