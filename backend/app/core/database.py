"""Database engine and session management."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel

from app.core.config import settings

engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the async database engine."""
    global engine
    if engine is None:
        engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            future=True,
        )
    return engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory."""
    global async_session_factory
    if async_session_factory is None:
        async_session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return async_session_factory


async def get_session() -> AsyncSession:  # type: ignore[misc]
    """Dependency that provides an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables on startup (development only)."""
    from app.models import (  # noqa: F401 — ensure models are registered
        artifact,
        collection,
        doc_cache,
        profile,
        token,
        user,
    )

    async_engine = get_engine()
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
