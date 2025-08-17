#!/usr/bin/env python3
"""
Initialize test database with proper schema creation.
This script creates the database schema directly from models,
bypassing potential migration issues.
"""

import asyncio
import os
import sys

# Ensure the app directory is in the Python path
sys.path.insert(0, "/app")

from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.logging import logger  # noqa: E402
from app.models.base import BaseModel  # noqa: E402


async def init_test_database():
    """Initialize the test database with proper schema."""

    # Database URL for test environment (ensure asyncpg driver)
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://test:test@postgres-test:5432/devpocket_test",
    )

    # Ensure we're using asyncpg driver
    if "postgresql://" in database_url and "postgresql+asyncpg://" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    logger.info(f"Initializing test database: {database_url}")

    try:
        # Create async engine
        engine = create_async_engine(
            database_url,
            echo=False,
            future=True,
        )

        # Create all tables from models
        async with engine.begin() as conn:
            # Drop all tables first with CASCADE (clean slate)
            logger.info("Dropping all existing tables with CASCADE...")

            # Drop tables manually to handle dependencies
            await conn.execute(text("DROP SCHEMA public CASCADE;"))
            await conn.execute(text("CREATE SCHEMA public;"))
            await conn.execute(text("GRANT ALL ON SCHEMA public TO test;"))

            # Create all tables from models
            logger.info("Creating all tables from models...")
            await conn.run_sync(BaseModel.metadata.create_all)

        # Verify tables were created
        async with engine.begin() as conn:
            # Get list of tables
            result = await conn.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """
                )
            )
            tables = [row[0] for row in result.fetchall()]

            logger.info(f"Created tables: {', '.join(tables)}")

            # Verify we have the expected core tables
            expected_tables = [
                "users",
                "ssh_profiles",
                "ssh_keys",
                "user_settings",
                "sessions",
            ]
            missing_tables = set(expected_tables) - set(tables)

            if missing_tables:
                logger.warning(f"Missing expected tables: {missing_tables}")
            else:
                logger.info("All expected core tables created successfully")

        await engine.dispose()
        logger.info("✅ Test database initialization completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to initialize test database: {e}")
        return False


if __name__ == "__main__":
    from sqlalchemy import text

    # Run the initialization
    success = asyncio.run(init_test_database())
    sys.exit(0 if success else 1)
