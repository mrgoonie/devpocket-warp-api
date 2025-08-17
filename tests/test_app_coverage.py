"""
Basic unit tests to improve code coverage for core application modules.
"""

import pytest

from app.auth import dependencies, security
from app.db import database
from app.models import command, session, ssh_profile, sync, user
from app.repositories import user as user_repo
from app.websocket import manager
from main import create_application


@pytest.mark.unit
class TestAppImports:
    """Test that core application modules can be imported and initialized."""

    def test_main_app_creation(self):
        """Test that the main application can be created."""
        app = create_application()
        assert app is not None
        assert hasattr(app, "routes")

    def test_model_imports(self):
        """Test that all models can be imported."""
        assert hasattr(user, "User")
        assert hasattr(session, "Session")
        assert hasattr(ssh_profile, "SSHProfile")
        assert hasattr(command, "Command")
        assert hasattr(sync, "SyncData")

    def test_auth_imports(self):
        """Test that auth modules can be imported."""
        assert hasattr(security, "create_access_token")
        assert hasattr(dependencies, "get_current_user")

    def test_db_imports(self):
        """Test that database modules can be imported."""
        assert hasattr(database, "get_db")
        assert hasattr(database, "Base")

    def test_repository_imports(self):
        """Test that repository modules can be imported."""
        assert hasattr(user_repo, "UserRepository")

    def test_websocket_imports(self):
        """Test that websocket modules can be imported."""
        assert hasattr(manager, "ConnectionManager")
        assert hasattr(manager, "connection_manager")


@pytest.mark.unit
class TestBasicFunctionality:
    """Test basic functionality of core components."""

    def test_connection_manager(self):
        """Test WebSocket connection manager."""
        conn_manager = manager.connection_manager
        assert conn_manager is not None
        assert hasattr(conn_manager, "connect")
        assert hasattr(conn_manager, "disconnect")

    def test_user_model_creation(self):
        """Test User model creation without database."""
        from app.models.user import User

        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hashed_password",
        }

        user = User(**user_data)
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.is_verified is False

    def test_security_functions(self):
        """Test security utility functions."""
        from app.auth.security import hash_password, verify_password

        password = "test_password_123"
        hashed = hash_password(password)

        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False


@pytest.mark.unit
class TestConstants:
    """Test application constants and configurations."""

    def test_app_constants(self):
        """Test that important constants are defined."""
        from app.models.user import User

        # Test default values
        user = User(email="test@example.com", username="test", password_hash="hash")
        assert user.subscription_tier == "free"
        assert user.is_active is True

    def test_websocket_manager_singleton(self):
        """Test that connection manager is a singleton."""
        from app.websocket.manager import connection_manager

        # Import again to verify it's the same instance
        from app.websocket.manager import connection_manager as conn_mgr_2

        assert connection_manager is conn_mgr_2
