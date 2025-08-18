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
    """Clear all test data while preserving database schema with enhanced isolation."""
    import asyncio
    
    max_retries = 3
    retry_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                # Add session-level timeout to prevent hanging
                await conn.execute(text("SET statement_timeout = '30s';"))
                
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
                    # Enhanced cleanup with explicit transaction isolation
                    await conn.execute(text("SET session_replication_role = replica;"))
                    await conn.execute(text("SET lock_timeout = '10s';"))
                    
                    # Use CASCADE truncation to handle foreign key constraints
                    table_list = ", ".join(tables)
                    await conn.execute(
                        text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE")
                    )
                    
                    # Re-enable foreign key checks
                    await conn.execute(text("SET session_replication_role = DEFAULT;"))
                    await conn.execute(text("RESET lock_timeout;"))

                    # Reset sequences for primary keys with error handling
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
                                BEGIN
                                    EXECUTE 'SELECT setval(''' || seq_record.sequence_name || ''', 1, false)';
                                EXCEPTION WHEN OTHERS THEN
                                    -- Continue if sequence reset fails
                                    NULL;
                                END;
                            END LOOP;
                        END
                        $$;
                        """
                        )
                    )
                    
                # Commit transaction explicitly
                await conn.commit()
                break  # Success, exit retry loop
                
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Warning: Test data cleanup attempt {attempt + 1} failed: {e}. Retrying...")
                await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
            else:
                print(f"Error: Test data cleanup failed after {max_retries} attempts: {e}")
                # Don't raise - cleanup failures shouldn't break tests


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
        connect_args={
            "server_settings": {
                "jit": "off",
                "statement_timeout": "30s",
                "lock_timeout": "10s",
                "idle_in_transaction_session_timeout": "30s",
            }
        },
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
    """Create a fresh database session for each test with proper transaction isolation."""
    connection = await test_db_engine.connect()
    transaction = await connection.begin()
    
    async_session_factory = sessionmaker(
        bind=connection, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_factory() as session:
        try:
            # Start a savepoint for the test
            savepoint = await connection.begin_nested()
            
            # Clear any existing test data at the start of each test
            await _clear_test_data_in_session(session)
            await session.flush()
            
            yield session
            
        except Exception:
            # Rollback the savepoint on any exception
            await savepoint.rollback()
            raise
        finally:
            # Always close the session
            await session.close()
            # Rollback the main transaction to ensure test isolation
            await transaction.rollback()
            await connection.close()


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


class MockRedisClient:
    """Enhanced mock Redis client with proper state isolation."""
    
    def __init__(self):
        self._storage = {}
        self._ttl_storage = {}
        self._pubsub_channels = {}
        
    async def get(self, key):
        return self._storage.get(key)
    
    async def set(self, key, value, ex=None, px=None, nx=False, xx=False):
        if nx and key in self._storage:
            return False
        if xx and key not in self._storage:
            return False
        self._storage[key] = str(value)
        if ex:
            self._ttl_storage[key] = ex
        return True
    
    async def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self._storage:
                del self._storage[key]
                self._ttl_storage.pop(key, None)
                deleted += 1
        return deleted
    
    async def exists(self, key):
        return key in self._storage
    
    async def flushall(self):
        self._storage.clear()
        self._ttl_storage.clear()
        self._pubsub_channels.clear()
        return True
    
    async def incr(self, key):
        current = int(self._storage.get(key, 0))
        new_value = current + 1
        self._storage[key] = str(new_value)
        return new_value
    
    async def expire(self, key, seconds):
        if key in self._storage:
            self._ttl_storage[key] = seconds
            return True
        return False
    
    async def setex(self, key, seconds, value):
        self._storage[key] = str(value)
        self._ttl_storage[key] = seconds
        return True
    
    async def ttl(self, key):
        return self._ttl_storage.get(key, -1)
    
    async def keys(self, pattern="*"):
        if pattern == "*":
            return list(self._storage.keys())
        # Simple pattern matching for testing
        import fnmatch
        return [k for k in self._storage.keys() if fnmatch.fnmatch(k, pattern)]
    
    async def ping(self):
        return True
    
    async def close(self):
        pass
    
    def pubsub(self):
        """Return a mock pubsub object."""
        from unittest.mock import AsyncMock
        mock_pubsub = AsyncMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.publish = AsyncMock(return_value=1)
        mock_pubsub.get_message = AsyncMock(return_value=None)
        return mock_pubsub


@pytest.fixture
def mock_redis() -> MockRedisClient:
    """Create a mocked Redis client for unit tests with proper isolation."""
    return MockRedisClient()


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
    import os
    
    # Generate highly unique identifiers to prevent conflicts between tests
    # Include process ID for multi-process testing and nanosecond precision
    unique_id = str(uuid.uuid4())[:8]
    process_id = str(os.getpid())[-4:]  # Process isolation for parallel workers
    timestamp = str(int(time.time_ns()))[-12:]  # Nanosecond precision 
    thread_id = str(threading.current_thread().ident)[-4:]  # Thread isolation
    random_suffix = str(random.randint(100000, 999999))
    
    # Create ultra-unique identifier that includes all isolation factors
    ultra_unique = f"{unique_id}_{process_id}_{timestamp}_{thread_id}_{random_suffix}"
    
    return {
        "email": f"test_{ultra_unique}@example.com",
        "username": f"test_{ultra_unique}"[:30],  # Ensure max 30 chars
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
