"""
Database configuration and session management for KinoStats.
Configures SQLAlchemy 2.0 async engine and sessionmaker using asyncpg.
"""

from collections.abc import AsyncGenerator
import logging
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from src.core.config import settings

logger = logging.getLogger(__name__)


# 1. Base Declarative Class
# In SQLAlchemy 2.0, DeclarativeBase replaces the legacy declarative_base() factory.
# All ORM models inherit from this Base.
class Base(DeclarativeBase):
    """Root declarative class for all KinoStats database models."""
    pass


# 2. AsyncEngine Creation
# The engine maintains the connection pool (QueuePool) to PostgreSQL.
engine: AsyncEngine = create_async_engine(
    settings.async_database_url,
    echo=False,  # Set to True only for debugging raw SQL queries
    pool_size=10,  # Matches standard HikariCP base pool sizing
    max_overflow=20,  # Max additional connections to spin up during spikes
    pool_timeout=30.0,  # Seconds to wait before raising a TimeoutError
    pool_pre_ping=True,  # Emits 'SELECT 1' test query to discard stale/dead sockets
)

# 3. AsyncSession Factory
# expire_on_commit=False is CRITICAL for AsyncIO applications.
# If True, accessing model attributes after `await session.commit()` triggers
# an implicit lazy reload, which raises a MissingGreenlet exception in async environments.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# 4. FastAPI Request Session Dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding a thread-safe AsyncSession per request.
    
    Ensures deterministic connection handling: commits on success,
    rolls back on unhandled exceptions, and unconditionally closes
    the session back to the pool in the finally block.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as exc:
            logger.error("Database transaction rolled back due to error: %s", exc)
            await session.rollback()
            raise
        finally:
            await session.close()