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
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import create_application
from app.core.config import settings
from app.auth.security import create_access_token, create_refresh_token
from app.db.database import get_db, db_manager
from app.models.base import Base
from app.models.user import User
from app.repositories.user import UserRepository
from app.auth.security import set_redis_client
from app.websocket.manager import connection_manager


# Test database configuration  
# Use environment DATABASE_URL if available, otherwise fall back to localhost
TEST_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5433/devpocket_test")
if not TEST_DATABASE_URL.startswith("postgresql+asyncpg://"):
    TEST_DATABASE_URL = TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
TEST_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380")


async def _cleanup_test_data(engine):
    """Clear all test data while preserving database schema."""
    async with engine.begin() as conn:
        # Get all table names from the current schema
        result = await conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename != 'alembic_version'
            ORDER BY tablename
        """))
        tables = [row[0] for row in result.fetchall()]
        
        if tables:
            # Disable foreign key checks temporarily
            await conn.execute(text("SET session_replication_role = 'replica'"))
            
            # Truncate all tables
            for table in tables:
                await conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
            
            # Re-enable foreign key checks
            await conn.execute(text("SET session_replication_role = 'origin'"))


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
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
        ))
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
        # Start a transaction that will be rolled back after the test
        transaction = await session.begin()
        
        try:
            yield session
        finally:
            # Always rollback to ensure test isolation
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
    """Create a mocked Redis client for unit tests."""
    mock_redis = MagicMock()
    
    # Mock common Redis operations
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.exists = AsyncMock(return_value=False)
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.flushall = AsyncMock(return_value=True)
    mock_redis.close = AsyncMock()
    
    return mock_redis


@pytest_asyncio.fixture
async def app(test_db_engine, mock_redis) -> FastAPI:
    """Create FastAPI application instance for testing."""
    app = create_application()
    
    # Create a test session factory
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    test_session_factory = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Override dependencies
    async def override_get_db():
        async with test_session_factory() as session:
            # Use transaction for each request to ensure isolation
            transaction = await session.begin()
            try:
                yield session
                await transaction.commit()
            except Exception:
                await transaction.rollback()
                raise
            finally:
                await session.close()
                
    app.dependency_overrides[get_db] = override_get_db
    app.state.redis = mock_redis
    
    # Set Redis client for auth module
    set_redis_client(mock_redis)
    
    # Set Redis client for WebSocket manager
    connection_manager.redis = mock_redis
    
    return app


@pytest_asyncio.fixture
async def client(app) -> TestClient:
    """Create test client for synchronous requests."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client for async requests."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def user_repository(test_session) -> UserRepository:
    """Create user repository for testing."""
    return UserRepository(test_session)


# User fixtures
@pytest.fixture
def user_data() -> dict:
    """Basic user data for testing."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "SecurePassword123!",
        "full_name": "Test User"
    }


@pytest_asyncio.fixture
async def test_user(user_repository, user_data) -> User:
    """Create a test user in the database."""
    from app.auth.security import hash_password
    
    hashed_password = hash_password(user_data["password"])
    create_data = {k: v for k, v in user_data.items() if k != "password"}
    user = await user_repository.create(
        **create_data,
        hashed_password=hashed_password
    )
    return user


@pytest_asyncio.fixture
async def verified_user(user_repository, user_data) -> User:
    """Create a verified test user."""
    from app.auth.security import hash_password
    
    hashed_password = hash_password(user_data["password"])
    create_data = {k: v for k, v in user_data.items() if k != "password"}
    user = await user_repository.create(
        **create_data,
        hashed_password=hashed_password,
        is_verified=True,
        verified_at=datetime.now(timezone.utc)
    )
    return user


@pytest_asyncio.fixture
async def premium_user(user_repository, user_data) -> User:
    """Create a premium test user."""
    from app.auth.security import hash_password
    
    hashed_password = hash_password(user_data["password"])
    create_data = {k: v for k, v in user_data.items() if k != "password"}
    user = await user_repository.create(
        **create_data,
        hashed_password=hashed_password,
        is_verified=True,
        verified_at=datetime.now(timezone.utc),
        subscription_tier="premium",
        subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    )
    return user


# Authentication fixtures
@pytest_asyncio.fixture
async def auth_headers(test_user) -> dict:
    """Create authentication headers for test user."""
    user = test_user  # test_user is already awaited
    access_token = create_access_token({"sub": user.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def premium_auth_headers(premium_user) -> dict:
    """Create authentication headers for premium user."""
    user = premium_user  # premium_user is already awaited
    access_token = create_access_token({"sub": user.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def expired_auth_headers() -> dict:
    """Create expired authentication headers."""
    # Create token that expires immediately
    access_token = create_access_token(
        {"sub": "test@example.com"},
        expires_delta=timedelta(seconds=-1)
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
        "confidence": 0.95
    }
    mock_service.analyze_command.return_value = {
        "safe": True,
        "risk_level": "low",
        "explanation": "Safe command"
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
        "exit_code": 0
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


# Environment setup
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment variables."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("REDIS_URL", TEST_REDIS_URL)


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