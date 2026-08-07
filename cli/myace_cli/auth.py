"""CLI authentication — token storage and credential management."""

import json
from pathlib import Path
from typing import Optional


class AuthManager:
    """Manages CLI credentials stored in ~/.myace/credentials.json."""

    def __init__(self):
        self.config_dir = Path.home() / ".myace"
        self.credentials_path = self.config_dir / "credentials.json"

    def store_credentials(self, server: str, token: str) -> None:
        """Store server URL and API token to disk."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.credentials_path.write_text(
            json.dumps(
                {
                    "server": server.rstrip("/"),
                    "token": token,
                    "version": "0.1.0",
                },
                indent=2,
            )
        )
        # Restrict permissions to owner only
        self.credentials_path.chmod(0o600)

    def load_credentials(self) -> Optional[dict[str, str]]:
        """Load stored credentials from disk."""
        if not self.credentials_path.exists():
            return None

        try:
            data = json.loads(self.credentials_path.read_text())
            return {
                "server": data["server"],
                "token": data["token"],
            }
        except (json.JSONDecodeError, KeyError):
            return None

    def clear_credentials(self) -> None:
        """Remove stored credentials."""
        if self.credentials_path.exists():
            self.credentials_path.unlink()
