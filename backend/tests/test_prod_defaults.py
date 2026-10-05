"""SQL logging never leaks bound parameters; APP_ENV=development on a real
deployment is detectable (AGENTS.md rules 10, 27)."""

import pytest

from app.core import database
from app.core.config import settings
from app.main import DEFAULT_SECRET_KEY, looks_like_real_deployment


@pytest.fixture
def fresh_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(database, "engine", None)
    monkeypatch.setattr(settings, "database_url", "sqlite+aiosqlite://")


def test_debug_true_does_not_enable_sql_echo(
    fresh_engine: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "debug", True)
    monkeypatch.setattr(settings, "sql_echo", False)
    assert database.get_engine().echo is False


def test_bound_parameters_are_hidden_even_with_sql_echo(
    fresh_engine: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "sql_echo", True)
    engine = database.get_engine()
    assert engine.echo is True
    assert engine.sync_engine.hide_parameters is True


@pytest.mark.parametrize(
    ("secret", "hosts", "cors", "expected"),
    [
        (DEFAULT_SECRET_KEY, "", "https://myace.localhost", False),
        (DEFAULT_SECRET_KEY, "", "http://localhost:5173,http://127.0.0.1:5173", False),
        ("a-real-secret", "", "https://myace.localhost", True),
        (DEFAULT_SECRET_KEY, "myace.example.com", "https://myace.localhost", True),
        (DEFAULT_SECRET_KEY, "", "https://myace.example.com", True),
    ],
)
def test_looks_like_real_deployment(
    monkeypatch: pytest.MonkeyPatch, secret: str, hosts: str, cors: str, expected: bool
) -> None:
    monkeypatch.setattr(settings, "app_secret_key", secret)
    monkeypatch.setattr(settings, "trusted_hosts", hosts)
    monkeypatch.setattr(settings, "cors_origins", cors)
    assert looks_like_real_deployment() is expected
