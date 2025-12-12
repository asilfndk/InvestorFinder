"""
Database configuration and connection management.
Supports SQLite for development and PostgreSQL for production.
"""

import os
from pathlib import Path
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class DatabaseManager:
    """
    Manages database connections and sessions.
    Singleton pattern for application-wide access.
    """

    _instance: "DatabaseManager | None" = None
    _engine: AsyncEngine | None = None
    _session_factory: async_sessionmaker[AsyncSession] | None = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError(
                "Database not initialized. Call initialize() first.")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError(
                "Database not initialized. Call initialize() first.")
        return self._session_factory

    async def initialize(self, database_url: str | None = None) -> None:
        """
        Initialize database connection.

        Args:
            database_url: Database URL. If None, uses settings.
        """
        if self._engine is not None:
            logger.warning("Database already initialized")
            return

        settings = get_settings()
        url = database_url or settings.database_url

        # Ensure data directory exists for SQLite
        if url.startswith("sqlite"):
            # Extract the db file path from URL
            # Format: sqlite+aiosqlite:///./data/investor_finder.db
            db_path = url.split("///")[-1]
            db_dir = Path(db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured database directory exists: {db_dir}")

        # Determine if using SQLite
        is_sqlite = url.startswith("sqlite")

        # Create engine with appropriate settings
        if is_sqlite:
            # SQLite-specific settings
            self._engine = create_async_engine(
                url,
                echo=settings.debug,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            # PostgreSQL settings
            self._engine = create_async_engine(
                url,
                echo=settings.debug,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
            )

        # Create session factory
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        logger.info(
            f"Database initialized: {url.split('@')[-1] if '@' in url else url}")

    async def create_tables(self) -> None:
        """Create all tables defined in models."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

    async def drop_tables(self) -> None:
        """Drop all tables. Use with caution!"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("All database tables dropped")

    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database connections closed")

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


# Global database manager instance
db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async for session in db_manager.get_session():
        yield session


async def init_db(database_url: str | None = None) -> None:
    """Initialize database and create tables."""
    await db_manager.initialize(database_url)
    await db_manager.create_tables()


async def close_db() -> None:
    """Close database connections."""
    await db_manager.close()
