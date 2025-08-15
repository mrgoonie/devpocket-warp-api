import os
import sys
from logging.config import fileConfig
from dotenv import load_dotenv

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Load environment variables
load_dotenv()

# Add the project root to sys.path so we can import our models
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

# Import all models to ensure they're registered with SQLAlchemy
from app.models.base import Base
from app.models import (
    User, UserSettings, Session, Command, SSHProfile, SSHKey, SyncData
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the sqlalchemy.url from environment if available
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    if url is None:
        url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/dbname")
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Get the database URL and ensure it uses the sync driver
    configuration = config.get_section(config.config_ini_section, {})
    if 'sqlalchemy.url' not in configuration:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            # Ensure we use the sync driver (psycopg2) not the async driver
            database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
            configuration['sqlalchemy.url'] = database_url
    else:
        # Also ensure the configured URL uses sync driver
        url = configuration.get('sqlalchemy.url', '')
        if 'asyncpg' in url:
            configuration['sqlalchemy.url'] = url.replace("postgresql+asyncpg://", "postgresql://")
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
