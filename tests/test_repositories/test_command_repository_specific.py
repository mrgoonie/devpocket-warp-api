"""
Specific tests for Command repository methods to improve coverage.

This module focuses on testing the CommandRepository-specific methods
that are not covered by the base repository tests.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.models.command import Command
from app.models.session import Session
from app.models.user import User
from app.repositories.command import CommandRepository


@pytest.mark.database
class TestCommandRepositorySpecific:
    """Test CommandRepository-specific methods."""

    @pytest.fixture
    def command_repository(self, test_session):
        """Create command repository instance."""
        return CommandRepository(test_session)

    @pytest.fixture
    async def test_user(self, test_session):
        """Create a test user."""
        user = User(
            username="testuser",
            email="test@example.com", 
            full_name="Test User",
            hashed_password="hashed_password_123"
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        return user

    @pytest.fixture
    async def test_session_obj(self, test_session, test_user):
        """Create a test session."""
        session = Session(
            user_id=test_user.id,
            session_name="test_session",
            shell="/bin/bash",
            environment="test"
        )
        test_session.add(session)
        await test_session.commit()
        await test_session.refresh(session)
        return session

    @pytest.fixture
    async def sample_command(self, test_session, test_session_obj):
        """Create a sample command."""
        command = Command(
            session_id=test_session_obj.id,
            command="ls -la",
            working_directory="/home/user",
            status="pending"
        )
        test_session.add(command)
        await test_session.commit()
        await test_session.refresh(command)
        return command

    @pytest.mark.asyncio
    async def test_create_command_method(self, command_repository, test_session_obj):
        """Test the create_command method specifically."""
        command = await command_repository.create_command(
            session_id=test_session_obj.id,
            command="echo hello"
        )
        
        assert command.command == "echo hello"
        assert command.session_id == test_session_obj.id
        assert command.status == "pending"
        assert command.id is not None

    @pytest.mark.asyncio
    async def test_create_command_with_kwargs(self, command_repository, test_session_obj):
        """Test create_command with additional parameters."""
        command = await command_repository.create_command(
            session_id=test_session_obj.id,
            command="cat file.txt",
            working_directory="/home/user",
            priority=5
        )
        
        assert command.working_directory == "/home/user"
        assert command.priority == 5

    @pytest.mark.asyncio
    async def test_get_session_commands(self, command_repository, test_session_obj, sample_command):
        """Test getting commands for a session."""
        commands = await command_repository.get_session_commands(test_session_obj.id)
        assert len(commands) >= 1
        assert commands[0].session_id == test_session_obj.id

    @pytest.mark.asyncio
    async def test_get_session_commands_with_status_filter(self, command_repository, test_session_obj):
        """Test getting commands with status filter."""
        # Create command with specific status
        command_data = {
            "session_id": test_session_obj.id,
            "command": "test command",
            "status": "success"
        }
        await command_repository.create(command_data)
        
        success_commands = await command_repository.get_session_commands(
            test_session_obj.id, status_filter="success"
        )
        assert len(success_commands) >= 1
        for cmd in success_commands:
            assert cmd.status == "success"

    @pytest.mark.asyncio
    async def test_get_session_commands_pagination(self, command_repository, test_session_obj):
        """Test pagination for session commands."""
        # Create multiple commands
        for i in range(3):
            command_data = {
                "session_id": test_session_obj.id,
                "command": f"command_{i}",
                "status": "pending"
            }
            await command_repository.create(command_data)
        
        page1 = await command_repository.get_session_commands(
            test_session_obj.id, offset=0, limit=2
        )
        page2 = await command_repository.get_session_commands(
            test_session_obj.id, offset=2, limit=2
        )
        
        assert len(page1) == 2
        assert len(page2) >= 1

    @pytest.mark.asyncio
    async def test_get_user_command_history(self, command_repository, test_user, sample_command):
        """Test getting user command history."""
        commands = await command_repository.get_user_command_history(str(test_user.id))
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_get_user_command_history_with_search(self, command_repository, test_user, test_session_obj):
        """Test searching user command history."""
        # Create command with searchable term
        command_data = {
            "session_id": test_session_obj.id,
            "command": "docker ps",
            "status": "pending"
        }
        await command_repository.create(command_data)
        
        commands = await command_repository.get_user_command_history(
            str(test_user.id), search_term="docker"
        )
        assert len(commands) >= 1
        for cmd in commands:
            assert "docker" in cmd.command.lower()

    @pytest.mark.asyncio
    async def test_get_commands_by_status(self, command_repository, test_session_obj):
        """Test getting commands by status."""
        # Create command with specific status
        command_data = {
            "session_id": test_session_obj.id,
            "command": "running command",
            "status": "running"
        }
        await command_repository.create(command_data)
        
        running_commands = await command_repository.get_commands_by_status("running")
        assert len(running_commands) >= 1
        for cmd in running_commands:
            assert cmd.status == "running"

    @pytest.mark.asyncio
    async def test_get_commands_by_status_with_user_filter(self, command_repository, test_user, test_session_obj):
        """Test getting commands by status filtered by user."""
        command_data = {
            "session_id": test_session_obj.id,
            "command": "user command",
            "status": "success"
        }
        await command_repository.create(command_data)
        
        commands = await command_repository.get_commands_by_status(
            "success", user_id=str(test_user.id)
        )
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_get_running_commands(self, command_repository, test_session_obj):
        """Test getting running commands."""
        command_data = {
            "session_id": test_session_obj.id,
            "command": "sleep 60",
            "status": "running"
        }
        await command_repository.create(command_data)
        
        running_commands = await command_repository.get_running_commands()
        assert len(running_commands) >= 1

    @pytest.mark.asyncio
    async def test_get_running_commands_by_session(self, command_repository, test_session_obj):
        """Test getting running commands for specific session."""
        command_data = {
            "session_id": test_session_obj.id,
            "command": "long running task",
            "status": "running"
        }
        await command_repository.create(command_data)
        
        running_commands = await command_repository.get_running_commands(
            session_id=test_session_obj.id
        )
        assert len(running_commands) >= 1
        for cmd in running_commands:
            assert cmd.session_id == test_session_obj.id

    @pytest.mark.asyncio
    async def test_get_running_commands_by_user(self, command_repository, test_user, test_session_obj):
        """Test getting running commands for specific user."""
        command_data = {
            "session_id": test_session_obj.id,
            "command": "user running task",
            "status": "running"
        }
        await command_repository.create(command_data)
        
        running_commands = await command_repository.get_running_commands(
            user_id=str(test_user.id)
        )
        assert len(running_commands) >= 1

    @pytest.mark.asyncio
    async def test_start_command_execution(self, command_repository, sample_command):
        """Test starting command execution."""
        updated_command = await command_repository.start_command_execution(sample_command.id)
        
        assert updated_command is not None
        assert updated_command.status == "running"
        assert updated_command.started_at is not None

    @pytest.mark.asyncio
    async def test_start_command_execution_not_found(self, command_repository):
        """Test starting execution for non-existent command."""
        result = await command_repository.start_command_execution("non-existent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_complete_command_execution(self, command_repository, sample_command):
        """Test completing command execution."""
        # First start the command
        await command_repository.start_command_execution(sample_command.id)
        
        # Then complete it
        updated_command = await command_repository.complete_command_execution(
            sample_command.id,
            exit_code=0,
            output="hello\\n"
        )
        
        assert updated_command is not None
        assert updated_command.status == "success"
        assert updated_command.exit_code == 0
        assert updated_command.output == "hello\\n"

    @pytest.mark.asyncio
    async def test_complete_command_execution_with_error(self, command_repository, sample_command):
        """Test completing command execution with error."""
        await command_repository.start_command_execution(sample_command.id)
        
        updated_command = await command_repository.complete_command_execution(
            sample_command.id,
            exit_code=1,
            error_output="command failed"
        )
        
        assert updated_command.status == "error"
        assert updated_command.exit_code == 1
        assert updated_command.error_output == "command failed"

    @pytest.mark.asyncio
    async def test_cancel_command(self, command_repository, sample_command):
        """Test cancelling a command."""
        await command_repository.start_command_execution(sample_command.id)
        
        cancelled_command = await command_repository.cancel_command(sample_command.id)
        
        assert cancelled_command is not None
        assert cancelled_command.status == "cancelled"

    @pytest.mark.asyncio
    async def test_timeout_command(self, command_repository, sample_command):
        """Test timing out a command."""
        await command_repository.start_command_execution(sample_command.id)
        
        timed_out_command = await command_repository.timeout_command(sample_command.id)
        
        assert timed_out_command is not None
        assert timed_out_command.status == "timeout"

    @pytest.mark.asyncio
    async def test_search_commands_basic(self, command_repository, test_user, sample_command):
        """Test basic command search."""
        commands = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)}
        )
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_search_commands_with_query(self, command_repository, test_user, test_session_obj):
        """Test command search with query."""
        command_data = {
            "session_id": test_session_obj.id,
            "command": "unique_search_term_xyz",
            "status": "pending"
        }
        await command_repository.create(command_data)
        
        commands = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)},
            query="unique_search_term_xyz"
        )
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_search_commands_date_range(self, command_repository, test_user, sample_command):
        """Test command search with date range."""
        hour_ago = datetime.now() - timedelta(hours=1)
        
        commands = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)},
            executed_after=hour_ago
        )
        # Should find our recent sample command
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_search_commands_sorting(self, command_repository, test_user, test_session_obj):
        """Test command search with sorting."""
        # Create multiple commands
        for i in range(3):
            command_data = {
                "session_id": test_session_obj.id,
                "command": f"sort_test_{i}",
                "status": "pending"
            }
            await command_repository.create(command_data)
        
        commands_desc = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)},
            sort_by="created_at",
            sort_order="desc"
        )
        
        commands_asc = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)},
            sort_by="created_at",
            sort_order="asc"
        )
        
        assert len(commands_desc) >= 3
        assert len(commands_asc) >= 3
        # Check that order is different
        if len(commands_desc) > 1 and len(commands_asc) > 1:
            assert commands_desc[0].id != commands_asc[0].id

    @pytest.mark.asyncio
    async def test_get_user_commands_with_session(self, command_repository, test_user, sample_command):
        """Test getting user commands with session info."""
        commands = await command_repository.get_user_commands_with_session(
            test_user.id, include_session_info=True
        )
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_count_user_commands(self, command_repository, test_user, sample_command):
        """Test counting user commands."""
        count = await command_repository.count_user_commands(test_user.id)
        assert count >= 1

    @pytest.mark.asyncio
    async def test_count_commands_with_criteria(self, command_repository, test_user, test_session_obj):
        """Test counting commands with criteria."""
        command_data = {
            "session_id": test_session_obj.id,
            "command": "criteria test",
            "status": "success"
        }
        await command_repository.create(command_data)
        
        count = await command_repository.count_commands_with_criteria({
            "user_id": str(test_user.id),
            "status": "success"
        })
        assert count >= 1

    @pytest.mark.asyncio
    async def test_get_user_commands(self, command_repository, test_user, sample_command):
        """Test getting all user commands."""
        commands = await command_repository.get_user_commands(test_user.id)
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_get_session_command_stats(self, command_repository, test_user, sample_command):
        """Test getting command statistics by session."""
        stats = await command_repository.get_session_command_stats(test_user.id)
        assert len(stats) >= 1
        for stat in stats:
            assert "session_id" in stat
            assert "command_count" in stat

    @pytest.mark.asyncio
    async def test_get_user_commands_since(self, command_repository, test_user, sample_command):
        """Test getting user commands since a date."""
        hour_ago = datetime.now() - timedelta(hours=1)
        commands = await command_repository.get_user_commands_since(test_user.id, hour_ago)
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_get_user_recent_commands(self, command_repository, test_user, sample_command):
        """Test getting recent user commands."""
        commands = await command_repository.get_user_recent_commands(test_user.id)
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_get_failed_commands(self, command_repository, test_user, test_session_obj):
        """Test getting failed commands."""
        command_data = {
            "session_id": test_session_obj.id,
            "command": "failed command",
            "status": "error",
            "exit_code": 1
        }
        await command_repository.create(command_data)
        
        failed_commands = await command_repository.get_failed_commands(
            user_id=str(test_user.id)
        )
        assert len(failed_commands) >= 1

    @pytest.mark.asyncio
    async def test_get_command_stats(self, command_repository, test_user, sample_command):
        """Test getting command statistics."""
        stats = await command_repository.get_command_stats(user_id=str(test_user.id))
        
        assert "total_commands" in stats
        assert "status_breakdown" in stats
        assert stats["total_commands"] >= 1

    @pytest.mark.asyncio
    async def test_get_top_commands(self, command_repository, test_user, sample_command):
        """Test getting top commands."""
        top_commands = await command_repository.get_top_commands(
            user_id=str(test_user.id)
        )
        
        assert len(top_commands) >= 1
        for cmd_data in top_commands:
            assert "command" in cmd_data
            assert "usage_count" in cmd_data

    @pytest.mark.asyncio
    async def test_cleanup_old_commands(self, command_repository, test_session):
        """Test cleaning up old commands."""
        # Create an old command
        old_command = Command(
            session_id=str(uuid4()),
            command="old command"
        )
        old_command.created_at = datetime.now() - timedelta(days=100)
        
        test_session.add(old_command)
        await test_session.commit()
        
        deleted_count = await command_repository.cleanup_old_commands(days_old=90)
        assert deleted_count >= 1

    @pytest.mark.asyncio
    async def test_get_recent_commands(self, command_repository, test_user, sample_command):
        """Test getting recent commands."""
        recent_commands = await command_repository.get_recent_commands(
            str(test_user.id), hours=24
        )
        assert len(recent_commands) >= 1

    @pytest.mark.asyncio
    async def test_get_ai_suggested_commands(self, command_repository, test_user, test_session_obj):
        """Test getting AI-suggested commands."""
        command_data = {
            "session_id": test_session_obj.id,
            "command": "ai suggested command",
            "was_ai_suggested": True
        }
        await command_repository.create(command_data)
        
        ai_commands = await command_repository.get_ai_suggested_commands(
            user_id=str(test_user.id)
        )
        assert len(ai_commands) >= 1
        for cmd in ai_commands:
            assert cmd.was_ai_suggested is True

    @pytest.mark.asyncio
    async def test_get_commands_by_type(self, command_repository, test_user, test_session_obj):
        """Test getting commands by type."""
        command_data = {
            "session_id": test_session_obj.id,
            "command": "ls -la",
            "command_type": "list"
        }
        command = await command_repository.create(command_data)
        
        if command.command_type:
            commands = await command_repository.get_commands_by_type(
                command.command_type, user_id=str(test_user.id)
            )
            assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_error_handling_methods(self, command_repository):
        """Test error handling for various methods."""
        # Test with non-existent IDs
        result = await command_repository.complete_command_execution(
            "non-existent", exit_code=0
        )
        assert result is None
        
        result = await command_repository.cancel_command("non-existent")
        assert result is None
        
        result = await command_repository.timeout_command("non-existent")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_commands_edge_cases(self, command_repository):
        """Test search with edge cases."""
        # Empty criteria
        commands = await command_repository.search_commands()
        assert isinstance(commands, list)
        
        # Non-existent user
        commands = await command_repository.search_commands(
            criteria={"user_id": "non-existent"}
        )
        assert commands == []

    @pytest.mark.asyncio
    async def test_pagination_edge_cases(self, command_repository, test_session_obj):
        """Test pagination edge cases."""
        # Large offset
        commands = await command_repository.get_session_commands(
            test_session_obj.id, offset=1000, limit=10
        )
        assert isinstance(commands, list)
        
        # Zero limit
        commands = await command_repository.get_session_commands(
            test_session_obj.id, offset=0, limit=0
        )
        assert len(commands) == 0