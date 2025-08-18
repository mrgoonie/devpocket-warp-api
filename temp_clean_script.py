#!/usr/bin/env python3
"""
Temporary cleaning script for DevPocket API
"""

import asyncio
import sys
import os
from pathlib import Path

# CRITICAL: Load environment variables FIRST before importing any app modules
from dotenv import load_dotenv
load_dotenv(override=True)

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

async def clean_database(data_types: str, force_clean: bool = False):
    """Clean specific data types from database."""
    
    from app.db.database import AsyncSessionLocal
    from app.core.logging import logger
    from sqlalchemy import text
    
    # Import models
    from app.models.user import User
    from app.models.ssh_profile import SSHProfile, SSHKey
    from app.models.command import Command
    from app.models.session import Session
    from app.models.sync import SyncData
    
    logger.info(f"Starting database cleaning (types: {data_types}, force: {force_clean})")
    
    try:
        async with AsyncSessionLocal() as session:
            
            # Parse data types to clean
            types_to_clean = [t.strip() for t in data_types.split(',')]
            
            # Clean in reverse dependency order to avoid FK constraint issues
            if 'all' in types_to_clean or 'commands' in types_to_clean:
                logger.info("Cleaning commands...")
                result = await session.execute(text("DELETE FROM commands"))
                logger.info(f"Deleted {result.rowcount} commands")
            
            if 'all' in types_to_clean or 'sessions' in types_to_clean:
                logger.info("Cleaning sessions...")
                result = await session.execute(text("DELETE FROM sessions"))
                logger.info(f"Deleted {result.rowcount} sessions")
            
            if 'all' in types_to_clean or 'ssh' in types_to_clean:
                logger.info("Cleaning SSH profiles...")
                result = await session.execute(text("DELETE FROM ssh_profiles"))
                logger.info(f"Deleted {result.rowcount} SSH profiles")
                
                logger.info("Cleaning SSH keys...")
                result = await session.execute(text("DELETE FROM ssh_keys"))
                logger.info(f"Deleted {result.rowcount} SSH keys")
            
            if 'all' in types_to_clean or 'sync' in types_to_clean:
                logger.info("Cleaning sync data...")
                result = await session.execute(text("DELETE FROM sync_data"))
                logger.info(f"Deleted {result.rowcount} sync data records")
            
            if 'all' in types_to_clean or 'settings' in types_to_clean:
                logger.info("Cleaning user settings...")
                result = await session.execute(text("DELETE FROM user_settings"))
                logger.info(f"Deleted {result.rowcount} user settings")
            
            if 'all' in types_to_clean or 'users' in types_to_clean:
                logger.info("Cleaning users...")
                result = await session.execute(text("DELETE FROM users"))
                logger.info(f"Deleted {result.rowcount} users")
            
            # Reset sequences if requested
            if force_clean:
                logger.info("Resetting database sequences...")
                await session.execute(text("SELECT setval(pg_get_serial_sequence('users', 'id'), 1, false)"))
            
            await session.commit()
            logger.info("Database cleaning completed successfully")
            
    except Exception as e:
        logger.error(f"Database cleaning failed: {e}")
        raise

async def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python temp_clean_script.py <data_types> [force]")
        sys.exit(1)
    
    data_types = sys.argv[1]
    force_clean = len(sys.argv) > 2 and sys.argv[2].lower() == 'true'
    
    await clean_database(data_types, force_clean)

if __name__ == "__main__":
    asyncio.run(main())
