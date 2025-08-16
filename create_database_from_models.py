#!/usr/bin/env python3
"""
Create database from SQLAlchemy models
"""

import asyncio
import sys
from pathlib import Path

# Load environment FIRST
import os
from dotenv import load_dotenv
load_dotenv(override=True)

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

async def create_database_from_models():
    """Create database using SQLAlchemy models."""
    print("🚀 Creating DevPocket database from SQLAlchemy models...")
    print(f"Using DATABASE_URL: {os.getenv('DATABASE_URL')}")
    
    # Import after environment is loaded
    from app.core.config import Settings
    from app.db.database import engine
    from app.models.base import Base
    from sqlalchemy import text
    
    # Import all models to ensure they're registered
    from app.models import User, UserSettings, Session, Command, SSHProfile, SSHKey, SyncData
    
    # Create fresh settings
    settings = Settings()
    print(f"Settings database URL: {settings.database_url}")
    
    try:
        async with engine.begin() as conn:
            print("🗑️  Dropping existing tables...")
            # Drop all tables with CASCADE to handle dependencies
            await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
            
            # Create enum first
            print("🏷️  Creating user_role enum...")
            await conn.execute(text("CREATE TYPE user_role AS ENUM ('user', 'admin', 'premium')"))
            
            # Create all tables from models
            print("📊 Creating tables from SQLAlchemy models...")
            await conn.run_sync(Base.metadata.create_all)
            
            # Create alembic_version table manually
            print("🔧 Creating alembic_version table...")
            await conn.execute(text("""
                CREATE TABLE alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """))
            
            # Insert alembic version
            print("🔧 Setting up alembic version...")
            await conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('2f441b98e37b')"))
            
            print("✅ Database created successfully!")
            
            # Verify tables
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
            )
            tables = result.fetchall()
            table_names = [t[0] for t in tables]
            print(f"📊 Created tables: {table_names}")
            
            # Verify enum
            result = await conn.execute(
                text("SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_role') ORDER BY enumlabel")
            )
            enum_values = result.fetchall()
            enum_labels = [e[0] for e in enum_values]
            print(f"🏷️  Created enum user_role: {enum_labels}")
            
        return True
        
    except Exception as e:
        print(f"❌ Database creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(create_database_from_models())
    if success:
        print("\n🎉 Database is ready! Now you can:")
        print("   1. Seed data: ./scripts/db_seed.sh all 10")
        print("   2. Check health: python ./scripts/db_utils.py health")
        print("   3. Start the app: python main.py")
    exit(0 if success else 1)