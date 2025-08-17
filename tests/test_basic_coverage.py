"""
Additional basic tests to improve overall code coverage.
"""


import pytest

from app.auth.security import create_access_token, create_refresh_token
from app.models.base import Base
from app.models.command import Command
from app.models.session import Session
from app.models.ssh_profile import SSHKey, SSHProfile
from app.models.sync import SyncData


@pytest.mark.unit
class TestSecurityModule:
    """Test auth security module functions."""

    def test_token_creation(self):
        """Test JWT token creation."""
        # Test access token
        access_token = create_access_token({"sub": "test@example.com"})
        assert access_token is not None
        assert isinstance(access_token, str)

        # Test refresh token
        refresh_token = create_refresh_token({"sub": "test@example.com"})
        assert refresh_token is not None
        assert isinstance(refresh_token, str)
        assert refresh_token != access_token


@pytest.mark.unit
class TestModelMethods:
    """Test model methods without database connection."""

    def test_session_methods(self):
        """Test Session model methods."""
        session = Session(user_id="user123", device_id="device456", device_type="web")

        # Test is_ssh_session method
        assert session.is_ssh_session() is False

        session.ssh_host = "example.com"
        assert session.is_ssh_session() is True

        # Test resize_terminal method
        session.resize_terminal(120, 40)
        assert session.terminal_cols == 120
        assert session.terminal_rows == 40

    def test_command_methods(self):
        """Test Command model methods."""
        command = Command(session_id="session123", command="git status")

        # Test classify_command
        assert command.classify_command() == "git"

        command.command = "ls -la"
        assert command.classify_command() == "file_operation"

        command.command = "ping google.com"
        assert command.classify_command() == "network"

        # Test sensitive content detection
        sensitive_cmd = Command(
            session_id="session123", command="export PASSWORD=secret123"
        )
        assert sensitive_cmd.check_sensitive_content() is True

        normal_cmd = Command(session_id="session123", command="ls")
        assert normal_cmd.check_sensitive_content() is False

    def test_ssh_profile_methods(self):
        """Test SSHProfile model methods."""
        profile = SSHProfile(
            user_id="user123",
            name="Test Server",
            host="example.com",
            username="testuser",
        )

        # Test success rate calculation
        assert profile.success_rate == 0.0

        # Test connection recording
        profile.record_connection_attempt(True)
        assert profile.connection_count == 1
        assert profile.successful_connections == 1

        profile.record_connection_attempt(False)
        assert profile.connection_count == 2
        assert profile.failed_connections == 1

        # Success rate should be 50%
        assert profile.success_rate == 50.0

    def test_ssh_key_methods(self):
        """Test SSHKey model methods."""
        ssh_key = SSHKey(
            user_id="user123",
            name="Test Key",
            key_type="rsa",
            fingerprint="abcdef1234567890abcdef1234567890",
            encrypted_private_key=b"key_data",
            public_key="ssh-rsa AAAAB3...",
        )

        # Test short fingerprint
        short_fp = ssh_key.short_fingerprint
        assert len(short_fp) == 19  # 8 + 3 + 8 characters
        assert "..." in short_fp

        # Test usage recording
        initial_usage = ssh_key.usage_count
        ssh_key.record_usage()
        assert ssh_key.usage_count == initial_usage + 1

    def test_sync_data_methods(self):
        """Test SyncData model methods."""
        sync_data = SyncData.create_sync_item(
            user_id="user123",
            sync_type="settings",
            sync_key="user_settings",
            data={"theme": "dark"},
            device_id="device456",
            device_type="ios",
        )

        assert sync_data.sync_type == "settings"
        assert sync_data.version == 1
        assert sync_data.data == {"theme": "dark"}

        # Test update
        sync_data.update_data(
            new_data={"theme": "light"}, device_id="device789", device_type="android"
        )
        assert sync_data.version == 2
        assert sync_data.data == {"theme": "light"}

        # Test conflict creation
        sync_data.create_conflict({"theme": "auto"})
        assert sync_data.has_conflict is True
        assert sync_data.conflict_data is not None


@pytest.mark.unit
class TestBaseModel:
    """Test base model functionality."""

    def test_base_model_exists(self):
        """Test that Base model is properly configured."""
        assert Base is not None
        assert hasattr(Base, "metadata")
        assert hasattr(Base, "registry")


@pytest.mark.unit
class TestUtilityFunctions:
    """Test utility functions across modules."""

    def test_password_utilities(self):
        """Test password hashing utilities."""
        from app.auth.security import hash_password, verify_password

        password = "TestPassword123!"
        hashed = hash_password(password)

        # Test that password is properly hashed
        assert hashed != password
        assert len(hashed) > 50  # BCrypt hashes are long
        assert hashed.startswith("$2b$")  # BCrypt format

        # Test verification
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword", hashed) is False
        assert verify_password("", hashed) is False

    def test_user_model_utilities(self):
        """Test User model utility methods."""
        from app.models.user import User

        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
        )

        # Test to_dict method
        user_dict = user.to_dict()
        assert isinstance(user_dict, dict)
        assert user_dict["email"] == "test@example.com"
        assert user_dict["username"] == "testuser"

        # Test account locking
        assert not user.is_locked()
        assert user.failed_login_attempts == 0

        # Test failed login increment
        for _ in range(5):
            user.increment_failed_login()

        assert user.is_locked()
        assert user.failed_login_attempts == 5

        # Test reset
        user.reset_failed_login()
        assert not user.is_locked()
        assert user.failed_login_attempts == 0
