"""
Focused tests for Command repository functionality to improve coverage.

This module focuses on the most impactful test cases to drive coverage up quickly.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.models.command import Command
from app.models.session import Session
from app.models.user import User
from app.repositories.command import CommandRepository


@pytest.mark.database
class TestCommandRepositoryFocused:
    """Focused test suite for CommandRepository coverage improvement."""

    @pytest.fixture
    async def command_repository(self, test_session):
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

    @pytest.mark.asyncio
    async def test_create_command_basic(self, command_repository, test_session_obj):
        """Test basic command creation."""
        command = await command_repository.create_command(
            session_id=test_session_obj.id,
            command="ls -la"
        )
        
        assert command.command == "ls -la"
        assert command.session_id == test_session_obj.id
        assert command.status == "pending"
        assert command.id is not None

    @pytest.mark.asyncio
    async def test_create_command_with_params(self, command_repository, test_session_obj):
        """Test command creation with parameters."""
        command = await command_repository.create_command(
            session_id=test_session_obj.id,
            command="cat file.txt",
            working_directory="/home/user",
            priority=5
        )
        
        assert command.command == "cat file.txt"
        assert command.working_directory == "/home/user"
        assert command.priority == 5

    @pytest.mark.asyncio
    async def test_get_session_commands(self, command_repository, test_session_obj):
        """Test getting commands for a session."""
        # Create test commands
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="ls"
        )
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="pwd"
        )
        
        commands = await command_repository.get_session_commands(test_session_obj.id)
        assert len(commands) >= 2

    @pytest.mark.asyncio
    async def test_get_session_commands_with_status_filter(self, command_repository, test_session_obj):
        """Test getting commands with status filter."""
        # Create commands with different statuses
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="ls",
            status="success"
        )
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="pwd",
            status="error"
        )
        
        success_commands = await command_repository.get_session_commands(
            test_session_obj.id, status_filter="success"
        )
        assert len(success_commands) >= 1
        for cmd in success_commands:
            assert cmd.status == "success"

    @pytest.mark.asyncio
    async def test_get_user_command_history(self, command_repository, test_user, test_session_obj):
        """Test getting user command history."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="history_command"
        )
        
        commands = await command_repository.get_user_command_history(str(test_user.id))
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_get_user_command_history_with_search(self, command_repository, test_user, test_session_obj):
        """Test searching user command history."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="docker ps"
        )
        
        commands = await command_repository.get_user_command_history(
            str(test_user.id), search_term="docker"
        )
        assert len(commands) >= 1
        for cmd in commands:
            assert "docker" in cmd.command.lower()

    @pytest.mark.asyncio
    async def test_get_commands_by_status(self, command_repository, test_session_obj):
        """Test getting commands by status."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="running_command",
            status="running"
        )
        
        running_commands = await command_repository.get_commands_by_status("running")
        assert len(running_commands) >= 1
        for cmd in running_commands:
            assert cmd.status == "running"

    @pytest.mark.asyncio
    async def test_get_running_commands(self, command_repository, test_session_obj):
        """Test getting running commands."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="sleep 60",
            status="running"
        )
        
        running_commands = await command_repository.get_running_commands()
        assert len(running_commands) >= 1

    @pytest.mark.asyncio
    async def test_start_command_execution(self, command_repository, test_session_obj):
        """Test starting command execution."""
        command = await command_repository.create_command(
            session_id=test_session_obj.id,
            command="echo hello"
        )
        
        updated_command = await command_repository.start_command_execution(command.id)
        assert updated_command is not None
        assert updated_command.status == "running"
        assert updated_command.started_at is not None

    @pytest.mark.asyncio
    async def test_complete_command_execution(self, command_repository, test_session_obj):
        """Test completing command execution."""
        command = await command_repository.create_command(
            session_id=test_session_obj.id,
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
    async def test_cancel_command(self, command_repository, test_session_obj):
        """Test cancelling a command."""
        command = await command_repository.create_command(
            session_id=test_session_obj.id,
            command="sleep 60"
        )
        await command_repository.start_command_execution(command.id)
        
        cancelled_command = await command_repository.cancel_command(command.id)
        assert cancelled_command is not None
        assert cancelled_command.status == "cancelled"

    @pytest.mark.asyncio
    async def test_timeout_command(self, command_repository, test_session_obj):
        """Test timing out a command."""
        command = await command_repository.create_command(
            session_id=test_session_obj.id,
            command="sleep 60"
        )
        await command_repository.start_command_execution(command.id)
        
        timed_out_command = await command_repository.timeout_command(command.id)
        assert timed_out_command is not None
        assert timed_out_command.status == "timeout"

    @pytest.mark.asyncio
    async def test_search_commands_basic(self, command_repository, test_user, test_session_obj):
        """Test basic command search."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="test search command"
        )
        
        commands = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)}
        )
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_search_commands_with_query(self, command_repository, test_user, test_session_obj):
        """Test command search with query."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="unique_search_term_xyz"
        )
        
        commands = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)},
            query="unique_search_term_xyz"
        )
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_get_user_commands_with_session(self, command_repository, test_user, test_session_obj):
        """Test getting user commands with session info."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="test command"
        )
        
        commands = await command_repository.get_user_commands_with_session(
            test_user.id, include_session_info=True
        )
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_count_user_commands(self, command_repository, test_user, test_session_obj):
        """Test counting user commands."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="count test"
        )
        
        count = await command_repository.count_user_commands(test_user.id)
        assert count >= 1

    @pytest.mark.asyncio
    async def test_get_user_commands(self, command_repository, test_user, test_session_obj):
        """Test getting all user commands."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="user command test"
        )
        
        commands = await command_repository.get_user_commands(test_user.id)
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_get_session_command_stats(self, command_repository, test_user, test_session_obj):
        """Test getting command stats by session."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="stats test"
        )
        
        stats = await command_repository.get_session_command_stats(test_user.id)
        assert len(stats) >= 1
        for stat in stats:
            assert "session_id" in stat
            assert "command_count" in stat

    @pytest.mark.asyncio
    async def test_get_user_commands_since(self, command_repository, test_user, test_session_obj):
        """Test getting user commands since a date."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="recent command"
        )
        
        hour_ago = datetime.now() - timedelta(hours=1)
        commands = await command_repository.get_user_commands_since(test_user.id, hour_ago)
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_get_user_recent_commands(self, command_repository, test_user, test_session_obj):
        """Test getting recent user commands."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="recent command"
        )
        
        commands = await command_repository.get_user_recent_commands(test_user.id)
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_get_failed_commands(self, command_repository, test_user, test_session_obj):
        """Test getting failed commands."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="failed command",
            status="error",
            exit_code=1
        )
        
        failed_commands = await command_repository.get_failed_commands(
            user_id=str(test_user.id)
        )
        assert len(failed_commands) >= 1

    @pytest.mark.asyncio
    async def test_get_command_stats(self, command_repository, test_user, test_session_obj):
        """Test getting command statistics."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="stats command"
        )
        
        stats = await command_repository.get_command_stats(user_id=str(test_user.id))
        
        assert "total_commands" in stats
        assert "status_breakdown" in stats
        assert stats["total_commands"] >= 1

    @pytest.mark.asyncio
    async def test_get_top_commands(self, command_repository, test_user, test_session_obj):
        """Test getting top commands."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="popular command"
        )
        
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
        # Create an old command by setting date manually
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
    async def test_get_recent_commands(self, command_repository, test_user, test_session_obj):
        """Test getting recent commands."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="recent command test"
        )
        
        recent_commands = await command_repository.get_recent_commands(
            str(test_user.id), hours=24
        )
        assert len(recent_commands) >= 1

    @pytest.mark.asyncio
    async def test_start_command_execution_not_found(self, command_repository):
        """Test starting execution for non-existent command."""
        result = await command_repository.start_command_execution("non-existent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_count_commands_with_criteria(self, command_repository, test_user, test_session_obj):
        """Test counting commands with criteria."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="criteria test",
            status="success"
        )
        
        count = await command_repository.count_commands_with_criteria({
            "user_id": str(test_user.id),
            "status": "success"
        })
        assert count >= 1

    @pytest.mark.asyncio
    async def test_get_ai_suggested_commands(self, command_repository, test_user, test_session_obj):
        """Test getting AI-suggested commands."""
        await command_repository.create_command(
            session_id=test_session_obj.id,
            command="ai suggested",
            was_ai_suggested=True
        )
        
        ai_commands = await command_repository.get_ai_suggested_commands(
            user_id=str(test_user.id)
        )
        assert len(ai_commands) >= 1
        for cmd in ai_commands:
            assert cmd.was_ai_suggested is True

    @pytest.mark.asyncio
    async def test_get_commands_by_type(self, command_repository, test_user, test_session_obj):
        """Test getting commands by type."""
        # Create command and ensure it has a type
        command = await command_repository.create_command(
            session_id=test_session_obj.id,
            command="ls -la",
            command_type="list"
        )
        
        if command.command_type:
            commands = await command_repository.get_commands_by_type(
                command.command_type, user_id=str(test_user.id)
            )
            assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_search_commands_pagination(self, command_repository, test_user, test_session_obj):
        """Test search pagination."""
        # Create multiple commands
        for i in range(5):
            await command_repository.create_command(
                session_id=test_session_obj.id,
                command=f"pagination test {i}"
            )
        
        page1 = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)},
            offset=0,
            limit=2
        )
        page2 = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)},
            offset=2,
            limit=2
        )
        
        assert len(page1) == 2
        assert len(page2) >= 1
        # Ensure different results
        page1_ids = {cmd.id for cmd in page1}
        page2_ids = {cmd.id for cmd in page2}
        assert not page1_ids.intersection(page2_ids)

    @pytest.mark.asyncio
    async def test_repository_methods_exist(self, command_repository):
        """Test that repository has expected methods."""
        assert hasattr(command_repository, 'create_command')
        assert hasattr(command_repository, 'get_session_commands')
        assert hasattr(command_repository, 'get_user_command_history')
        assert hasattr(command_repository, 'get_commands_by_status')
        assert hasattr(command_repository, 'search_commands')
        assert hasattr(command_repository, 'cleanup_old_commands')