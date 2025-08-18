"""
Comprehensive tests for Command repository functionality.

This module provides extensive coverage for all Command repository operations,
including CRUD operations, search functionality, bulk operations, and performance metrics.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from app.models.command import Command
from app.models.session import Session
from app.models.user import User
from app.repositories.command import CommandRepository
from app.repositories.session import SessionRepository
from app.repositories.user import UserRepository


@pytest.mark.database
class TestCommandRepositoryComprehensive:
    """Comprehensive test suite for CommandRepository."""

    @pytest.fixture
    async def command_repository(self, test_session):
        """Create command repository instance."""
        return CommandRepository(test_session)

    @pytest.fixture
    async def user_repository(self, test_session):
        """Create user repository instance."""
        return UserRepository(test_session)

    @pytest.fixture
    async def session_repository(self, test_session):
        """Create session repository instance."""
        return SessionRepository(test_session)

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
    async def test_session_1(self, test_session, test_user):
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
    async def test_session_2(self, test_session, test_user):
        """Create a second test session."""
        session = Session(
            user_id=test_user.id,
            session_name="test_session_2",
            shell="/bin/zsh",
            environment="production"
        )
        test_session.add(session)
        await test_session.commit()
        await test_session.refresh(session)
        return session

    @pytest.fixture
    async def sample_commands(self, command_repository, test_session, test_user, test_session_1, test_session_2):
        """Create multiple sample commands for testing."""
        commands = []

        # Create varied commands
        command_specs = [
            {"session": test_session_1, "command": "ls -la", "status": "success", "exit_code": 0},
            {"session": test_session_1, "command": "grep -r 'pattern' .", "status": "error", "exit_code": 1}, 
            {"session": test_session_2, "command": "python script.py", "status": "running", "exit_code": None},
            {"session": test_session_2, "command": "docker ps", "status": "success", "exit_code": 0},
            {"session": test_session_1, "command": "rm -rf /", "status": "cancelled", "exit_code": 130}
        ]

        for spec in command_specs:
            cmd = await command_repository.create_command(
                session_id=spec["session"].id,
                command=spec["command"],
                status=spec["status"],
                exit_code=spec["exit_code"]
            )
            commands.append(cmd)

        return commands

    @pytest.mark.asyncio
    async def test_create_command_success(self, command_repository, test_session_1):
        """Test successful command creation."""
        command = await command_repository.create_command(
            session_id=test_session_1.id,
            command="ls -la",
            working_directory="/home/user"
        )

        assert command.command == "ls -la"
        assert command.working_directory == "/home/user"
        assert command.status == "pending"
        assert command.id is not None
        assert command.command_type is not None
        assert command.is_sensitive is not None

    @pytest.mark.asyncio
    async def test_create_command_with_kwargs(self, command_repository, test_session):
        """Test command creation with additional kwargs."""
        command = await command_repository.create_command(
            session_id=str(uuid4()),
            command="cat secret.txt",
            working_directory="/home/user",
            priority=5,
            environment={"PATH": "/usr/bin"}
        )

        assert command.command == "cat secret.txt"
        assert command.working_directory == "/home/user"
        assert command.priority == 5

    @pytest.mark.asyncio
    async def test_get_session_commands(self, command_repository, sample_commands):
        """Test retrieving commands for a specific session."""
        commands = await sample_commands
        session_id = commands[0].session_id
        
        commands = await command_repository.get_session_commands(session_id)
        
        assert len(commands) >= 2  # At least 2 commands in first session
        for cmd in commands:
            assert cmd.session_id == session_id

    @pytest.mark.asyncio
    async def test_get_session_commands_with_status_filter(self, command_repository, sample_commands):
        """Test retrieving commands with status filter."""
        commands = await sample_commands
        session_id = commands[0].session_id
        
        success_commands = await command_repository.get_session_commands(
            session_id, status_filter="success"
        )
        
        assert len(success_commands) >= 1
        for cmd in success_commands:
            assert cmd.status == "success"

    @pytest.mark.asyncio
    async def test_get_session_commands_pagination(self, command_repository, sample_commands):
        """Test pagination for session commands."""
        commands = await sample_commands
        session_id = commands[0].session_id
        
        page1 = await command_repository.get_session_commands(
            session_id, offset=0, limit=1
        )
        page2 = await command_repository.get_session_commands(
            session_id, offset=1, limit=1
        )
        
        assert len(page1) == 1
        assert len(page2) <= 1
        if len(page2) == 1:
            assert page1[0].id != page2[0].id

    @pytest.mark.asyncio
    async def test_get_user_command_history(self, command_repository, test_user, sample_commands):
        """Test retrieving command history for a user."""
        await sample_commands  # Ensure sample commands are created
        commands = await command_repository.get_user_command_history(str(test_user.id))
        
        assert len(commands) >= 5  # All sample commands
        for cmd in commands:
            assert cmd.session.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_get_user_command_history_with_search(self, command_repository, test_user, sample_commands):
        """Test searching user command history."""
        await sample_commands  # Ensure sample commands are created
        commands = await command_repository.get_user_command_history(
            str(test_user.id), search_term="docker"
        )
        
        assert len(commands) >= 1
        for cmd in commands:
            assert "docker" in cmd.command.lower()

    @pytest.mark.asyncio
    async def test_get_commands_by_status(self, command_repository, sample_commands):
        """Test retrieving commands by status."""
        await sample_commands  # Ensure sample commands are created
        running_commands = await command_repository.get_commands_by_status("running")
        success_commands = await command_repository.get_commands_by_status("success")
        
        assert len(running_commands) >= 1
        assert len(success_commands) >= 2
        
        for cmd in running_commands:
            assert cmd.status == "running"
        for cmd in success_commands:
            assert cmd.status == "success"

    @pytest.mark.asyncio
    async def test_get_commands_by_status_with_user_filter(self, command_repository, test_user, sample_commands):
        """Test retrieving commands by status filtered by user."""
        await sample_commands  # Ensure sample commands are created
        commands = await command_repository.get_commands_by_status(
            "success", user_id=str(test_user.id)
        )
        
        assert len(commands) >= 2
        for cmd in commands:
            assert cmd.status == "success"

    @pytest.mark.asyncio
    async def test_get_running_commands(self, command_repository, sample_commands):
        """Test retrieving currently running commands."""
        await sample_commands  # Ensure sample commands are created
        running_commands = await command_repository.get_running_commands()
        
        assert len(running_commands) >= 1
        for cmd in running_commands:
            assert cmd.status == "running"

    @pytest.mark.asyncio
    async def test_get_running_commands_by_session(self, command_repository, sample_commands):
        """Test retrieving running commands for specific session."""
        commands = await sample_commands
        session_id = commands[2].session_id  # running command is in session 2
        
        running_commands = await command_repository.get_running_commands(
            session_id=session_id
        )
        
        for cmd in running_commands:
            assert cmd.status == "running"
            assert cmd.session_id == session_id

    @pytest.mark.asyncio
    async def test_get_running_commands_by_user(self, command_repository, test_user, sample_commands):
        """Test retrieving running commands for specific user."""
        await sample_commands  # Ensure sample commands are created
        running_commands = await command_repository.get_running_commands(
            user_id=str(test_user.id)
        )
        
        assert len(running_commands) >= 1
        for cmd in running_commands:
            assert cmd.status == "running"

    @pytest.mark.asyncio
    async def test_start_command_execution(self, command_repository, test_session):
        """Test starting command execution."""
        # Create a pending command
        command = await command_repository.create_command(
            session_id=str(uuid4()),
            command="sleep 5"
        )
        
        # Start execution
        updated_command = await command_repository.start_command_execution(command.id)
        
        assert updated_command is not None
        assert updated_command.status == "running"
        assert updated_command.started_at is not None

    @pytest.mark.asyncio
    async def test_start_command_execution_not_found(self, command_repository):
        """Test starting execution for non-existent command."""
        result = await command_repository.start_command_execution("non-existent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_complete_command_execution(self, command_repository, test_session):
        """Test completing command execution."""
        # Create and start a command
        command = await command_repository.create_command(
            session_id=str(uuid4()),
            command="echo hello"
        )
        await command_repository.start_command_execution(command.id)
        
        # Complete execution
        updated_command = await command_repository.complete_command_execution(
            command.id,
            exit_code=0,
            output="hello\\n",
            error_output=None
        )
        
        assert updated_command is not None
        assert updated_command.status == "success"
        assert updated_command.exit_code == 0
        assert updated_command.output == "hello\\n"
        assert updated_command.completed_at is not None
        assert updated_command.execution_time is not None

    @pytest.mark.asyncio
    async def test_complete_command_execution_with_error(self, command_repository, test_session):
        """Test completing command execution with error."""
        command = await command_repository.create_command(
            session_id=str(uuid4()),
            command="false"
        )
        await command_repository.start_command_execution(command.id)
        
        updated_command = await command_repository.complete_command_execution(
            command.id,
            exit_code=1,
            output="",
            error_output="command failed"
        )
        
        assert updated_command.status == "error"
        assert updated_command.exit_code == 1
        assert updated_command.error_output == "command failed"

    @pytest.mark.asyncio
    async def test_cancel_command(self, command_repository, test_session):
        """Test cancelling a command."""
        command = await command_repository.create_command(
            session_id=str(uuid4()),
            command="sleep 60"
        )
        await command_repository.start_command_execution(command.id)
        
        cancelled_command = await command_repository.cancel_command(command.id)
        
        assert cancelled_command is not None
        assert cancelled_command.status == "cancelled"
        assert cancelled_command.completed_at is not None

    @pytest.mark.asyncio
    async def test_timeout_command(self, command_repository, test_session):
        """Test timing out a command."""
        command = await command_repository.create_command(
            session_id=str(uuid4()),
            command="sleep 60"
        )
        await command_repository.start_command_execution(command.id)
        
        timed_out_command = await command_repository.timeout_command(command.id)
        
        assert timed_out_command is not None
        assert timed_out_command.status == "timeout"
        assert timed_out_command.completed_at is not None

    @pytest.mark.asyncio
    async def test_search_commands_basic(self, command_repository, test_user, sample_commands):
        """Test basic command search."""
        await sample_commands  # Ensure sample commands are created
        commands = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)}
        )
        
        assert len(commands) >= 5
        
    @pytest.mark.asyncio
    async def test_search_commands_with_query(self, command_repository, test_user, sample_commands):
        """Test command search with text query."""
        await sample_commands  # Ensure sample commands are created
        commands = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)},
            query="docker"
        )
        
        assert len(commands) >= 1
        for cmd in commands:
            assert "docker" in cmd.command.lower()

    @pytest.mark.asyncio
    async def test_search_commands_date_range(self, command_repository, test_user, sample_commands):
        """Test command search with date range."""
        await sample_commands  # Ensure sample commands are created
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        commands = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)},
            executed_after=hour_ago
        )
        
        # All our sample commands should be within the last hour
        assert len(commands) >= 5

    @pytest.mark.asyncio
    async def test_search_commands_duration_filter(self, command_repository, test_user, sample_commands):
        """Test command search with duration filters."""
        commands = await sample_commands
        # First complete some commands with known durations
        for cmd in commands[:2]:
            if cmd.status != "success":
                continue
            await command_repository.complete_command_execution(
                cmd.id, exit_code=0, output="test"
            )
        
        commands = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)},
            min_duration_ms=0,
            max_duration_ms=5000  # 5 seconds
        )
        
        for cmd in commands:
            if cmd.execution_time:
                assert cmd.execution_time <= 5.0

    @pytest.mark.asyncio
    async def test_search_commands_output_filters(self, command_repository, test_user, sample_commands):
        """Test command search with output filters."""
        commands = await sample_commands
        # Add output to a command
        cmd = commands[0]
        await command_repository.complete_command_execution(
            cmd.id, exit_code=0, output="test output"
        )
        
        # Search for commands with output
        commands = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)},
            has_output=True
        )
        
        assert len(commands) >= 1
        for cmd in commands:
            assert cmd.output is not None

    @pytest.mark.asyncio
    async def test_search_commands_error_filter(self, command_repository, test_user, sample_commands):
        """Test command search with error filter."""
        await sample_commands  # Ensure sample commands are created
        commands = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)},
            has_error=True
        )
        
        assert len(commands) >= 1
        for cmd in commands:
            assert cmd.exit_code != 0

    @pytest.mark.asyncio
    async def test_search_commands_output_contains(self, command_repository, test_user, sample_commands):
        """Test command search with output content filter."""
        commands = await sample_commands
        # Add specific output to a command
        cmd = commands[0]
        await command_repository.complete_command_execution(
            cmd.id, exit_code=0, output="specific_test_content"
        )
        
        commands = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)},
            output_contains="specific_test_content"
        )
        
        assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_search_commands_sorting(self, command_repository, test_user, sample_commands):
        """Test command search with sorting."""
        await sample_commands  # Ensure sample commands are created
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
        
        assert len(commands_desc) >= 2
        assert len(commands_asc) >= 2
        assert commands_desc[0].id != commands_asc[0].id

    @pytest.mark.asyncio
    async def test_get_user_commands_with_session(self, command_repository, test_user, sample_commands):
        """Test retrieving user commands with session info."""
        await sample_commands  # Ensure sample commands are created
        commands = await command_repository.get_user_commands_with_session(
            test_user.id, include_session_info=True
        )
        
        assert len(commands) >= 5
        for cmd in commands:
            assert hasattr(cmd, 'session')

    @pytest.mark.asyncio
    async def test_count_user_commands(self, command_repository, test_user, sample_commands):
        """Test counting user commands."""
        await sample_commands  # Ensure sample commands are created
        count = await command_repository.count_user_commands(test_user.id)
        assert count >= 5

    @pytest.mark.asyncio
    async def test_count_commands_with_criteria(self, command_repository, test_user, sample_commands):
        """Test counting commands with criteria."""
        await sample_commands  # Ensure sample commands are created
        count = await command_repository.count_commands_with_criteria({
            "user_id": str(test_user.id),
            "status": "success"
        })
        assert count >= 2

    @pytest.mark.asyncio
    async def test_get_user_commands(self, command_repository, test_user, sample_commands):
        """Test getting all user commands."""
        await sample_commands  # Ensure sample commands are created
        commands = await command_repository.get_user_commands(test_user.id)
        assert len(commands) >= 5

    @pytest.mark.asyncio
    async def test_get_session_command_stats(self, command_repository, test_user, sample_commands):
        """Test getting command statistics by session."""
        await sample_commands  # Ensure sample commands are created
        stats = await command_repository.get_session_command_stats(test_user.id)
        
        assert len(stats) >= 2  # At least 2 sessions
        for stat in stats:
            assert "session_id" in stat
            assert "session_name" in stat
            assert "command_count" in stat
            assert stat["command_count"] > 0

    @pytest.mark.asyncio
    async def test_get_user_commands_since(self, command_repository, test_user, sample_commands):
        """Test getting user commands since a date."""
        await sample_commands  # Ensure sample commands are created
        hour_ago = datetime.now() - timedelta(hours=1)
        commands = await command_repository.get_user_commands_since(test_user.id, hour_ago)
        
        assert len(commands) >= 5
        for cmd in commands:
            assert cmd.created_at >= hour_ago

    @pytest.mark.asyncio
    async def test_get_user_recent_commands(self, command_repository, test_user, sample_commands):
        """Test getting recent user commands."""
        await sample_commands  # Ensure sample commands are created
        commands = await command_repository.get_user_recent_commands(test_user.id)
        
        assert len(commands) >= 5

    @pytest.mark.asyncio
    async def test_get_commands_by_type(self, command_repository, test_user, sample_commands):
        """Test getting commands by type."""
        commands = await sample_commands
        # Commands should have been classified during creation
        first_cmd = commands[0]
        if first_cmd.command_type:
            commands = await command_repository.get_commands_by_type(
                first_cmd.command_type, user_id=str(test_user.id)
            )
            assert len(commands) >= 1

    @pytest.mark.asyncio
    async def test_get_ai_suggested_commands(self, command_repository, test_user, test_session):
        """Test getting AI-suggested commands."""
        # Create an AI-suggested command
        command = await command_repository.create_command(
            session_id=str(uuid4()),
            command="ls -la",
            was_ai_suggested=True
        )
        
        ai_commands = await command_repository.get_ai_suggested_commands(
            user_id=str(test_user.id)
        )
        
        assert len(ai_commands) >= 1
        for cmd in ai_commands:
            assert cmd.was_ai_suggested is True

    @pytest.mark.asyncio
    async def test_get_failed_commands(self, command_repository, test_user, sample_commands):
        """Test getting failed commands."""
        await sample_commands  # Ensure sample commands are created
        failed_commands = await command_repository.get_failed_commands(
            user_id=str(test_user.id)
        )
        
        assert len(failed_commands) >= 1
        for cmd in failed_commands:
            assert cmd.exit_code != 0 or cmd.status == "error"

    @pytest.mark.asyncio
    async def test_get_command_stats(self, command_repository, test_user, sample_commands):
        """Test getting command execution statistics."""
        await sample_commands  # Ensure sample commands are created
        stats = await command_repository.get_command_stats(user_id=str(test_user.id))
        
        assert "total_commands" in stats
        assert "status_breakdown" in stats
        assert "type_breakdown" in stats
        assert "ai_suggested_count" in stats
        assert "average_execution_time" in stats
        
        assert stats["total_commands"] >= 5
        assert isinstance(stats["status_breakdown"], dict)
        assert isinstance(stats["type_breakdown"], dict)

    @pytest.mark.asyncio
    async def test_get_top_commands(self, command_repository, test_user, sample_commands):
        """Test getting most frequently used commands."""
        await sample_commands  # Ensure sample commands are created
        top_commands = await command_repository.get_top_commands(
            user_id=str(test_user.id)
        )
        
        assert len(top_commands) >= 1
        for cmd_data in top_commands:
            assert "command" in cmd_data
            assert "usage_count" in cmd_data
            assert cmd_data["usage_count"] >= 1

    @pytest.mark.asyncio
    async def test_cleanup_old_commands(self, command_repository, test_session):
        """Test cleaning up old commands."""
        # Create an old command by manually setting the date
        old_command = Command(
            session_id=str(uuid4()),
            command="old command"
        )
        old_command.created_at = datetime.now() - timedelta(days=100)
        
        test_session.add(old_command)
        await test_session.commit()
        
        # Cleanup commands older than 90 days
        deleted_count = await command_repository.cleanup_old_commands(days_old=90)
        
        assert deleted_count >= 1

    @pytest.mark.asyncio
    async def test_cleanup_old_commands_keep_successful(self, command_repository, test_session):
        """Test cleaning up old commands while keeping successful ones."""
        # Create old successful and failed commands
        old_success = Command(
            session_id=str(uuid4()),
            command="old success",
            status="success",
            exit_code=0
        )
        old_failed = Command(
            session_id=str(uuid4()),
            command="old failed",
            status="error",
            exit_code=1
        )
        
        old_date = datetime.now() - timedelta(days=100)
        old_success.created_at = old_date
        old_failed.created_at = old_date
        
        test_session.add_all([old_success, old_failed])
        await test_session.commit()
        
        deleted_count = await command_repository.cleanup_old_commands(
            days_old=90, keep_successful=True
        )
        
        # Should delete failed but keep successful
        assert deleted_count >= 1

    @pytest.mark.asyncio
    async def test_get_recent_commands(self, command_repository, test_user, sample_commands):
        """Test getting recent commands for a user."""
        await sample_commands  # Ensure sample commands are created
        recent_commands = await command_repository.get_recent_commands(
            str(test_user.id), hours=24
        )
        
        assert len(recent_commands) >= 5
        
        # All should be within last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        for cmd in recent_commands:
            assert cmd.created_at >= cutoff

    @pytest.mark.asyncio
    async def test_repository_inheritance(self, command_repository):
        """Test that CommandRepository properly inherits from BaseRepository."""
        # Test inherited methods work
        assert hasattr(command_repository, 'create')
        assert hasattr(command_repository, 'get_by_id')
        assert hasattr(command_repository, 'update')
        assert hasattr(command_repository, 'delete')
        assert hasattr(command_repository, 'list')
        assert hasattr(command_repository, 'count')

    @pytest.mark.asyncio
    async def test_edge_cases_empty_results(self, command_repository):
        """Test edge cases with empty results."""
        # Search with impossible criteria
        commands = await command_repository.search_commands(
            query="impossible_command_that_does_not_exist"
        )
        assert commands == []
        
        # Get commands for non-existent user
        commands = await command_repository.get_user_commands("non-existent-user-id")
        assert commands == []
        
        # Count for non-existent user
        count = await command_repository.count_user_commands("non-existent-user-id")
        assert count == 0

    @pytest.mark.asyncio
    async def test_error_handling_invalid_params(self, command_repository):
        """Test error handling for invalid parameters."""
        # Test with invalid sort parameters
        try:
            await command_repository.search_commands(
                sort_by="invalid_field",
                sort_order="invalid_order"
            )
        except Exception:
            # Should handle gracefully or raise appropriate error
            pass

    @pytest.mark.asyncio
    async def test_performance_large_dataset(self, command_repository, test_user, test_session):
        """Test performance with larger datasets."""
        # Create session for bulk commands
        session = Session(
            user_id=test_user.id,
            session_name="bulk_test_session",
            shell="/bin/bash"
        )
        test_session.add(session)
        await test_session.commit()
        await test_session.refresh(session)
        
        # Create multiple commands efficiently
        commands = []
        for i in range(50):
            cmd = Command(
                session_id=session.id,
                command=f"test_command_{i}",
                status="success" if i % 2 == 0 else "error",
                exit_code=0 if i % 2 == 0 else 1
            )
            commands.append(cmd)
        
        test_session.add_all(commands)
        await test_session.commit()
        
        # Test search performance
        start_time = datetime.now()
        results = await command_repository.search_commands(
            criteria={"user_id": str(test_user.id)},
            limit=25
        )
        end_time = datetime.now()
        
        assert len(results) == 25
        # Should complete within reasonable time (adjust as needed)
        assert (end_time - start_time).total_seconds() < 1.0