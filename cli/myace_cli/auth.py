"""CLI authentication — token storage, credential management, and validation."""

import json
from pathlib import Path
from urllib.parse import urlparse

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

    @staticmethod
    def validate_server_url(server: str) -> str | None:
        """Validate a server URL's format and scheme.

        Returns None if valid, or an error message string if invalid.
        """
        parsed = urlparse(server)
        if not parsed.scheme:
            return "Server URL must include a scheme (http:// or https://)."
        if parsed.scheme not in ("http", "https"):
            return (
                f"Unsupported URL scheme '{parsed.scheme}' — "
                "use http:// or https://."
            )
        if not parsed.netloc:
            return "Server URL must include a hostname."
        return None

    @staticmethod
    def validate_token_format(token: str) -> str | None:
        """Validate basic token format.

        Returns None if valid, or an error message string if invalid.
        """
        if len(token) < 8:
            return (
                "Token appears too short (minimum 8 characters)."
            )
        return None

    def validate_credentials(self, server: str, token: str) -> str | None:
        """Validate credentials by calling the server's profiles endpoint.

        Performs URL format validation, token format validation, and a
        live HTTP check against the server. Redirects are not followed
        to prevent token leakage to third-party hosts.

        Args:
            server: MyACE server URL.
            token: API token to validate.

        Returns:
            None if valid, or an error message string if validation failed.
        """
        # Static validation first (no network)
        url_error = self.validate_server_url(server)
        if url_error:
            return url_error

        token_error = self.validate_token_format(token)
        if token_error:
            return token_error

        # Live HTTP validation
        url = f"{server.rstrip('/')}/api/v1/profiles"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            # Disable redirects to prevent token leakage to third-party hosts
            # in case the server responds with a 302 to an attacker URL.
            with httpx.Client(timeout=15.0, follow_redirects=False) as client:
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
