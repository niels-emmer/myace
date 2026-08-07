"""Test fixtures and configuration."""

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.main import app
from app.core.database import get_session

# Use SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
