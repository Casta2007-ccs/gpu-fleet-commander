import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Load connection string from environment variable (injected by Flox)
# Uses asyncpg driver to support high-performance asynchronous operations
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/gpu_fleet"
)

# Initialize asynchronous engine
# pool_pre_ping=True: automatically checks and recycles stale connections
# echo=False: set to True to log SQL execution for local debugging
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    future=True
)

# Async session maker factory
AsyncSessionMaker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    """Declarative Base class for all SQL-mapped domain models (SQLAlchemy 2.0+ Style)."""
    pass


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection helper or context manager to get an active DB session.

    Yields:
        AsyncSession: The active transaction session.

    Raises:
        Exception: Rolls back transaction on any runtime database error.
    """
    async with AsyncSessionMaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
