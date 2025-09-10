"""Database connection and session management."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import event, pool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class DatabaseManager:
    """Database connection and session manager."""
    
    def __init__(self):
        """Initialize database manager."""
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    
    def create_engine(self) -> AsyncEngine:
        """Create database engine."""
        if self._engine is not None:
            return self._engine
        
        logger.info("Creating database engine")
        
        # Engine configuration
        engine_kwargs = {
            "url": settings.database_url,
            "echo": settings.debug,
            "echo_pool": settings.debug,
            "pool_pre_ping": True,
            "pool_recycle": 3600,  # 1 hour
            "pool_size": 10,
            "max_overflow": 20,
            # Async engines use AsyncAdaptedQueuePool by default, no need to specify poolclass
        }
        
        self._engine = create_async_engine(**engine_kwargs)
        
        # Add event listeners
        self._setup_engine_events()
        
        return self._engine
    
    def _setup_engine_events(self) -> None:
        """Setup engine event listeners."""
        if self._engine is None:
            return
        
        @event.listens_for(self._engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas if using SQLite."""
            if "sqlite" in settings.database_url:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=1000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.close()
        
        @event.listens_for(self._engine.sync_engine, "connect")
        def set_postgresql_settings(dbapi_connection, connection_record):
            """Set PostgreSQL settings."""
            if "postgresql" in settings.database_url:
                with dbapi_connection.cursor() as cursor:
                    # Set timezone to UTC
                    cursor.execute("SET timezone TO 'UTC'")
                    # Set statement timeout (30 seconds)
                    cursor.execute("SET statement_timeout = '30s'")
    
    def create_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Create session factory."""
        if self._session_factory is not None:
            return self._session_factory
        
        engine = self.create_engine()
        
        self._session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )
        
        return self._session_factory
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session context manager."""
        session_factory = self.create_session_factory()
        
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def create_tables(self) -> None:
        """Create all database tables."""
        engine = self.create_engine()
        
        logger.info("Creating database tables")
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
    
    async def drop_tables(self) -> None:
        """Drop all database tables."""
        engine = self.create_engine()
        
        logger.warning("Dropping all database tables")
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.info("Database tables dropped successfully")
    
    async def close(self) -> None:
        """Close database connections."""
        if self._engine is not None:
            logger.info("Closing database engine")
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
    
    @property
    def engine(self) -> AsyncEngine:
        """Get database engine."""
        return self.create_engine()
    
    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get session factory."""
        return self.create_session_factory()


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    async with db_manager.get_session() as session:
        yield session


async def init_database() -> None:
    """Initialize database (create tables)."""
    await db_manager.create_tables()


async def close_database() -> None:
    """Close database connections."""
    await db_manager.close()


# Health check function
async def check_database_health() -> bool:
    """Check database connectivity."""
    try:
        async with db_manager.get_session() as session:
            # Simple query to test connection
            result = await session.execute("SELECT 1")
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False