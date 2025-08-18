"""
Tests for Command repository functionality.

Basic tests to improve coverage for command repository operations.
"""

import pytest

from app.models.command import Command
from app.repositories.command import CommandRepository
from app.repositories.user import UserRepository


@pytest.mark.database
class TestCommandRepository:
    """Test command repository operations."""

    @pytest.fixture
    def command_repository(self, test_session):
        """Create command repository instance."""
        return CommandRepository(test_session)

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
        session = Session(
            user_id=sample_user.id,
            session_name="test_session",
            shell="/bin/bash",
            environment="test"
        )
        test_session.add(session)
        await test_session.commit()
        await test_session.refresh(session)
        return session

    @pytest.fixture
    def sample_command_data(self, sample_session):
        """Sample command data for testing."""
        return {
            "session_id": sample_session.id,
            "command": "ls -la",
            "working_directory": "/home/user",
            "status": "pending"
        }

    @pytest.mark.asyncio
    async def test_create_command_success(self, command_repository, sample_command_data):
        """Test successful command creation."""
        command = await command_repository.create(sample_command_data)
        
        assert command.command == "ls -la"
        assert command.working_directory == "/home/user"
        assert command.status == "pending"
        assert command.id is not None

    @pytest.mark.asyncio
    async def test_get_command_by_id(self, command_repository, sample_command_data):
        """Test getting command by ID."""
        # Create command first
        created_command = await command_repository.create(sample_command_data)
        
        # Get command by ID
        fetched_command = await command_repository.get_by_id(created_command.id)
        
        assert fetched_command is not None
        assert fetched_command.id == created_command.id
        assert fetched_command.command == "ls -la"

    @pytest.mark.asyncio
    async def test_get_command_by_id_not_found(self, command_repository):
        """Test getting command by non-existent ID."""
        command = await command_repository.get_by_id(99999)
        assert command is None

    @pytest.mark.asyncio
    async def test_update_command_status(self, command_repository, sample_command_data):
        """Test updating command status."""
        # Create command first
        command = await command_repository.create(sample_command_data)
        
        # Update status
        update_data = {
            "status": "success",
            "exit_code": 0,
            "output": "command output"
        }
        updated_command = await command_repository.update(command.id, update_data)
        
        assert updated_command.status == "success"
        assert updated_command.exit_code == 0
        assert updated_command.output == "command output"

    @pytest.mark.asyncio
    async def test_update_command_not_found(self, command_repository):
        """Test updating non-existent command."""
        update_data = {"status": "success"}
        updated_command = await command_repository.update(99999, update_data)
        assert updated_command is None

    @pytest.mark.asyncio
    async def test_delete_command(self, command_repository, sample_command_data):
        """Test deleting command."""
        # Create command first
        command = await command_repository.create(sample_command_data)
        command_id = command.id
        
        # Delete command
        result = await command_repository.delete(command_id)
        assert result is True
        
        # Verify command is deleted
        deleted_command = await command_repository.get_by_id(command_id)
        assert deleted_command is None

    @pytest.mark.asyncio
    async def test_delete_command_not_found(self, command_repository):
        """Test deleting non-existent command."""
        result = await command_repository.delete(99999)
        assert result is False

    @pytest.mark.asyncio
    async def test_list_session_commands(self, command_repository, sample_session):
        """Test listing commands for a session."""
        # Create multiple commands for the session
        for i in range(3):
            command_data = {
                "session_id": sample_session.id,
                "command": f"command_{i}",
                "working_directory": "/home/user",
                "status": "pending"
            }
            await command_repository.create(command_data)
        
        # List commands - assuming the repository has a list method
        commands = await command_repository.list(limit=2)
        
        assert len(commands) == 2
        # Should be ordered by created_at desc (most recent first)
        assert commands[0].command == "command_2"
        assert commands[1].command == "command_1"

    @pytest.mark.asyncio
    async def test_count_commands(self, command_repository, sample_session):
        """Test counting commands."""
        initial_count = await command_repository.count()
        
        # Create a command
        command_data = {
            "session_id": sample_session.id,
            "command": "test command",
            "working_directory": "/home/user",
            "status": "pending"
        }
        await command_repository.create(command_data)
        
        # Count should increase by 1
        new_count = await command_repository.count()
        assert new_count == initial_count + 1

    @pytest.mark.asyncio
    async def test_command_model_attributes(self, command_repository, sample_command_data):
        """Test that command model has expected attributes."""
        command = await command_repository.create(sample_command_data)
        
        # Test required attributes
        assert hasattr(command, 'id')
        assert hasattr(command, 'session_id')
        assert hasattr(command, 'command')
        assert hasattr(command, 'working_directory')
        assert hasattr(command, 'status')
        assert hasattr(command, 'created_at')
        assert hasattr(command, 'updated_at')
        
        # Test optional attributes
        assert hasattr(command, 'output')
        assert hasattr(command, 'error_output')
        assert hasattr(command, 'exit_code')
        assert hasattr(command, 'execution_time')
        
        # Test that timestamps are set
        assert command.created_at is not None
        assert command.updated_at is not None