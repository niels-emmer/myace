"""SQL logging never leaks bound parameters; APP_ENV=development on a real
deployment is detectable; unsafe transport config (wildcard CORS, DEBUG)
fails startup (AGENTS.md rules 10, 27)."""

import pytest

from app.core import database
from app.core.config import settings
from app.main import (
    DEFAULT_SECRET_KEY,
    looks_like_real_deployment,
    validate_cors_origins,
)


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


def test_cors_wildcard_outside_development_refuses_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """L-16: a `*` origin with allow_credentials=True is either rejected by
    the browser or reflects any Origin back with credentials. Outside
    development the app must refuse to start."""
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "cors_origins", "*")
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        validate_cors_origins()


def test_cors_wildcard_mixed_with_a_real_origin_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "cors_origins", "https://myace.example.com,*")
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        validate_cors_origins()


def test_cors_wildcard_is_allowed_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "cors_origins", "*")
    validate_cors_origins()


def test_explicit_cors_origins_pass_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(
        settings, "cors_origins", "https://myace.example.com,https://app.example.com"
    )
    validate_cors_origins()


def test_session_cookie_secure_follows_frontend_scheme(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """L-14: the session cookie's `Secure` flag is derived from
    FRONTEND_BASE_URL's scheme, not from `debug` (which defaults to true and
    used to leave a production deployment issuing a non-Secure cookie)."""
    monkeypatch.setattr(settings, "frontend_base_url", "https://myace.example.com")
    assert settings.session_cookie_secure is True

    monkeypatch.setattr(settings, "frontend_base_url", "http://localhost:5173")
    assert settings.session_cookie_secure is False


def test_session_cookie_secure_does_not_depend_on_debug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "frontend_base_url", "https://myace.example.com")
    monkeypatch.setattr(settings, "debug", True)
    assert settings.session_cookie_secure is True
    monkeypatch.setattr(settings, "debug", False)
    assert settings.session_cookie_secure is True
