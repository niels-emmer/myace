"""Profile sync engine — fetch, validate, and write compiled profiles."""


import httpx


class SyncEngine:
    """Fetches compiled profiles from the MyACE API and writes files locally."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def pull_profile(
        self,
        server: str,
        token: str,
        profile_name: str,
        target: str,
    ) -> dict | None:
        """
        Fetch a compiled profile from the server.

        Args:
            server: MyACE API server URL (e.g., https://api.myace.localhost)
            token: API token for authentication
            profile_name: Profile name or ID
            target: Target framework (e.g., opencode, claude-code, cursor)

        Returns:
            Dict with 'files' key containing {filename: content} mappings,
            or None if the request fails.
        """
        # First, resolve profile name to ID if needed
        profile_id = self._resolve_profile_id(server, token, profile_name)
        if not profile_id:
            return None

        # Compile the profile
        url = f"{server}/api/v1/profiles/compile"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "profile_id": profile_id,
            "target": target,
            "include_disabled": False,
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    def list_profiles(self, server: str, token: str) -> list[dict]:
        """List available profiles from the server."""
        url = f"{server}/api/v1/profiles"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
            return []

    def _resolve_profile_id(
        self,
        server: str,
        token: str,
        profile_name: str,
    ) -> str | None:
        """
        Resolve a profile name or ID to a UUID.
        If the input looks like a UUID, return it directly.
        Otherwise, search profiles by name.
        """
        import uuid

        # Check if it's already a UUID
        try:
            uuid.UUID(profile_name)
            return profile_name
        except ValueError:
            pass

        # Search by name
        profiles = self.list_profiles(server, token)
        for profile in profiles:
            if profile.get("name") == profile_name:
                return str(profile["id"])

        # Try partial match
        for profile in profiles:
            if profile_name.lower() in profile.get("name", "").lower():
                return str(profile["id"])

        return None
