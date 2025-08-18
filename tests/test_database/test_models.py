"""
Test all SQLAlchemy models and their relationships.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.command import Command
from app.models.session import Session
from app.models.ssh_profile import SSHKey, SSHProfile
from app.models.sync import SyncData
from app.models.user import User, UserSettings


@pytest.mark.database
@pytest.mark.unit
class TestUserModel:
    """Test User model functionality."""

    async def test_user_creation(self, test_session):
        """Test basic user creation."""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hashed_password",
        }

        user = User(**user_data)
        test_session.add(user)
        await test_session.commit()

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.subscription_tier == "free"

    async def test_user_unique_constraints(self, test_session):
        """Test unique constraints on email and username."""
        user1 = User(
            email="test@example.com",
            username="testuser",
            password_hash="hash1",
        )
        user2 = User(
            email="test@example.com",  # Duplicate email
            username="testuser2",
            password_hash="hash2",
        )

        test_session.add(user1)
        await test_session.commit()

        test_session.add(user2)
        with pytest.raises(IntegrityError):
            await test_session.commit()

    async def test_user_account_locking(self, test_session):
        """Test user account locking mechanism."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")

        # Test initial state
        assert not user.is_locked()
        assert user.can_login() is False  # Not verified

        # Verify user
        user.is_verified = True
        assert user.can_login() is True

        # Test failed login attempts
        for _ in range(4):
            user.increment_failed_login()
            assert not user.is_locked()

        # 5th attempt should lock account
        user.increment_failed_login()
        assert user.is_locked()
        assert user.failed_login_attempts == 5
        assert user.locked_until is not None
        assert not user.can_login()

    async def test_user_login_reset(self, test_session):
        """Test resetting failed login attempts."""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            is_verified=True,
            failed_login_attempts=3,
        )

        user.reset_failed_login()

        assert user.failed_login_attempts == 0
        assert user.locked_until is None
        assert user.last_login_at is not None

    async def test_user_to_dict(self, test_session):
        """Test user to_dict conversion."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")

        user_dict = user.to_dict()

        assert isinstance(user_dict, dict)
        assert user_dict["email"] == "test@example.com"
        assert user_dict["username"] == "testuser"
        assert "password_hash" in user_dict

    async def test_user_relationships(self, test_session):
        """Test user model relationships."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()  # Get user ID

        # Add related objects
        session = Session(user_id=user.id, device_id="device123", device_type="web")
        ssh_profile = SSHProfile(
            user_id=user.id,
            name="Test Server",
            host="example.com",
            username="testuser",
        )

        test_session.add_all([session, ssh_profile])
        await test_session.commit()

        # Test relationships
        await test_session.refresh(user, ["sessions", "ssh_profiles"])
        assert len(user.sessions) == 1
        assert len(user.ssh_profiles) == 1
        assert user.sessions[0].device_type == "web"
        assert user.ssh_profiles[0].name == "Test Server"


@pytest.mark.database
@pytest.mark.unit
class TestUserSettingsModel:
    """Test UserSettings model functionality."""

    async def test_user_settings_creation(self, test_session):
        """Test user settings creation."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        settings = UserSettings(
            user_id=user.id,
            terminal_theme="dark",
            preferred_ai_model="claude-3-haiku",
        )
        test_session.add(settings)
        await test_session.commit()

        assert settings.id is not None
        assert settings.user_id == user.id
        assert settings.terminal_theme == "dark"
        assert settings.terminal_font_size == 14  # Default
        assert settings.ai_suggestions_enabled is True  # Default

    async def test_user_settings_relationship(self, test_session):
        """Test user-settings relationship."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        settings = UserSettings(user_id=user.id)
        test_session.add(settings)
        await test_session.commit()

        # Test relationship
        await test_session.refresh(user, ["settings"])
        await test_session.refresh(settings, ["user"])

        assert user.settings.id == settings.id
        assert settings.user.id == user.id


