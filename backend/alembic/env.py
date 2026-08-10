"""Alembic migrations environment."""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from alembic import context

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import all models so they are registered
from app.models import (  # noqa: F401
    artifact,
    collection,
    doc_cache,
    profile,
    system_settings,
    token,
    user,
)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Prefer the DATABASE_URL from the environment (set via .env / compose) over
# the hardcoded value in alembic.ini. The ini ships with the dev default
# password, which silently breaks migrations in any deployment that uses a
# real secret (e.g. production). Without this, `alembic upgrade head` fails
# with "password authentication failed" even though the app connects fine.
#
# The app's DATABASE_URL uses the asyncpg driver, but alembic runs
# synchronously and can't drive an async engine (MissingGreenlet). Rewrite
# the URL to the synchronous psycopg2 driver for migrations.
if os.environ.get("DATABASE_URL"):
    url = os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2")
    config.set_main_option("sqlalchemy.url", url)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
