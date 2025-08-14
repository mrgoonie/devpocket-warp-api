"""
Database connection and session management for DevPocket API.
"""

from typing import AsyncGenerator
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
from app.core.logging import logger


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Create async engine
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.app_debug,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class DatabaseManager:
    """Database connection manager."""
    
    def __init__(self):
        self._pool: asyncpg.Pool = None
    
    async def connect(self) -> None:
        """Create database connection pool."""
        try:
            self._pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=10,
                max_size=20,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                setup=self._setup_connection,
            )
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create database connection pool: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("Database connection pool closed")
    
    async def _setup_connection(self, connection: asyncpg.Connection) -> None:
        """Set up database connection with custom types and settings."""
        # Set timezone
        await connection.execute("SET timezone TO 'UTC'")
        
        # Set JSON serialization
        await connection.set_type_codec(
            'json',
            encoder=lambda x: x,
            decoder=lambda x: x,
            schema='pg_catalog'
        )
    
    async def execute_query(self, query: str, *args) -> list:
        """Execute a SELECT query and return results."""
        async with self._pool.acquire() as connection:
            try:
                result = await connection.fetch(query, *args)
                return [dict(record) for record in result]
            except Exception as e:
                logger.error(f"Database query error: {e}")
                raise
    
    async def execute_command(self, query: str, *args) -> str:
        """Execute an INSERT/UPDATE/DELETE command and return status."""
        async with self._pool.acquire() as connection:
            try:
                result = await connection.execute(query, *args)
                return result
            except Exception as e:
                logger.error(f"Database command error: {e}")
                raise
    
    async def execute_transaction(self, queries: list) -> bool:
        """Execute multiple queries in a transaction."""
        async with self._pool.acquire() as connection:
            async with connection.transaction():
                try:
                    for query, args in queries:
                        await connection.execute(query, *args)
                    return True
                except Exception as e:
                    logger.error(f"Database transaction error: {e}")
                    raise
    
    @property
    def pool(self) -> asyncpg.Pool:
        """Get the connection pool."""
        if not self._pool:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._pool


# Global database manager instance
db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_pool() -> asyncpg.Pool:
    """
    Dependency to get database connection pool.
    
    Returns:
        asyncpg.Pool: Database connection pool
    """
    return db_manager.pool


async def create_tables() -> None:
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def drop_tables() -> None:
    """Drop all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("Database tables dropped successfully")


async def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        bool: True if connection is working
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def init_database() -> None:
    """Initialize database with required data."""
    try:
        # Create tables
        await create_tables()
        
        # Add any initial data here if needed
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise