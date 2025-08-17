"""
Global test configuration and fixtures for DevPocket API tests.
"""

import asyncio
import os
import sys

import pytest
import pytest_asyncio

# Add project root to Python path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from collections.abc import AsyncGenerator, Generator  # noqa: E402
from datetime import UTC, datetime, timedelta  # noqa: E402
from unittest.mock import AsyncMock, MagicMock  # noqa: E402

import redis.asyncio as aioredis  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from httpx import AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.auth.security import (  # noqa: E402
    create_access_token,
    set_redis_client,
)
from app.db.database import get_db  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.user import User  # noqa: E402
from app.repositories.user import UserRepository  # noqa: E402
from app.websocket.manager import connection_manager  # noqa: E402
from main import create_application  # noqa: E402

# Test database configuration
# Use environment DATABASE_URL if available, otherwise fall back to localhost
TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5433/devpocket_test",
)
if not TEST_DATABASE_URL.startswith("postgresql+asyncpg://"):
    TEST_DATABASE_URL = TEST_DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://"
    )
TEST_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380")


async def _cleanup_test_data(engine):
    """Clear all test data while preserving database schema."""
    try:
        async with engine.begin() as conn:
            # Get all table names from the current schema
            result = await conn.execute(
                text(
                    """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename != 'alembic_version'
                ORDER BY tablename DESC
            """
                )
            )
            tables = [row[0] for row in result.fetchall()]

            if tables:
                # Disable foreign key checks temporarily for faster cleanup
                await conn.execute(text("SET session_replication_role = replica;"))
                
                # Use CASCADE truncation to handle foreign key constraints
                table_list = ", ".join(tables)
                await conn.execute(
                    text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE")
                )
                
                # Re-enable foreign key checks
                await conn.execute(text("SET session_replication_role = DEFAULT;"))

                # Reset sequences for primary keys - simplified approach
                await conn.execute(
                    text(
                        """
                    DO $$
                    DECLARE
                        seq_record RECORD;
                    BEGIN
                        FOR seq_record IN
                            SELECT sequence_name
                            FROM information_schema.sequences
                            WHERE sequence_schema = 'public'
                        LOOP
                            EXECUTE 'SELECT setval(''' || seq_record.sequence_name || ''', 1, false)';
                        END LOOP;
                    END
                    $$;
                    """
                    )
                )
    except Exception as e:
        # Log error but don't fail - cleanup is best effort
        print(f"Warning: Test data cleanup failed: {e}")


async def _clear_test_data_in_session(session):
    """Clear test data within a session transaction."""
    try:
        # Check which tables actually exist first
        existing_tables_result = await session.execute(
            text(
                """
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename != 'alembic_version'
                """
            )
        )
        existing_tables = {row[0] for row in existing_tables_result.fetchall()}
        
        # Clear data in dependency order (child tables first) - only if they exist
        tables_to_clear = [
            "user_settings",
            "command_history", 
            "session_commands",
            "ssh_keys",
            "ssh_profiles",
            "sessions",
            "sync_data",
            "users"
        ]
        
        for table in tables_to_clear:
            if table in existing_tables:
                await session.execute(text(f"DELETE FROM {table}"))
        
        # Reset sequences to ensure consistent IDs
        await session.execute(
            text(
                """
            DO $$
            DECLARE
                seq_record RECORD;
            BEGIN
                FOR seq_record IN
                    SELECT sequence_name
                    FROM information_schema.sequences
                    WHERE sequence_schema = 'public'
                LOOP
                    EXECUTE 'SELECT setval(''' || seq_record.sequence_name || ''', 1, false)';
                END LOOP;
            END
            $$;
            """
            )
        )
        
        await session.flush()
    except Exception as e:
        # Log error but don't fail - cleanup is best effort
        print(f"Warning: Session data cleanup failed: {e}")


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_db_engine():
    """Create test database engine for the session."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        poolclass=StaticPool,
        connect_args={"server_settings": {"jit": "off"}},
    )

    # Tables already exist from migrations - no need to create them
    # Just verify the engine can connect
    async with engine.begin() as conn:
        # Test connection by checking if users table exists (created by migration)
        result = await conn.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
            )
        )
        table_exists = result.scalar()
        if not table_exists:
            # Fallback: create tables if migration hasn't run
            await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up: Clear data but preserve schema for next test run
    await _cleanup_test_data(engine)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test with transaction isolation."""
    async_session_factory = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_factory() as session:
        # Start a nested transaction (savepoint) that will be rolled back after the test
        transaction = await session.begin()

        try:
            # Critical: Ensure we flush any initial operations to establish the transaction
            await session.execute(text("SELECT 1"))
            
            # Clear any existing test data at the start of each test
            await _clear_test_data_in_session(session)
            
            yield session
            
            # Don't commit in tests - let the test cleanup handle rollback
        except Exception:
            # Rollback on any exception
            if transaction.is_active:
                await transaction.rollback()
            raise
        finally:
            # Always rollback to ensure test isolation
            if transaction.is_active:
                await transaction.rollback()
            await session.close()


@pytest_asyncio.fixture
async def test_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """Create test Redis client."""
    redis_client = await aioredis.from_url(
        TEST_REDIS_URL,
        decode_responses=True,
        max_connections=10,
    )

    # Clear any existing data
    await redis_client.flushall()

    yield redis_client

    # Clean up
    await redis_client.flushall()
    await redis_client.close()


@pytest.fixture
def mock_redis() -> MagicMock:
    """Create a mocked Redis client for unit tests with proper isolation."""
    mock_redis = MagicMock()
    
    # Create a fresh storage for each test to simulate Redis isolation
    redis_storage = {}
    
    async def mock_get(key):
        return redis_storage.get(key)
    
    async def mock_set(key, value, ex=None, px=None, nx=False, xx=False):
        if nx and key in redis_storage:
            return False
        if xx and key not in redis_storage:
            return False
        redis_storage[key] = value
        return True
    
    async def mock_delete(*keys):
        deleted = 0
        for key in keys:
            if key in redis_storage:
                del redis_storage[key]
                deleted += 1
        return deleted
    
    async def mock_exists(key):
        return key in redis_storage
    
    async def mock_flushall():
        redis_storage.clear()
        return True
    
    async def mock_incr(key):
        current = int(redis_storage.get(key, 0))
        redis_storage[key] = str(current + 1)
        return current + 1
    
    async def mock_expire(key, seconds):
        # For testing, we'll just track that expire was called
        return key in redis_storage

    # Mock common Redis operations with proper state management
    mock_redis.get = mock_get
    mock_redis.set = mock_set
    mock_redis.delete = mock_delete
    mock_redis.exists = mock_exists
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.flushall = mock_flushall
    mock_redis.close = AsyncMock()
    mock_redis.incr = mock_incr
    mock_redis.expire = mock_expire
    
    # Additional methods that might be used in rate limiting
    mock_redis.setex = AsyncMock(return_value=True)
    mock_redis.ttl = AsyncMock(return_value=-1)
    mock_redis.keys = AsyncMock(return_value=[])

    return mock_redis


@pytest_asyncio.fixture
async def app(test_session, mock_redis) -> FastAPI:
    """Create FastAPI application instance for testing."""
    app = create_application()

    # Override dependencies to use the same test session
    async def override_get_db():
        # Use the same test session that's already set up with transaction isolation
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    app.state.redis = mock_redis

    # Set Redis client for auth module
    set_redis_client(mock_redis)

    # Set Redis client for WebSocket manager
    connection_manager.redis = mock_redis
    
    # Ensure middleware state is clean
    app.state.test_mode = True
    
    # Reset rate limiting middleware state for each test
    for middleware in app.user_middleware:
        if hasattr(middleware.cls, '__name__') and 'RateLimitMiddleware' in middleware.cls.__name__:
            # Reset the rate limit store if it exists
            if hasattr(middleware.cls, '_store'):
                middleware.cls._store = None

    return app


@pytest_asyncio.fixture
async def client(app) -> TestClient:
    """Create test client for synchronous requests."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client for async requests."""
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def user_repository(test_session) -> UserRepository:
    """Create user repository for testing."""
    return UserRepository(test_session)


# User fixtures
@pytest.fixture
def user_data() -> dict:
    """Basic user data for testing with unique identifiers."""
    import time
    import uuid
    import random
    import threading

    # Generate highly unique identifiers to prevent conflicts between tests
    unique_id = str(uuid.uuid4())[:8]
    timestamp = str(int(time.time() * 1000000))[-8:]  # Microsecond precision
    thread_id = str(threading.current_thread().ident)[-4:]  # Thread isolation
    random_suffix = str(random.randint(10000, 99999))

    return {
        "email": f"test_{unique_id}_{timestamp}_{thread_id}_{random_suffix}@example.com",
        "username": f"test_{unique_id}_{timestamp}"[:30],  # Ensure max 30 chars
        "password": "SecurePassword123!",
        "full_name": f"Test User {unique_id}",
    }


@pytest_asyncio.fixture
async def test_user(user_repository, user_data) -> User:
    """Create a test user in the database."""
    from app.auth.security import hash_password
    from app.models.user import UserRole

    hashed_password = hash_password(user_data["password"])
    create_data = {k: v for k, v in user_data.items() if k != "password"}
    # Explicitly set the role to ensure it's using the enum value correctly
    create_data["role"] = UserRole.USER
    user = await user_repository.create(**create_data, hashed_password=hashed_password)
    return user


