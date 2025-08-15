#!/usr/bin/env python3
"""
Database utilities for DevPocket API.
"""

import asyncio
import asyncpg
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Load environment variables from specified file (default: .env)
env_file = os.getenv('ENV_FILE', '.env')
env_path = os.path.join(project_root, env_file)
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
    print(f"Loaded environment from: {env_path}")
else:
    print(f"Warning: Environment file not found: {env_path}")

from app.core.config import settings
from app.core.logging import logger


async def create_database():
    """Create the database if it doesn't exist."""
    try:
        # Connect to default postgres database first
        default_db_url = settings.database_url.replace(
            f"/{settings.database_name}",
            "/postgres"
        )
        
        conn = await asyncpg.connect(default_db_url)
        
        # Check if database exists
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            settings.database_name
        )
        
        if not db_exists:
            await conn.execute(f'CREATE DATABASE "{settings.database_name}"')
            logger.info(f"Created database: {settings.database_name}")
        else:
            logger.info(f"Database already exists: {settings.database_name}")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        return False


async def drop_database():
    """Drop the database."""
    try:
        # Connect to default postgres database first
        default_db_url = settings.database_url.replace(
            f"/{settings.database_name}",
            "/postgres"
        )
        
        conn = await asyncpg.connect(default_db_url)
        
        # Terminate all connections to the database
        await conn.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{settings.database_name}'
            AND pid <> pg_backend_pid()
        """)
        
        # Drop the database
        await conn.execute(f'DROP DATABASE IF EXISTS "{settings.database_name}"')
        logger.info(f"Dropped database: {settings.database_name}")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to drop database: {e}")
        return False


async def test_database_connection():
    """Test database connection."""
    try:
        conn = await asyncpg.connect(settings.database_url)
        result = await conn.fetchval("SELECT version()")
        logger.info(f"Database connection successful. PostgreSQL version: {result}")
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


async def init_database():
    """Initialize the database with tables."""
    try:
        from app.db.database import init_database
        await init_database()
        logger.info("Database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


async def check_database_health():
    """Check database health and connection."""
    try:
        conn = await asyncpg.connect(settings.database_url)
        
        # Check basic connection
        await conn.fetchval("SELECT 1")
        
        # Check table existence
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        table_names = [row['table_name'] for row in tables]
        
        logger.info(f"Database health check passed. Tables: {table_names}")
        await conn.close()
        
        return {
            "status": "healthy",
            "tables": table_names,
            "table_count": len(table_names)
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def reset_database():
    """Reset the database by dropping and recreating it."""
    logger.info("Resetting database...")
    
    if await drop_database():
        if await create_database():
            if await init_database():
                logger.info("Database reset completed successfully")
                return True
    
    logger.error("Database reset failed")
    return False


async def main():
    """Main entry point for database utilities."""
    if len(sys.argv) < 2:
        print("""
Database Utilities for DevPocket API

Usage: python scripts/db_utils.py <command>

Commands:
  create     Create the database
  drop       Drop the database
  init       Initialize database tables
  test       Test database connection
  health     Check database health
  reset      Reset database (drop, create, init)

Examples:
  python scripts/db_utils.py create
  python scripts/db_utils.py init
  python scripts/db_utils.py health
""")
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "create":
        success = await create_database()
    elif command == "drop":
        success = await drop_database()
    elif command == "init":
        success = await init_database()
    elif command == "test":
        success = await test_database_connection()
    elif command == "health":
        result = await check_database_health()
        success = result["status"] == "healthy"
        if success:
            print(f"✅ Database health: {result}")
        else:
            print(f"❌ Database health: {result}")
    elif command == "reset":
        success = await reset_database()
    else:
        print(f"❌ Unknown command: {command}")
        return 1
    
    if success:
        print(f"✅ Command '{command}' completed successfully")
        return 0
    else:
        print(f"❌ Command '{command}' failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))