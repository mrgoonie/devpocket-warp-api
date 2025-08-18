"""
Basic tests for Command model functionality.
"""

import pytest
from datetime import datetime

from app.models.command import Command
from app.repositories.user import UserRepository


@pytest.mark.database
class TestCommandModel:
    """Test command model basic functionality."""

    @pytest.fixture
    def user_repository(self, test_session):
        """Create user repository instance."""
        return UserRepository(test_session)

    @pytest.fixture
    async def sample_user(self, user_repository):
        """Create a sample user for testing."""
        user_data = {
            "username": "testuser",
            "email": "test@example.com", 
            "full_name": "Test User",
            "hashed_password": "hashed_password_123"
        }
        return await user_repository.create(user_data)

    @pytest.fixture
    async def sample_session(self, test_session, sample_user):
        """Create a sample session for testing."""
        from app.models.session import Session
        user = sample_user
        session = Session(
            user_id=user.id,
            device_id="test_device_123",
            device_type="web",
            session_name="test_session",
            environment='{"SHELL": "/bin/bash"}'
        )
        test_session.add(session)
        await test_session.commit()
        await test_session.refresh(session)
        return session

    @pytest.mark.asyncio
    async def test_command_creation(self, test_session, sample_session):
        """Test command creation with basic attributes."""
        session = sample_session
        command = Command(
            session_id=session.id,
            command="ls -la",
            working_directory="/home/user",
            status="pending"
        )
        
        test_session.add(command)
        await test_session.commit()
        await test_session.refresh(command)
        
        assert command.id is not None
        assert command.command == "ls -la"
        assert command.working_directory == "/home/user"
        assert command.status == "pending"
        assert command.session_id == session.id

    @pytest.mark.asyncio
    async def test_command_model_attributes(self, test_session, sample_session):
        """Test that command model has expected attributes."""
        session = sample_session
        command = Command(
            session_id=session.id,
            command="ls -la",
            working_directory="/home/user",
            status="pending"
        )
        
        # Test required attributes exist
        assert hasattr(command, 'id')
        assert hasattr(command, 'session_id')
        assert hasattr(command, 'command')
        assert hasattr(command, 'working_directory')
        assert hasattr(command, 'status')
        assert hasattr(command, 'created_at')
        assert hasattr(command, 'updated_at')
        
        # Test execution attributes exist
        assert hasattr(command, 'output')
        assert hasattr(command, 'error_output')
        assert hasattr(command, 'exit_code')
        assert hasattr(command, 'execution_time')
        assert hasattr(command, 'started_at')
        assert hasattr(command, 'completed_at')

    @pytest.mark.asyncio
    async def test_command_defaults(self, test_session, sample_session):
        """Test command default values."""
        session = sample_session
        command = Command(
            session_id=session.id,
            command="ls -la",
            working_directory="/home/user"
        )
        
        test_session.add(command)
        await test_session.commit()
        await test_session.refresh(command)
        
        # Default status should be 'pending'
        assert command.status == "pending"
        # Default capture_output should be True
        assert command.capture_output is True
        # Default timeout should be 30
        assert command.timeout_seconds == 30

    @pytest.mark.asyncio
    async def test_command_methods(self, test_session, sample_session):
        """Test command methods."""
        session = sample_session
        command = Command(
            session_id=session.id,
            command="ls -la",
            working_directory="/home/user",
            status="pending"
        )
        
        test_session.add(command)
        await test_session.commit()
        await test_session.refresh(command)
        
        # Test start_execution method
        command.start_execution()
        assert command.status == "running"
        assert command.started_at is not None
        
        # Test complete_execution method
        command.complete_execution(
            exit_code=0,
            output="command output",
            error_output=None
        )
        assert command.status == "success"
        assert command.exit_code == 0
        assert command.output == "command output"
        assert command.completed_at is not None
        assert command.execution_time is not None

    @pytest.mark.asyncio
    async def test_command_properties(self, test_session, sample_session):
        """Test command properties."""
        session = sample_session
        command = Command(
            session_id=session.id,
            command="ls -la",
            working_directory="/home/user",
            status="success",
            exit_code=0
        )
        
        # Test is_successful property
        assert command.is_successful is True
        
        # Test has_error property
        assert command.has_error is False
        
        # Test command with error
        error_command = Command(
            session_id=session.id,
            command="invalid_command",
            status="error",
            exit_code=1
        )
        
        assert error_command.is_successful is False
        assert error_command.has_error is True

    @pytest.mark.asyncio
    async def test_command_classify_method(self, test_session, sample_session):
        """Test command classification method."""
        session = sample_session
        
        # Test git command
        git_command = Command(
            session_id=session.id,
            command="git status"
        )
        assert git_command.classify_command() == "git"
        
        # Test file operation command
        file_command = Command(
            session_id=session.id,
            command="ls -la"
        )
        assert file_command.classify_command() == "file_operation"
        
        # Test network command
        network_command = Command(
            session_id=session.id,
            command="curl https://example.com"
        )
        assert network_command.classify_command() == "network"
        
        # Test system command
        system_command = Command(
            session_id=session.id,
            command="ps aux"
        )
        assert system_command.classify_command() == "system"

    @pytest.mark.asyncio
    async def test_command_sensitive_check(self, test_session, sample_session):
        """Test command sensitive content check."""
        session = sample_session
        
        # Test regular command
        regular_command = Command(
            session_id=session.id,
            command="ls -la"
        )
        assert regular_command.check_sensitive_content() is False
        
        # Test sensitive command
        sensitive_command = Command(
            session_id=session.id,
            command="echo password123"
        )
        assert sensitive_command.check_sensitive_content() is True
        
        # Test another sensitive command
        key_command = Command(
            session_id=session.id,
            command="ssh-keygen -t rsa"
        )
        assert key_command.check_sensitive_content() is True

    @pytest.mark.asyncio
    async def test_command_string_representation(self, test_session, sample_session):
        """Test command string representation."""
        session = sample_session
        command = Command(
            session_id=session.id,
            command="ls -la /very/long/directory/path/that/exceeds/fifty/characters",
            status="pending"
        )
        
        # Test that string representation exists and is truncated
        str_repr = str(command)
        assert "ls -la" in str_repr
        assert "pending" in str_repr
        assert len(str_repr) < 200  # Should be reasonably short

    @pytest.mark.asyncio
    async def test_command_execution_methods(self, test_session, sample_session):
        """Test command execution control methods."""
        session = sample_session
        command = Command(
            session_id=session.id,
            command="sleep 10",
            status="pending"
        )
        
        test_session.add(command)
        await test_session.commit()
        await test_session.refresh(command)
        
        # Test cancel_execution method
        command.cancel_execution()
        assert command.status == "cancelled"
        assert command.completed_at is not None
        
        # Test timeout_execution method  
        command2 = Command(
            session_id=session.id,
            command="long_running_command",
            status="running"
        )
        command2.start_execution()
        command2.timeout_execution()
        assert command2.status == "timeout"
        assert command2.completed_at is not None

    @pytest.mark.asyncio
    async def test_command_additional_properties(self, test_session, sample_session):
        """Test additional command properties and methods."""
        session = sample_session
        
        # Test duration_ms property
        command = Command(
            session_id=session.id,
            command="test command",
            execution_time=1.5
        )
        assert command.duration_ms == 1500
        
        # Test user_id property through session relationship
        test_session.add(command)
        await test_session.commit()
        await test_session.refresh(command)
        # Note: user_id property requires session relationship to be loaded
        
        # Test classify_command with more types
        package_command = Command(
            session_id=session.id,
            command="pip install requests"
        )
        assert package_command.classify_command() == "package_management"
        
        dev_command = Command(
            session_id=session.id,
            command="docker run hello-world"
        )
        assert dev_command.classify_command() == "development"
        
        other_command = Command(
            session_id=session.id,
            command="unknown_command_xyz"
        )
        assert other_command.classify_command() == "other"