@pytest.mark.database
@pytest.mark.unit
class TestSessionModel:
    """Test Session model functionality."""

    async def test_session_creation(self, test_session):
        """Test session creation."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        session = Session(
            user_id=user.id,
            device_id="device123",
            device_type="ios",
            device_name="iPhone 15",
            session_name="Terminal Session",
        )
        test_session.add(session)
        await test_session.commit()

        assert session.id is not None
        assert session.user_id == user.id
        assert session.device_type == "ios"
        assert session.is_active is True
        assert session.terminal_cols == 80  # Default
        assert session.terminal_rows == 24  # Default

    async def test_session_ssh_properties(self, test_session):
        """Test SSH session properties."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        # Regular session
        regular_session = Session(
            user_id=user.id, device_id="device123", device_type="web"
        )

        # SSH session
        ssh_session = Session(
            user_id=user.id,
            device_id="device456",
            device_type="web",
            ssh_host="example.com",
            ssh_port=22,
            ssh_username="remoteuser",
        )

        test_session.add_all([regular_session, ssh_session])
        await test_session.commit()

        assert not regular_session.is_ssh_session()
        assert ssh_session.is_ssh_session()

    async def test_session_activity_tracking(self, test_session):
        """Test session activity tracking."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        session = Session(user_id=user.id, device_id="device123", device_type="web")
        test_session.add(session)
        await test_session.commit()

        # Test activity update
        initial_activity = session.last_activity_at
        session.update_activity()
        assert session.last_activity_at != initial_activity

        # Test session ending
        assert session.is_active is True
        assert session.ended_at is None

        session.end_session()
        assert session.is_active is False
        assert session.ended_at is not None

    async def test_session_terminal_resize(self, test_session):
        """Test terminal resize functionality."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        session = Session(user_id=user.id, device_id="device123", device_type="web")
        test_session.add(session)
        await test_session.commit()

        session.resize_terminal(120, 40)

        assert session.terminal_cols == 120
        assert session.terminal_rows == 40
        assert session.last_activity_at is not None


