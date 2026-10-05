"""Tests for CLI auth module."""

from pathlib import Path

from myace_cli.auth import AuthManager


def test_store_and_load_credentials(tmp_path: Path):
    """Test storing and loading credentials."""
    auth = AuthManager()
    auth.config_dir = tmp_path
    auth.credentials_path = tmp_path / "credentials.json"

    auth.store_credentials("https://api.example.com", "test-token-12345")
    assert auth.credentials_path.exists()

    creds = auth.load_credentials()
    assert creds is not None
    assert creds["server"] == "https://api.example.com"
    assert creds["token"] == "test-token-12345"


def test_clear_credentials(tmp_path: Path):
    """Test clearing credentials."""
    auth = AuthManager()
    auth.config_dir = tmp_path
    auth.credentials_path = tmp_path / "credentials.json"

    auth.store_credentials("https://api.example.com", "test-token")
    assert auth.credentials_path.exists()

    auth.clear_credentials()
    assert not auth.credentials_path.exists()


def test_load_credentials_no_file(tmp_path: Path):
    """Test loading when no credentials file exists."""
    auth = AuthManager()
    auth.config_dir = tmp_path
    auth.credentials_path = tmp_path / "credentials.json"

    creds = auth.load_credentials()
    assert creds is None


def test_load_credentials_corrupted(tmp_path: Path):
    """Test loading corrupted credentials file."""
    auth = AuthManager()
    auth.config_dir = tmp_path
    auth.credentials_path = tmp_path / "credentials.json"
    auth.credentials_path.write_text("not-json")

    creds = auth.load_credentials()
    assert creds is None


def test_credentials_file_and_dir_are_owner_only(tmp_path: Path):
    import stat

    auth = AuthManager()
    auth.config_dir = tmp_path / ".myace"
    auth.credentials_path = auth.config_dir / "credentials.json"

    auth.store_credentials("https://api.example.com", "test-token-12345")

    assert stat.S_IMODE(auth.config_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(auth.credentials_path.stat().st_mode) == 0o600


def test_store_credentials_tightens_an_existing_loose_file(tmp_path: Path):
    import stat

    auth = AuthManager()
    auth.config_dir = tmp_path
    auth.credentials_path = tmp_path / "credentials.json"
    auth.credentials_path.write_text("{}")
    auth.credentials_path.chmod(0o644)

    auth.store_credentials("https://api.example.com", "test-token-12345")

    assert stat.S_IMODE(auth.credentials_path.stat().st_mode) == 0o600
    assert auth.load_credentials() is not None
