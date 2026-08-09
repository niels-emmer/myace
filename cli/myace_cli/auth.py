"""CLI authentication — token storage, credential management, and validation."""

import json
from pathlib import Path

import httpx


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

    def load_credentials(self) -> dict[str, str] | None:
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

    def validate_credentials(self, server: str, token: str) -> str | None:
        """Validate credentials by calling the server's profiles endpoint.

        Args:
            server: MyACE server URL.
            token: API token to validate.

        Returns:
            None if valid, or an error message string if validation failed.
        """
        url = f"{server.rstrip('/')}/api/v1/profiles"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(url, headers=headers)
                if response.status_code == 200:
                    return None
                if response.status_code == 401:
                    return "Token rejected by server (401 Unauthorized)."
                return (
                    f"Server returned unexpected status {response.status_code}."
                )
        except httpx.ConnectError:
            return (
                f"Could not connect to {server}.\n"
                "  Check that the URL is correct and the server is running."
            )
        except httpx.TimeoutException:
            return (
                f"Connection to {server} timed out.\n"
                "  Check your network connection and try again."
            )
        except Exception as e:
            return f"Connection failed: {e}"