@pytest.mark.database
@pytest.mark.unit
class TestSSHProfileModel:
    """Test SSHProfile model functionality."""

    async def test_ssh_profile_creation(self, test_session):
        """Test SSH profile creation."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        profile = SSHProfile(
            user_id=user.id,
            name="Production Server",
            host="prod.example.com",
            username="deploy",
            port=22,
        )
        test_session.add(profile)
        await test_session.commit()

        assert profile.id is not None
        assert profile.name == "Production Server"
        assert profile.auth_method == "key"  # Default
        assert profile.compression is True  # Default
        assert profile.connection_timeout == 30  # Default

    async def test_ssh_profile_connection_tracking(self, test_session):
        """Test connection attempt tracking."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        profile = SSHProfile(
            user_id=user.id,
            name="Test Server",
            host="test.example.com",
            username="testuser",
        )
        test_session.add(profile)
        await test_session.commit()

        # Test successful connection
        initial_success_count = profile.successful_connections
        profile.record_connection_attempt(True)

        assert profile.connection_count == 1
        assert profile.successful_connections == initial_success_count + 1
        assert profile.last_used_at is not None

        # Test failed connection
        profile.record_connection_attempt(False)

        assert profile.connection_count == 2
        assert profile.failed_connections == 1

    async def test_ssh_profile_success_rate(self, test_session):
        """Test success rate calculation."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        profile = SSHProfile(
            user_id=user.id,
            name="Test Server",
            host="test.example.com",
            username="testuser",
        )
        test_session.add(profile)
        await test_session.commit()

        # No connections yet
        assert profile.success_rate == 0.0

        # Record some connections
        profile.record_connection_attempt(True)
        profile.record_connection_attempt(True)
        profile.record_connection_attempt(False)

        assert profile.success_rate == 66.67  # 2/3 * 100, rounded


@pytest.mark.database
@pytest.mark.unit
class TestSSHKeyModel:
    """Test SSHKey model functionality."""

    async def test_ssh_key_creation(self, test_session):
        """Test SSH key creation."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        ssh_key = SSHKey(
            user_id=user.id,
            name="My SSH Key",
            key_type="rsa",
            key_size=4096,
            fingerprint="abcdef1234567890",
            encrypted_private_key=b"encrypted_key_data",
            public_key="ssh-rsa AAAAB3NzaC1yc2E...",
        )
        test_session.add(ssh_key)
        await test_session.commit()

        assert ssh_key.id is not None
        assert ssh_key.key_type == "rsa"
        assert ssh_key.key_size == 4096
        assert ssh_key.is_active is True
        assert ssh_key.usage_count == 0

    async def test_ssh_key_usage_tracking(self, test_session):
        """Test SSH key usage tracking."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        ssh_key = SSHKey(
            user_id=user.id,
            name="Test Key",
            key_type="ed25519",
            fingerprint="fedcba0987654321",
            encrypted_private_key=b"key_data",
            public_key="ssh-ed25519 AAAAB3...",
        )
        test_session.add(ssh_key)
        await test_session.commit()

        initial_usage = ssh_key.usage_count
        ssh_key.record_usage()

        assert ssh_key.usage_count == initial_usage + 1
        assert ssh_key.last_used_at is not None

    async def test_ssh_key_fingerprint_property(self, test_session):
        """Test SSH key fingerprint property."""
        ssh_key = SSHKey(
            user_id="user_id",
            name="Test Key",
            key_type="rsa",
            fingerprint="abcdef1234567890abcdef1234567890",
            encrypted_private_key=b"key_data",
            public_key="ssh-rsa AAAAB3...",
        )

        short_fp = ssh_key.short_fingerprint
        assert len(short_fp) == 19  # 8 + 3 + 8 characters
        assert short_fp.startswith("abcdef12")
        assert short_fp.endswith("67890")
        assert "..." in short_fp


@pytest.mark.database
@pytest.mark.unit
class TestCommandModel:
    """Test Command model functionality."""

    async def test_command_creation(self, test_session):
        """Test command creation."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        session = Session(user_id=user.id, device_id="device123", device_type="web")
        test_session.add(session)
        await test_session.flush()

        command = Command(session_id=session.id, command="ls -la", status="pending")
        test_session.add(command)
        await test_session.commit()

        assert command.id is not None
        assert command.command == "ls -la"
        assert command.status == "pending"
        assert command.was_ai_suggested is False
        assert command.is_sensitive is False

    async def test_command_execution_lifecycle(self, test_session):
        """Test command execution lifecycle."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        session = Session(user_id=user.id, device_id="device123", device_type="web")
        test_session.add(session)
        await test_session.flush()

        command = Command(
            session_id=session.id, command="echo 'hello'", status="pending"
        )
        test_session.add(command)
        await test_session.commit()

        # Start execution
        command.start_execution()
        assert command.status == "running"
        assert command.started_at is not None

        # Complete execution
        command.complete_execution(exit_code=0, output="hello\n", error_output=None)
        assert command.status == "success"
        assert command.exit_code == 0
        assert command.output == "hello\n"
        assert command.completed_at is not None
        assert command.execution_time is not None
        assert command.is_successful is True

    async def test_command_classification(self, test_session):
        """Test command classification."""
        command = Command(session_id="session_id", command="git status")

        command_type = command.classify_command()
        assert command_type == "git"

        command.command = "ls -la"
        command_type = command.classify_command()
        assert command_type == "file_operation"

        command.command = "ping google.com"
        command_type = command.classify_command()
        assert command_type == "network"

    async def test_command_sensitive_detection(self, test_session):
        """Test sensitive command detection."""
        sensitive_command = Command(
            session_id="session_id", command="export PASSWORD=secret123"
        )

        assert sensitive_command.check_sensitive_content() is True

        normal_command = Command(session_id="session_id", command="ls -la")

        assert normal_command.check_sensitive_content() is False


@pytest.mark.database
@pytest.mark.unit
class TestSyncDataModel:
    """Test SyncData model functionality."""

    async def test_sync_data_creation(self, test_session):
        """Test sync data creation."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        sync_data = SyncData.create_sync_item(
            user_id=user.id,
            sync_type="commands",
            sync_key="commands_session_123",
            data={"commands": ["ls", "pwd"]},
            device_id="device123",
            device_type="ios",
        )
        test_session.add(sync_data)
        await test_session.commit()

        assert sync_data.id is not None
        assert sync_data.sync_type == "commands"
        assert sync_data.version == 1
        assert sync_data.is_deleted is False
        assert sync_data.data == {"commands": ["ls", "pwd"]}

    async def test_sync_data_update(self, test_session):
        """Test sync data update."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        sync_data = SyncData.create_sync_item(
            user_id=user.id,
            sync_type="settings",
            sync_key="user_settings",
            data={"theme": "dark"},
            device_id="device123",
            device_type="ios",
        )
        test_session.add(sync_data)
        await test_session.commit()

        initial_version = sync_data.version
        sync_data.update_data(
            new_data={"theme": "light"},
            device_id="device456",
            device_type="android",
        )

        assert sync_data.version == initial_version + 1
        assert sync_data.data == {"theme": "light"}
        assert sync_data.source_device_id == "device456"
        assert sync_data.source_device_type == "android"

    async def test_sync_data_conflict_handling(self, test_session):
        """Test sync data conflict handling."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        sync_data = SyncData.create_sync_item(
            user_id=user.id,
            sync_type="settings",
            sync_key="user_settings",
            data={"theme": "dark"},
            device_id="device123",
            device_type="ios",
        )
        test_session.add(sync_data)
        await test_session.commit()

        # Create conflict
        conflicting_data = {"theme": "light"}
        sync_data.create_conflict(conflicting_data)

        assert sync_data.has_conflict is True
        assert sync_data.conflict_data is not None
        assert "current_data" in sync_data.conflict_data
        assert "conflicting_data" in sync_data.conflict_data

        # Resolve conflict
        sync_data.resolve_conflict(
            chosen_data=conflicting_data,
            device_id="device456",
            device_type="web",
        )

        assert sync_data.has_conflict is False
        assert sync_data.conflict_data is None
        assert sync_data.resolved_at is not None
        assert sync_data.data == conflicting_data

    async def test_sync_data_deletion(self, test_session):
        """Test sync data deletion."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        sync_data = SyncData.create_sync_item(
            user_id=user.id,
            sync_type="ssh_profiles",
            sync_key="profile_123",
            data={"name": "Test Server"},
            device_id="device123",
            device_type="ios",
        )
        test_session.add(sync_data)
        await test_session.commit()

        initial_version = sync_data.version
        sync_data.mark_as_deleted("device456", "android")

        assert sync_data.is_deleted is True
        assert sync_data.version == initial_version + 1
        assert sync_data.source_device_id == "device456"
        assert sync_data.source_device_type == "android"


@pytest.mark.database
@pytest.mark.unit
class TestModelRelationships:
    """Test relationships between models."""

    async def test_user_cascade_deletion(self, test_session):
        """Test that related objects are deleted when user is deleted."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        # Create related objects
        session = Session(user_id=user.id, device_id="device123", device_type="web")
        ssh_profile = SSHProfile(
            user_id=user.id,
            name="Test Server",
            host="example.com",
            username="testuser",
        )
        ssh_key = SSHKey(
            user_id=user.id,
            name="Test Key",
            key_type="rsa",
            fingerprint="abc123",
            encrypted_private_key=b"key",
            public_key="ssh-rsa ...",
        )
        sync_data = SyncData(
            user_id=user.id,
            sync_type="settings",
            sync_key="test",
            data={"test": "data"},
            source_device_id="test_device_123",
            source_device_type="web",
        )

        test_session.add_all([session, ssh_profile, ssh_key, sync_data])
        await test_session.commit()

        user_id = user.id

        # Delete user
        await test_session.delete(user)
        await test_session.commit()

        # Check that related objects are also deleted
        result = await test_session.execute(
            select(Session).where(Session.user_id == user_id)
        )
        assert result.scalar_one_or_none() is None

        result = await test_session.execute(
            select(SSHProfile).where(SSHProfile.user_id == user_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_session_command_relationship(self, test_session):
        """Test session-command relationship."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        session = Session(user_id=user.id, device_id="device123", device_type="web")
        test_session.add(session)
        await test_session.flush()

        command = Command(session_id=session.id, command="ls -la")
        test_session.add(command)
        await test_session.commit()

        # Test relationships
        await test_session.refresh(session, ["commands"])
        await test_session.refresh(command, ["session"])

        assert len(session.commands) == 1
        assert session.commands[0].command == "ls -la"
        assert command.session.id == session.id
        assert command.user_id == user.id  # Through relationship

    async def test_ssh_profile_key_relationship(self, test_session):
        """Test SSH profile and key relationship."""
        user = User(email="test@example.com", username="testuser", password_hash="hash")
        test_session.add(user)
        await test_session.flush()

        ssh_key = SSHKey(
            user_id=user.id,
            name="Test Key",
            key_type="rsa",
            fingerprint="abc123",
            encrypted_private_key=b"key",
            public_key="ssh-rsa ...",
        )
        test_session.add(ssh_key)
        await test_session.flush()

        ssh_profile = SSHProfile(
            user_id=user.id,
            name="Test Server",
            host="example.com",
            username="testuser",
            ssh_key_id=ssh_key.id,
        )
        test_session.add(ssh_profile)
        await test_session.commit()

        # Test relationships
        await test_session.refresh(ssh_key, ["profiles"])
        await test_session.refresh(ssh_profile, ["ssh_key"])

        assert len(ssh_key.profiles) == 1
        assert ssh_key.profiles[0].name == "Test Server"
        assert ssh_profile.ssh_key.name == "Test Key"