@pytest_asyncio.fixture
async def verified_user(user_repository, user_data) -> User:
    """Create a verified test user."""
    from app.auth.security import hash_password
    from app.models.user import UserRole

    hashed_password = hash_password(user_data["password"])
    create_data = {k: v for k, v in user_data.items() if k != "password"}
    create_data["role"] = UserRole.USER
    user = await user_repository.create(
        **create_data,
        hashed_password=hashed_password,
        is_verified=True,
        verified_at=datetime.now(UTC),
    )
    return user


@pytest_asyncio.fixture
async def premium_user(user_repository, user_data) -> User:
    """Create a premium test user."""
    from app.auth.security import hash_password
    from app.models.user import UserRole

    hashed_password = hash_password(user_data["password"])
    create_data = {k: v for k, v in user_data.items() if k != "password"}
    create_data["role"] = UserRole.PREMIUM
    user = await user_repository.create(
        **create_data,
        hashed_password=hashed_password,
        is_verified=True,
        verified_at=datetime.now(UTC),
        subscription_tier="premium",
        subscription_expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    return user


# Authentication fixtures
@pytest_asyncio.fixture
async def auth_headers(verified_user) -> dict:
    """Create authentication headers for verified user."""
    user = verified_user  # verified_user is already awaited
    access_token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def premium_auth_headers(premium_user) -> dict:
    """Create authentication headers for premium user."""
    user = premium_user  # premium_user is already awaited
    access_token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def expired_auth_headers() -> dict:
    """Create expired authentication headers."""
    # Create token that expires immediately
    access_token = create_access_token(
        {"sub": "test@example.com"}, expires_delta=timedelta(seconds=-1)
    )
    return {"Authorization": f"Bearer {access_token}"}


# Mock service fixtures
@pytest.fixture
def mock_openrouter_service():
    """Mock OpenRouter AI service."""
    mock_service = AsyncMock()
    mock_service.generate_command.return_value = {
        "command": "ls -la",
        "explanation": "List all files in the current directory",
        "confidence": 0.95,
    }
    mock_service.analyze_command.return_value = {
        "safe": True,
        "risk_level": "low",
        "explanation": "Safe command",
    }
    return mock_service


@pytest.fixture
def mock_ssh_client():
    """Mock SSH client service."""
    mock_client = AsyncMock()
    mock_client.connect.return_value = True
    mock_client.execute_command.return_value = {
        "stdout": "Command output",
        "stderr": "",
        "exit_code": 0,
    }
    mock_client.disconnect.return_value = None
    return mock_client


@pytest.fixture
def mock_terminal_service():
    """Mock terminal service."""
    mock_service = AsyncMock()
    mock_service.create_session.return_value = "session_123"
    mock_service.write_input.return_value = True
    mock_service.read_output.return_value = "Terminal output"
    mock_service.close_session.return_value = True
    return mock_service


# WebSocket test fixtures
@pytest.fixture
def websocket_mock():
    """Create mock WebSocket for testing."""
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_text = AsyncMock()
    mock_ws.send_bytes = AsyncMock()
    mock_ws.receive_text = AsyncMock()
    mock_ws.receive_bytes = AsyncMock()
    mock_ws.close = AsyncMock()
    return mock_ws


# Test data cleanup
@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_data(test_session):
    """Auto cleanup test data after each test."""
    yield
    # Cleanup happens in test_session fixture rollback
    # Additional cleanup to ensure test isolation
    try:
        # Force rollback any active transactions
        if test_session.in_transaction():
            await test_session.rollback()
    except Exception:
        # Ignore cleanup errors - session will be closed anyway
        pass


# Rate limiting cleanup
@pytest.fixture(autouse=True)
def cleanup_rate_limiting():
    """Reset rate limiting state between tests."""
    # Clear any rate limiting storage before and after the test
    try:
        from app.middleware.rate_limit import rate_limit_store
        # Clear the global rate limit store before test
        rate_limit_store._store.clear()
        rate_limit_store._last_cleanup = 0
    except Exception:
        pass
    
    yield
    
    # Reset rate limit store after test
    try:
        from app.middleware.rate_limit import rate_limit_store
        # Clear the global rate limit store after test
        rate_limit_store._store.clear()
        rate_limit_store._last_cleanup = 0
    except Exception:
        # Ignore cleanup errors
        pass


# Environment setup
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment variables."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("REDIS_URL", TEST_REDIS_URL)
    
    # Reset any global state that might interfere with tests
    import app.auth.security as auth_security
    auth_security._redis_client = None  # Reset Redis client


# Pytest markers for test categorization
pytest_plugins = ["pytest_asyncio"]


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "websocket: WebSocket tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "auth: Authentication tests")
    config.addinivalue_line("markers", "database: Database tests")
    config.addinivalue_line("markers", "services: Service layer tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "external: Tests requiring external services")
