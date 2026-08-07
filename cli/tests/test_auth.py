"""Tests for CLI auth module."""

import json
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
