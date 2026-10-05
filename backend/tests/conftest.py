"""Test fixtures and configuration."""

from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

import app.models  # noqa: F401  populate SQLModel.metadata with every table
from app.core.database import get_session
from app.core.ratelimit import auth_limiter
from app.main import app as fastapi_app

# In-memory SQLite, single shared connection for the engine's lifetime so every
# session (and the API request that spawns it) sees the same tables/rows.
TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest.fixture(autouse=True)
def _disable_auth_rate_limit() -> Generator[None, None, None]:
    """Most tests log in/register many times from one fake client IP, which
    would trip the per-IP auth limits. Tests that exercise the limiter turn it
    back on themselves (see tests/test_auth_hardening.py)."""
    auth_limiter.enabled = False
    yield
    auth_limiter.reset()
    auth_limiter.enabled = True


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Spin up an isolated in-memory SQLite DB per test and point the app at it."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_session] = _override_get_session

    async with factory() as session:
        yield session

    fastapi_app.dependency_overrides.pop(get_session, None)
    await engine.dispose()


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client wired to the isolated test database."""
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
