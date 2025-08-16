"""
Global test configuration and fixtures for DevPocket API tests.
"""

import asyncio
import os
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
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
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5433/devpocket_test"
TEST_REDIS_URL = "redis://localhost:6380"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db_engine():
    """Create test database engine for the session."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        poolclass=StaticPool,
        connect_args={"server_settings": {"jit": "off"}},
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async_session = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Start a transaction
        await session.begin()
        
        try:
            yield session
        finally:
            # Rollback the transaction
            await session.rollback()


@pytest.fixture
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


@pytest.fixture
def app(test_session, mock_redis) -> FastAPI:
    """Create FastAPI application instance for testing."""
    app = create_application()
    
    # Override dependencies
    app.dependency_overrides[get_db] = lambda: test_session
    app.state.redis = mock_redis
    
    # Set Redis client for auth module
    set_redis_client(mock_redis)
    
    # Set Redis client for WebSocket manager
    connection_manager.redis = mock_redis
    
    return app


@pytest.fixture
def client(app) -> TestClient:
    """Create test client for synchronous requests."""
    return TestClient(app)


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client for async requests."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
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


@pytest.fixture
async def test_user(user_repository, user_data) -> User:
    """Create a test user in the database."""
    from app.auth.security import hash_password
    
    hashed_password = hash_password(user_data["password"])
    user = await user_repository.create({
        **user_data,
        "hashed_password": hashed_password
    })
    return user


@pytest.fixture
async def verified_user(user_repository, user_data) -> User:
    """Create a verified test user."""
    from app.auth.security import hash_password
    
    hashed_password = hash_password(user_data["password"])
    user = await user_repository.create({
        **user_data,
        "hashed_password": hashed_password,
        "is_verified": True,
        "verified_at": datetime.utcnow()
    })
    return user


@pytest.fixture
async def premium_user(user_repository, user_data) -> User:
    """Create a premium test user."""
    from app.auth.security import hash_password
    
    hashed_password = hash_password(user_data["password"])
    user = await user_repository.create({
        **user_data,
        "hashed_password": hashed_password,
        "is_verified": True,
        "verified_at": datetime.utcnow(),
        "subscription_tier": "premium",
        "subscription_expires_at": datetime.utcnow() + timedelta(days=30)
    })
    return user


# Authentication fixtures
@pytest.fixture
def auth_headers(test_user) -> dict:
    """Create authentication headers for test user."""
    access_token = create_access_token({"sub": test_user.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def premium_auth_headers(premium_user) -> dict:
    """Create authentication headers for premium user."""
    access_token = create_access_token({"sub": premium_user.email})
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
@pytest.fixture(autouse=True)
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