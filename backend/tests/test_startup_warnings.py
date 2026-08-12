"""Tests for the startup warnings in app.main.lifespan that flag unsafe
config left at its default outside local development."""

import logging

import pytest

from app.main import app, lifespan


@pytest.mark.asyncio
async def test_raises_on_default_secret_key_outside_dev(monkeypatch):
    monkeypatch.setattr("app.main.settings.app_env", "production")
    monkeypatch.setattr("app.main.settings.app_secret_key", "change-me-to-a-random-64-char-string")
    monkeypatch.setattr("app.main.settings.debug", False)
    monkeypatch.setattr("app.main.settings.admin_bootstrap_enabled", False)

    with pytest.raises(RuntimeError, match="APP_SECRET_KEY"):
        async with lifespan(app):
            pass


@pytest.mark.asyncio
async def test_no_secret_key_warning_in_development(monkeypatch, caplog):
    async def _no_op_init_db():
        return None

    monkeypatch.setattr("app.main.init_db", _no_op_init_db)
    monkeypatch.setattr("app.main.settings.app_env", "development")
    monkeypatch.setattr("app.main.settings.app_secret_key", "change-me-to-a-random-64-char-string")
    monkeypatch.setattr("app.main.settings.debug", True)
    monkeypatch.setattr("app.main.settings.admin_bootstrap_enabled", True)

    with caplog.at_level(logging.WARNING, logger="myace"):
        async with lifespan(app):
            pass

    assert not any("APP_SECRET_KEY" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_warns_on_debug_true_outside_dev(monkeypatch, caplog):
    monkeypatch.setattr("app.main.settings.app_env", "production")
    monkeypatch.setattr("app.main.settings.app_secret_key", "a-real-random-secret")
    monkeypatch.setattr("app.main.settings.debug", True)
    monkeypatch.setattr("app.main.settings.admin_bootstrap_enabled", False)

    with caplog.at_level(logging.WARNING, logger="myace"):
        async with lifespan(app):
            pass

    assert any("DEBUG" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_warns_on_admin_bootstrap_enabled_outside_dev(monkeypatch, caplog):
    monkeypatch.setattr("app.main.settings.app_env", "production")
    monkeypatch.setattr("app.main.settings.app_secret_key", "a-real-random-secret")
    monkeypatch.setattr("app.main.settings.debug", False)
    monkeypatch.setattr("app.main.settings.admin_bootstrap_enabled", True)

    with caplog.at_level(logging.WARNING, logger="myace"):
        async with lifespan(app):
            pass

    assert any("ADMIN_BOOTSTRAP_ENABLED" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_warns_on_missing_settings_encryption_key(monkeypatch, caplog):
    monkeypatch.setattr("app.main.settings.app_env", "production")
    monkeypatch.setattr("app.main.settings.app_secret_key", "a-real-random-secret")
    monkeypatch.setattr("app.main.settings.debug", False)
    monkeypatch.setattr("app.main.settings.admin_bootstrap_enabled", False)
    monkeypatch.setattr("app.main.settings.settings_encryption_key", "")

    with caplog.at_level(logging.WARNING, logger="myace"):
        async with lifespan(app):
            pass

    assert any("SETTINGS_ENCRYPTION_KEY" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_no_warnings_when_properly_configured(monkeypatch, caplog):
    monkeypatch.setattr("app.main.settings.app_env", "production")
    monkeypatch.setattr("app.main.settings.app_secret_key", "a-real-random-secret")
    monkeypatch.setattr("app.main.settings.debug", False)
    monkeypatch.setattr("app.main.settings.admin_bootstrap_enabled", False)
    monkeypatch.setattr("app.main.settings.settings_encryption_key", "a-real-fernet-key")

    with caplog.at_level(logging.WARNING, logger="myace"):
        async with lifespan(app):
            pass

    assert caplog.records == []
