"""
Working tests for Command repository functionality.

This module provides focused coverage for high-impact Command repository operations
with proper async handling and realistic test scenarios.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from app.models.command import Command
from app.models.session import Session
from app.models.user import User
from app.repositories.command import CommandRepository


@pytest.mark.database
class TestCommandRepositoryWorking:
    """Working test suite for CommandRepository focused on coverage."""

    @pytest_asyncio.fixture
    async def command_repository(self, test_session):
        """Create command repository instance."""
        return CommandRepository(test_session)

    @pytest_asyncio.fixture
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

    @pytest_asyncio.fixture
    async def test_session_1(self, test_session, test_user):
        """Create a test session."""
        session = Session(
            user_id=test_user.id,
            device_id="test-device-1",
            device_type="web",
            ssh_host="localhost",
            ssh_port=22,
            ssh_username="testuser"
        )
        test_session.add(session)
        await test_session.commit()
        await test_session.refresh(session)
        return session

    @pytest_asyncio.fixture
    async def test_session_2(self, test_session, test_user):
        """Create a second test session."""
        session = Session(
            user_id=test_user.id,
            device_id="test-device-2",
            device_type="web",
            ssh_host="remote.example.com",
            ssh_port=2222,
            ssh_username="remoteuser"
        )
        test_session.add(session)
        await test_session.commit()
        await test_session.refresh(session)
        return session

    async def test_create_command_success(self, command_repository, test_session_1):
        """Test successful command creation."""
        command_text = "ls -la"
        
        result = await command_repository.create_command(
            session_id=test_session_1.id,
            command=command_text
        )
        
        assert result is not None
        assert result.command == command_text
        assert result.session_id == test_session_1.id
        assert result.status == "pending"

    async def test_create_command_with_kwargs(self, command_repository, test_session_1):
        """Test command creation with additional arguments."""
        command_text = "python script.py"
        
        result = await command_repository.create_command(
            session_id=test_session_1.id,
            command=command_text,
            working_directory="/home/user",
            was_ai_suggested=True,
            command_type="ai"
        )
        
        assert result is not None
        assert result.command == command_text
        assert result.working_directory == "/home/user"
        assert result.was_ai_suggested is True
        assert result.command_type == "ai"

    async def test_start_command_execution(self, command_repository, test_session_1):
        """Test starting command execution."""
        # Create command first
        command = await command_repository.create_command(
            session_id=test_session_1.id,
            command="sleep 5"
        )
        
        # Start execution
        result = await command_repository.start_command_execution(command.id)
        
        assert result is not None
        assert result.status == "running"
        assert result.started_at is not None

    async def test_start_command_execution_not_found(self, command_repository):
        """Test starting command execution for non-existent command."""
        non_existent_id = uuid4()
        
        result = await command_repository.start_command_execution(non_existent_id)
        
        assert result is None

    async def test_complete_command_execution(self, command_repository, test_session_1):
        """Test completing command execution successfully."""
        # Create and start command
        command = await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'hello world'"
        )
        await command_repository.start_command_execution(command.id)
        
        # Complete execution
        result = await command_repository.complete_command_execution(
            command_id=command.id,
            exit_code=0,
            output="hello world\n",
            error_output=None
        )
        
        assert result is not None
        assert result.status == "completed"
        assert result.exit_code == 0
        assert result.output == "hello world\n"
        assert result.completed_at is not None

    async def test_complete_command_execution_with_error(self, command_repository, test_session_1):
        """Test completing command execution with error."""
        # Create and start command
        command = await command_repository.create_command(
            session_id=test_session_1.id,
            command="ls /nonexistent"
        )
        await command_repository.start_command_execution(command.id)
        
        # Complete with error
        result = await command_repository.complete_command_execution(
            command_id=command.id,
            exit_code=2,
            output="",
            error_output="ls: cannot access '/nonexistent': No such file or directory\n"
        )
        
        assert result is not None
        assert result.status == "failed"
        assert result.exit_code == 2
        assert result.error_output is not None

    async def test_cancel_command(self, command_repository, test_session_1):
        """Test canceling a running command."""
        # Create and start command
        command = await command_repository.create_command(
            session_id=test_session_1.id,
            command="sleep 100"
        )
        await command_repository.start_command_execution(command.id)
        
        # Cancel command
        result = await command_repository.cancel_command(command.id)
        
        assert result is not None
        assert result.status == "cancelled"
        assert result.completed_at is not None

    async def test_timeout_command(self, command_repository, test_session_1):
        """Test timing out a command."""
        # Create and start command
        command = await command_repository.create_command(
            session_id=test_session_1.id,
            command="sleep 1000"
        )
        await command_repository.start_command_execution(command.id)
        
        # Timeout command
        result = await command_repository.timeout_command(command.id)
        
        assert result is not None
        assert result.status == "timeout"
        assert result.completed_at is not None

    async def test_get_session_commands(self, command_repository, test_session_1):
        """Test retrieving commands for a session."""
        # Create multiple commands
        commands = []
        for i in range(3):
            cmd = await command_repository.create_command(
                session_id=test_session_1.id,
                command=f"echo 'test {i}'"
            )
            commands.append(cmd)
        
        # Get session commands
        result = await command_repository.get_session_commands(
            session_id=test_session_1.id,
            offset=0,
            limit=10
        )
        
        assert len(result) == 3
        assert all(cmd.session_id == test_session_1.id for cmd in result)

    async def test_get_session_commands_pagination(self, command_repository, test_session_1):
        """Test session commands with pagination."""
        # Create multiple commands
        for i in range(5):
            await command_repository.create_command(
                session_id=test_session_1.id,
                command=f"echo 'test {i}'"
            )
        
        # Get first page
        page1 = await command_repository.get_session_commands(
            session_id=test_session_1.id,
            offset=0,
            limit=2
        )
        
        # Get second page
        page2 = await command_repository.get_session_commands(
            session_id=test_session_1.id,
            offset=2,
            limit=2
        )
        
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id

    async def test_get_session_commands_with_status_filter(self, command_repository, test_session_1):
        """Test session commands with status filter."""
        # Create commands with different statuses
        cmd1 = await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'pending'"
        )
        
        cmd2 = await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'running'"
        )
        await command_repository.start_command_execution(cmd2.id)
        
        # Filter by status
        pending_commands = await command_repository.get_session_commands(
            session_id=test_session_1.id,
            status_filter="pending"
        )
        
        running_commands = await command_repository.get_session_commands(
            session_id=test_session_1.id,
            status_filter="running"
        )
        
        assert len(pending_commands) == 1
        assert pending_commands[0].status == "pending"
        assert len(running_commands) == 1
        assert running_commands[0].status == "running"

    async def test_get_user_commands(self, command_repository, test_user, test_session_1):
        """Test retrieving commands for a user."""
        # Create commands
        for i in range(3):
            await command_repository.create_command(
                session_id=test_session_1.id,
                command=f"echo 'user command {i}'"
            )
        
        # Get user commands
        result = await command_repository.get_user_commands(
            user_id=test_user.id,
            offset=0,
            limit=10
        )
        
        assert len(result) == 3

    async def test_get_user_commands_with_session(self, command_repository, test_user, test_session_1, test_session_2):
        """Test retrieving user commands with session information."""
        # Create commands in different sessions
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'session1'"
        )
        await command_repository.create_command(
            session_id=test_session_2.id,
            command="echo 'session2'"
        )
        
        # Get commands with session info
        result = await command_repository.get_user_commands_with_session(
            user_id=test_user.id,
            include_session_info=True
        )
        
        assert len(result) == 2

    async def test_get_commands_by_status(self, command_repository, test_user, test_session_1):
        """Test retrieving commands by status."""
        # Create commands with different statuses
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'pending1'"
        )
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'pending2'"
        )
        
        # Get pending commands
        result = await command_repository.get_commands_by_status(
            status="pending",
            user_id=test_user.id
        )
        
        assert len(result) == 2
        assert all(cmd.status == "pending" for cmd in result)

    async def test_get_commands_by_status_with_user_filter(self, command_repository, test_user, test_session_1):
        """Test retrieving commands by status with user filter."""
        # Create commands
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'test'"
        )
        
        # Get with user filter
        result = await command_repository.get_commands_by_status(
            status="pending",
            user_id=test_user.id
        )
        
        assert len(result) == 1
        assert result[0].status == "pending"

    async def test_get_running_commands(self, command_repository, test_session_1):
        """Test retrieving running commands."""
        # Create and start commands
        cmd1 = await command_repository.create_command(
            session_id=test_session_1.id,
            command="sleep 10"
        )
        await command_repository.start_command_execution(cmd1.id)
        
        cmd2 = await command_repository.create_command(
            session_id=test_session_1.id,
            command="sleep 20"
        )
        await command_repository.start_command_execution(cmd2.id)
        
        # Get running commands
        result = await command_repository.get_running_commands()
        
        assert len(result) >= 2  # At least our 2 commands
        running_cmd_ids = [cmd.id for cmd in result]
        assert cmd1.id in running_cmd_ids
        assert cmd2.id in running_cmd_ids

    async def test_get_running_commands_by_user(self, command_repository, test_user, test_session_1):
        """Test retrieving running commands by user."""
        # Create and start command
        cmd = await command_repository.create_command(
            session_id=test_session_1.id,
            command="sleep 5"
        )
        await command_repository.start_command_execution(cmd.id)
        
        # Get running commands for user
        result = await command_repository.get_running_commands(user_id=test_user.id)
        
        assert len(result) == 1
        assert result[0].id == cmd.id

    async def test_get_running_commands_by_session(self, command_repository, test_session_1):
        """Test retrieving running commands by session."""
        # Create and start command
        cmd = await command_repository.create_command(
            session_id=test_session_1.id,
            command="sleep 5"
        )
        await command_repository.start_command_execution(cmd.id)
        
        # Get running commands for session
        result = await command_repository.get_running_commands(session_id=test_session_1.id)
        
        assert len(result) == 1
        assert result[0].id == cmd.id

    async def test_search_commands_basic(self, command_repository, test_session_1):
        """Test basic command search functionality."""
        # Create test commands
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="ls -la"
        )
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="grep test file.txt"
        )
        
        # Search all commands
        result = await command_repository.search_commands({})
        
        assert len(result) >= 2

    async def test_search_commands_with_query(self, command_repository, test_session_1):
        """Test command search with query filter."""
        # Create test commands
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="ls -la /home"
        )
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="grep search file.txt"
        )
        
        # Search with query
        result = await command_repository.search_commands({
            "query": "ls"
        })
        
        assert len(result) >= 1
        assert any("ls" in cmd.command for cmd in result)

    async def test_search_commands_date_range(self, command_repository, test_session_1):
        """Test command search with date range."""
        # Create test command
        cmd = await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'date test'"
        )
        
        # Search with date range
        now = datetime.utcnow()
        result = await command_repository.search_commands({
            "executed_after": now - timedelta(hours=1),
            "executed_before": now + timedelta(hours=1)
        })
        
        assert len(result) >= 1

    async def test_search_commands_duration_filter(self, command_repository, test_session_1):
        """Test command search with duration filter."""
        # Create and complete command with known duration
        cmd = await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'duration test'"
        )
        await command_repository.start_command_execution(cmd.id)
        await command_repository.complete_command_execution(
            command_id=cmd.id,
            exit_code=0,
            output="duration test\n"
        )
        
        # Search with duration filter (should work with wide range)
        result = await command_repository.search_commands({
            "min_duration_ms": 0,
            "max_duration_ms": 10000  # 10 seconds max
        })
        
        assert len(result) >= 1

    async def test_search_commands_output_filters(self, command_repository, test_session_1):
        """Test command search with output-related filters."""
        # Create command with output
        cmd = await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'output test'"
        )
        await command_repository.start_command_execution(cmd.id)
        await command_repository.complete_command_execution(
            command_id=cmd.id,
            exit_code=0,
            output="output test\n"
        )
        
        # Search commands with output
        result = await command_repository.search_commands({
            "has_output": True
        })
        
        assert len(result) >= 1

    async def test_search_commands_output_contains(self, command_repository, test_session_1):
        """Test command search with output content filter."""
        # Create command with specific output
        cmd = await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'specific output'"
        )
        await command_repository.start_command_execution(cmd.id)
        await command_repository.complete_command_execution(
            command_id=cmd.id,
            exit_code=0,
            output="specific output\n"
        )
        
        # Search by output content
        result = await command_repository.search_commands({
            "output_contains": "specific"
        })
        
        assert len(result) >= 1

    async def test_search_commands_error_filter(self, command_repository, test_session_1):
        """Test command search with error filter."""
        # Create command with error
        cmd = await command_repository.create_command(
            session_id=test_session_1.id,
            command="ls /nonexistent"
        )
        await command_repository.start_command_execution(cmd.id)
        await command_repository.complete_command_execution(
            command_id=cmd.id,
            exit_code=2,
            error_output="ls: cannot access '/nonexistent': No such file or directory\n"
        )
        
        # Search commands with errors
        result = await command_repository.search_commands({
            "has_error": True
        })
        
        assert len(result) >= 1

    async def test_search_commands_sorting(self, command_repository, test_session_1):
        """Test command search with sorting."""
        # Create multiple commands
        for i in range(3):
            await command_repository.create_command(
                session_id=test_session_1.id,
                command=f"echo 'sort test {i}'"
            )
        
        # Search with different sort orders
        asc_result = await command_repository.search_commands({
            "sort_by": "created_at",
            "sort_order": "asc"
        })
        
        desc_result = await command_repository.search_commands({
            "sort_by": "created_at", 
            "sort_order": "desc"
        })
        
        assert len(asc_result) >= 3
        assert len(desc_result) >= 3
        assert asc_result[0].id != desc_result[0].id

    async def test_count_user_commands(self, command_repository, test_user, test_session_1):
        """Test counting user commands."""
        # Create commands
        for i in range(5):
            await command_repository.create_command(
                session_id=test_session_1.id,
                command=f"echo 'count test {i}'"
            )
        
        # Count commands
        count = await command_repository.count_user_commands(test_user.id)
        
        assert count == 5

    async def test_count_commands_with_criteria(self, command_repository, test_session_1):
        """Test counting commands with search criteria."""
        # Create test commands
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="ls -la"
        )
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="grep test file.txt"
        )
        
        # Count with criteria
        count = await command_repository.count_commands_with_criteria({
            "query": "ls"
        })
        
        assert count >= 1

    async def test_get_commands_by_type(self, command_repository, test_user, test_session_1):
        """Test retrieving commands by type."""
        # Create commands with different types
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'manual command'",
            command_type="manual"
        )
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'ai command'",
            command_type="ai"
        )
        
        # Get AI commands
        ai_commands = await command_repository.get_commands_by_type(
            command_type="ai",
            user_id=test_user.id
        )
        
        assert len(ai_commands) == 1
        assert ai_commands[0].command_type == "ai"

    async def test_get_ai_suggested_commands(self, command_repository, test_user, test_session_1):
        """Test retrieving AI-suggested commands."""
        # Create AI-suggested command
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'ai suggested'",
            was_ai_suggested=True
        )
        
        # Create regular command
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'manual'"
        )
        
        # Get AI suggested commands
        result = await command_repository.get_ai_suggested_commands(test_user.id)
        
        assert len(result) == 1
        assert result[0].was_ai_suggested is True

    async def test_get_failed_commands(self, command_repository, test_user, test_session_1):
        """Test retrieving failed commands."""
        # Create and fail a command
        cmd = await command_repository.create_command(
            session_id=test_session_1.id,
            command="ls /nonexistent"
        )
        await command_repository.start_command_execution(cmd.id)
        await command_repository.complete_command_execution(
            command_id=cmd.id,
            exit_code=1,
            error_output="Error output"
        )
        
        # Get failed commands
        result = await command_repository.get_failed_commands(user_id=test_user.id)
        
        assert len(result) == 1
        assert result[0].status == "failed"

    async def test_get_user_command_history(self, command_repository, test_user, test_session_1):
        """Test retrieving user command history."""
        # Create commands
        for i in range(3):
            await command_repository.create_command(
                session_id=test_session_1.id,
                command=f"echo 'history {i}'"
            )
        
        # Get command history
        result = await command_repository.get_user_command_history(
            user_id=test_user.id,
            offset=0,
            limit=10
        )
        
        assert len(result) == 3

    async def test_get_user_command_history_with_search(self, command_repository, test_user, test_session_1):
        """Test retrieving user command history with search."""
        # Create commands
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="ls -la"
        )
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="grep search file.txt"
        )
        
        # Search command history
        result = await command_repository.get_user_command_history(
            user_id=test_user.id,
            search_term="ls"
        )
        
        assert len(result) >= 1
        assert any("ls" in cmd.command for cmd in result)

    async def test_get_user_commands_since(self, command_repository, test_user, test_session_1):
        """Test retrieving user commands since a specific time."""
        # Create command
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'since test'"
        )
        
        # Get commands since an hour ago
        since_time = datetime.utcnow() - timedelta(hours=1)
        result = await command_repository.get_user_commands_since(
            user_id=test_user.id,
            since=since_time
        )
        
        assert len(result) >= 1

    async def test_get_user_recent_commands(self, command_repository, test_user, test_session_1):
        """Test retrieving user recent commands."""
        # Create command
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'recent test'"
        )
        
        # Get recent commands
        result = await command_repository.get_user_recent_commands(
            user_id=test_user.id,
            limit=5
        )
        
        assert len(result) >= 1

    async def test_get_session_command_stats(self, command_repository, test_user, test_session_1):
        """Test retrieving session command statistics."""
        # Create commands with different statuses
        cmd1 = await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'completed'"
        )
        await command_repository.start_command_execution(cmd1.id)
        await command_repository.complete_command_execution(
            command_id=cmd1.id,
            exit_code=0,
            output="completed\n"
        )
        
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'pending'"
        )
        
        # Get session stats
        result = await command_repository.get_session_command_stats(test_user.id)
        
        assert len(result) >= 1

    async def test_get_command_stats(self, command_repository, test_user, test_session_1):
        """Test retrieving command statistics."""
        # Create various commands
        cmd1 = await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'completed'",
            command_type="manual"
        )
        await command_repository.start_command_execution(cmd1.id)
        await command_repository.complete_command_execution(
            command_id=cmd1.id,
            exit_code=0,
            output="completed\n"
        )
        
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'ai command'",
            was_ai_suggested=True,
            command_type="ai"
        )
        
        # Get command stats
        stats = await command_repository.get_command_stats(test_user.id)
        
        assert "total_commands" in stats
        assert "status_breakdown" in stats
        assert "type_breakdown" in stats
        assert stats["total_commands"] >= 2

    async def test_get_top_commands(self, command_repository, test_user, test_session_1):
        """Test retrieving top used commands."""
        # Create duplicate commands to test frequency
        for i in range(3):
            await command_repository.create_command(
                session_id=test_session_1.id,
                command="ls -la"
            )
        
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="pwd"
        )
        
        # Get top commands
        result = await command_repository.get_top_commands(
            user_id=test_user.id,
            limit=5
        )
        
        assert len(result) >= 1

    async def test_get_recent_commands(self, command_repository, test_user, test_session_1):
        """Test retrieving recent commands."""
        # Create command
        await command_repository.create_command(
            session_id=test_session_1.id,
            command="echo 'recent'"
        )
        
        # Get recent commands
        result = await command_repository.get_recent_commands(
            user_id=test_user.id,
            hours=24,
            limit=10
        )
        
        assert len(result) >= 1

    async def test_cleanup_old_commands(self, command_repository, test_session_1):
        """Test cleaning up old commands."""
        # Create old command by mocking datetime
        old_date = datetime.utcnow() - timedelta(days=100)
        
        with patch('app.repositories.command.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = old_date
            old_cmd = await command_repository.create_command(
                session_id=test_session_1.id,
                command="echo 'old command'"
            )
        
        # Cleanup old commands
        deleted_count = await command_repository.cleanup_old_commands(
            days_old=30,
            keep_successful=False
        )
        
        assert deleted_count >= 0  # Should work without errors

    async def test_cleanup_old_commands_keep_successful(self, command_repository, test_session_1):
        """Test cleaning up old commands while keeping successful ones."""
        # Test cleanup with keep_successful flag
        deleted_count = await command_repository.cleanup_old_commands(
            days_old=30,
            keep_successful=True
        )
        
        assert deleted_count >= 0  # Should work without errors

    async def test_repository_inheritance(self, command_repository):
        """Test that CommandRepository properly inherits from BaseRepository."""
        # Test that it has BaseRepository methods
        assert hasattr(command_repository, 'session')
        assert hasattr(command_repository, 'create')
        assert hasattr(command_repository, 'get_by_id')
        assert hasattr(command_repository, 'update')
        assert hasattr(command_repository, 'delete')

    async def test_edge_cases_empty_results(self, command_repository, test_user):
        """Test edge cases with empty results."""
        # Test getting commands for non-existent user
        fake_user_id = uuid4()
        result = await command_repository.get_user_commands(
            user_id=fake_user_id,
            offset=0,
            limit=10
        )
        
        assert result == []

    async def test_performance_large_dataset(self, command_repository, test_session_1):
        """Test performance with larger dataset."""
        # Create many commands (but not too many for CI)
        commands_to_create = 50
        for i in range(commands_to_create):
            await command_repository.create_command(
                session_id=test_session_1.id,
                command=f"echo 'performance test {i}'"
            )
        
        # Test search performance
        result = await command_repository.search_commands({
            "query": "performance",
            "limit": 20
        })
        
        assert len(result) <= 20  # Should respect limit
        assert len(result) > 0  # Should find some results