"""The CLI must report the version its package metadata declares."""

import json
from importlib.metadata import version

from myace_cli import __version__
from myace_cli.auth import AuthManager


def test_version_matches_package_metadata():
    assert __version__ == version("myace-cli")


def test_stored_credentials_record_the_package_version(tmp_path):
    auth = AuthManager()
    auth.config_dir = tmp_path
    auth.credentials_path = tmp_path / "credentials.json"

    auth.store_credentials("https://api.example.com", "test-token")

    # load_credentials intentionally exposes only server/token; the stored
    # client version is part of the on-disk payload.
    stored = json.loads(auth.credentials_path.read_text())
    assert stored["version"] == __version__
    assert stored["version"] != "0.1.0"
