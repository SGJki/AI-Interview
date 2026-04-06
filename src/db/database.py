"""
PostgreSQL Database Manager - Async SQLAlchemy Engine with Connection Pool
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool


class DatabaseManager:
    """
    PostgreSQL database manager with async SQLAlchemy engine.

    Provides:
    - Async engine with connection pooling
    - Session factory for creating async sessions
    - Context manager for session lifecycle

    Example:
        db = DatabaseManager("postgresql+asyncpg://user:pass@localhost/db")
        async with db.get_session() as session:
            result = await session.execute(query)
    """

    def __init__(
        self,
        database_url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo: bool = False,
    ):
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection URL with async driver.
                          Format: postgresql+asyncpg://user:pass@host:port/dbname
            pool_size: Number of connections to maintain in pool
            max_overflow: Max connections beyond pool_size
            pool_timeout: Seconds to wait for connection from pool
            pool_recycle: Recycle connections after N seconds
            echo: Log SQL statements (debug)
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo

        self.engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            poolclass=AsyncAdaptedQueuePool,
            echo=echo,
        )

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get async database session as context manager.

        Yields:
            AsyncSession: SQLAlchemy async session

        Example:
            async with db.get_session() as session:
                await session.execute(query)
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        """Close database engine and all connections."""
        await self.engine.dispose()

    async def create_tables(self) -> None:
        """Create all tables (for testing/setup)."""
        from src.db.models import Base

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all tables (for testing)."""
        from src.db.models import Base

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    def get_engine(self):
        """Get the underlying SQLAlchemy async engine."""
        return self.engine


# Default database manager instance (lazy initialization)
_default_db: DatabaseManager | None = None


def get_database_manager() -> DatabaseManager:
    """Get default database manager instance."""
    global _default_db

    if _default_db is None:
        from src.config import get_database_config

        cfg = get_database_config()
        _default_db = DatabaseManager(cfg.url)

    return _default_db


async def close_database_manager() -> None:
    """Close default database manager."""
    global _default_db

    if _default_db is not None:
        await _default_db.close()
        _default_db = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session as context manager (convenience function).

    Uses the default database manager instance.

    Yields:
        AsyncSession: SQLAlchemy async session

    Example:
        async for session in get_db_session():
            await session.execute(query)
    """
    db = get_database_manager()
    async with db.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
