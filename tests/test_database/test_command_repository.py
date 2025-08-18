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

    # Additional CommandRepository-specific method tests
    @pytest.mark.asyncio
    async def test_create_command_method(self, command_repository, sample_session):
        """Test the create_command method specifically."""
        command = await command_repository.create_command(
            session_id=sample_session.id,
            command="echo hello"
        )
        
        assert command.command == "echo hello"
        assert command.session_id == sample_session.id
        assert command.status == "pending"
        assert command.id is not None

    @pytest.mark.asyncio
    async def test_get_session_commands_basic(self, command_repository, sample_session):
        """Test getting commands for a session."""
        # Create test commands
        await command_repository.create_command(
            session_id=sample_session.id,
            command="ls"
        )
        await command_repository.create_command(
            session_id=sample_session.id,
            command="pwd"
        )
        
        commands = await command_repository.get_session_commands(sample_session.id)
        assert len(commands) >= 2
        for cmd in commands:
            assert cmd.session_id == sample_session.id

    @pytest.mark.asyncio
    async def test_get_session_commands_with_status_filter(self, command_repository, sample_session):
        """Test getting commands with status filter."""
        # Create commands with different statuses
        command_data_1 = {
            "session_id": sample_session.id,
            "command": "success cmd",
            "status": "success"
        }
        command_data_2 = {
            "session_id": sample_session.id,
            "command": "error cmd",
            "status": "error"
        }
        await command_repository.create(command_data_1)
        await command_repository.create(command_data_2)
        
        success_commands = await command_repository.get_session_commands(
            sample_session.id, status_filter="success"
        )
        assert len(success_commands) >= 1
        for cmd in success_commands:
            assert cmd.status == "success"

    @pytest.mark.asyncio
    async def test_get_user_command_history(self, command_repository, sample_user, sample_session):
        """Test getting user command history."""
        await command_repository.create_command(
            session_id=sample_session.id,
            command="history_command"
        )
        
        commands = await command_repository.get_user_command_history(str(sample_user.id))
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_get_commands_by_status(self, command_repository, sample_session):
        """Test getting commands by status."""
        command_data = {
            "session_id": sample_session.id,
            "command": "running command",
            "status": "running"
        }
        await command_repository.create(command_data)
        
        running_commands = await command_repository.get_commands_by_status("running")
        assert len(running_commands) >= 1
        for cmd in running_commands:
            assert cmd.status == "running"

    @pytest.mark.asyncio
    async def test_get_running_commands(self, command_repository, sample_session):
        """Test getting running commands."""
        command_data = {
            "session_id": sample_session.id,
            "command": "sleep 60",
            "status": "running"
        }
        await command_repository.create(command_data)
        
        running_commands = await command_repository.get_running_commands()
        assert len(running_commands) >= 1

    @pytest.mark.asyncio
    async def test_start_command_execution(self, command_repository, sample_session):
        """Test starting command execution."""
        command = await command_repository.create_command(
            session_id=sample_session.id,
            command="echo hello"
        )
        
        updated_command = await command_repository.start_command_execution(command.id)
        assert updated_command is not None
        assert updated_command.status == "running"
        assert updated_command.started_at is not None

    @pytest.mark.asyncio
    async def test_complete_command_execution(self, command_repository, sample_session):
        """Test completing command execution."""
        command = await command_repository.create_command(
            session_id=sample_session.id,
            command="echo hello"
        )
        await command_repository.start_command_execution(command.id)
        
        updated_command = await command_repository.complete_command_execution(
            command.id,
            exit_code=0,
            output="hello\\n"
        )
        
        assert updated_command is not None
        assert updated_command.status == "success"
        assert updated_command.exit_code == 0
        assert updated_command.output == "hello\\n"

    @pytest.mark.asyncio
    async def test_cancel_command(self, command_repository, sample_session):
        """Test cancelling a command."""
        command = await command_repository.create_command(
            session_id=sample_session.id,
            command="sleep 60"
        )
        await command_repository.start_command_execution(command.id)
        
        cancelled_command = await command_repository.cancel_command(command.id)
        assert cancelled_command is not None
        assert cancelled_command.status == "cancelled"

    @pytest.mark.asyncio
    async def test_timeout_command(self, command_repository, sample_session):
        """Test timing out a command."""
        command = await command_repository.create_command(
            session_id=sample_session.id,
            command="sleep 60"
        )
        await command_repository.start_command_execution(command.id)
        
        timed_out_command = await command_repository.timeout_command(command.id)
        assert timed_out_command is not None
        assert timed_out_command.status == "timeout"

    @pytest.mark.asyncio
    async def test_search_commands_basic(self, command_repository, sample_user, sample_session):
        """Test basic command search."""
        await command_repository.create_command(
            session_id=sample_session.id,
            command="test search command"
        )
        
        commands = await command_repository.search_commands(
            criteria={"user_id": str(sample_user.id)}
        )
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_get_user_commands_with_session(self, command_repository, sample_user, sample_session):
        """Test getting user commands with session info."""
        await command_repository.create_command(
            session_id=sample_session.id,
            command="test command"
        )
        
        commands = await command_repository.get_user_commands_with_session(
            sample_user.id, include_session_info=True
        )
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_count_user_commands(self, command_repository, sample_user, sample_session):
        """Test counting user commands."""
        await command_repository.create_command(
            session_id=sample_session.id,
            command="count test"
        )
        
        count = await command_repository.count_user_commands(sample_user.id)
        assert count >= 1

    @pytest.mark.asyncio
    async def test_get_user_commands(self, command_repository, sample_user, sample_session):
        """Test getting all user commands."""
        await command_repository.create_command(
            session_id=sample_session.id,
            command="user command test"
        )
        
        commands = await command_repository.get_user_commands(sample_user.id)
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_get_session_command_stats(self, command_repository, sample_user, sample_session):
        """Test getting command stats by session."""
        await command_repository.create_command(
            session_id=sample_session.id,
            command="stats test"
        )
        
        stats = await command_repository.get_session_command_stats(sample_user.id)
        assert len(stats) >= 1
        for stat in stats:
            assert "session_id" in stat
            assert "command_count" in stat

    @pytest.mark.asyncio
    async def test_get_command_stats(self, command_repository, sample_user, sample_session):
        """Test getting command statistics."""
        await command_repository.create_command(
            session_id=sample_session.id,
            command="stats command"
        )
        
        stats = await command_repository.get_command_stats(user_id=str(sample_user.id))
        
        assert "total_commands" in stats
        assert "status_breakdown" in stats
        assert stats["total_commands"] >= 1

    @pytest.mark.asyncio
    async def test_get_top_commands(self, command_repository, sample_user, sample_session):
        """Test getting top commands."""
        await command_repository.create_command(
            session_id=sample_session.id,
            command="popular command"
        )
        
        top_commands = await command_repository.get_top_commands(
            user_id=str(sample_user.id)
        )
        
        assert len(top_commands) >= 1
        for cmd_data in top_commands:
            assert "command" in cmd_data
            assert "usage_count" in cmd_data

    @pytest.mark.asyncio
    async def test_get_recent_commands(self, command_repository, sample_user, sample_session):
        """Test getting recent commands."""
        await command_repository.create_command(
            session_id=sample_session.id,
            command="recent command test"
        )
        
        recent_commands = await command_repository.get_recent_commands(
            str(sample_user.id), hours=24
        )
        assert len(recent_commands) >= 1

    @pytest.mark.asyncio
    async def test_get_failed_commands(self, command_repository, sample_user, sample_session):
        """Test getting failed commands."""
        command_data = {
            "session_id": sample_session.id,
            "command": "failed command",
            "status": "error",
            "exit_code": 1
        }
        await command_repository.create(command_data)
        
        failed_commands = await command_repository.get_failed_commands(
            user_id=str(sample_user.id)
        )
        assert len(failed_commands) >= 1

    @pytest.mark.asyncio
    async def test_error_handling_methods(self, command_repository):
        """Test error handling for various methods."""
        # Test with non-existent IDs
        result = await command_repository.start_command_execution("non-existent-id")
        assert result is None
        
        result = await command_repository.complete_command_execution(
            "non-existent", exit_code=0
        )
        assert result is None
        
        result = await command_repository.cancel_command("non-existent")
        assert result is None
        
        result = await command_repository.timeout_command("non-existent")
        assert result is None