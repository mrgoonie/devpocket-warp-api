"""
Comprehensive tests for Commands service with proper interface matching.

This module provides extensive coverage for Commands service operations,
targeting the high-impact methods to achieve 60%+ coverage gains.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.commands.service import CommandService
from app.api.commands.schemas import (
    CommandHistoryResponse,
    CommandSearchRequest,
    CommandSuggestionRequest,
    CommandType,
    CommandStatus,
    CommandUsageStats,
    FrequentCommandsResponse,
    SessionCommandStats,
    CommandMetrics,
)
from app.models.command import Command
from app.models.session import Session


@pytest.mark.database
class TestCommandServiceComprehensive:
    """Comprehensive test suite for CommandService with correct interfaces."""

    @pytest_asyncio.fixture
    async def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        return session

    @pytest_asyncio.fixture
    async def mock_command_repo(self):
        """Create a mock command repository."""
        repo = AsyncMock()
        return repo

    @pytest_asyncio.fixture
    async def mock_session_repo(self):
        """Create a mock session repository."""
        repo = AsyncMock()
        return repo

    @pytest_asyncio.fixture
    async def command_service(self, mock_session, mock_command_repo, mock_session_repo):
        """Create command service instance with mocked dependencies."""
        with patch('app.api.commands.service.CommandRepository', return_value=mock_command_repo), \
             patch('app.api.commands.service.SessionRepository', return_value=mock_session_repo):
            service = CommandService(mock_session)
            return service

    @pytest_asyncio.fixture
    async def sample_commands(self):
        """Create sample commands with all required fields."""
        commands = []
        base_user_id = uuid4()
        
        for i in range(5):
            session_id = uuid4()
            cmd = Command(
                id=uuid4(),
                session_id=session_id,
                command=f"echo 'test {i}'",
                status="completed",
                exit_code=0,
                stdout=f"test {i}\n",
                stderr="",
                executed_at=datetime.now(timezone.utc) - timedelta(hours=i),
                command_type="file",
                is_dangerous=False,
                working_directory="/",
            )
            
            # Create session mock object
            session_mock = MagicMock()
            session_mock.id = session_id
            session_mock.user_id = base_user_id
            session_mock.name = f"session_{i}"
            session_mock.session_type = "local"
            cmd.session = session_mock
            
            commands.append(cmd)
        return commands

    # ============================================================================
    # Service Initialization Tests
    # ============================================================================

    async def test_service_initialization(self, mock_session):
        """Test CommandService initialization."""
        with patch('app.api.commands.service.CommandRepository') as mock_cmd_repo, \
             patch('app.api.commands.service.SessionRepository') as mock_sess_repo:
            service = CommandService(mock_session)
            
            assert service.session == mock_session
            assert service.command_repo is not None
            assert service.session_repo is not None
            assert hasattr(service, 'command_patterns')
            assert hasattr(service, 'dangerous_patterns')
            mock_cmd_repo.assert_called_once_with(mock_session)
            mock_sess_repo.assert_called_once_with(mock_session)

    async def test_command_patterns_initialization(self, command_service):
        """Test that command patterns are properly initialized."""
        assert len(command_service.command_patterns) > 0
        assert len(command_service.dangerous_patterns) > 0
        
        # Check specific pattern types exist
        assert CommandType.SYSTEM in command_service.command_patterns
        assert CommandType.FILE in command_service.command_patterns
        assert CommandType.NETWORK in command_service.command_patterns
        assert CommandType.GIT in command_service.command_patterns

    # ============================================================================
    # Command History Tests
    # ============================================================================

    async def test_get_command_history_success(self, command_service, sample_commands):
        """Test successful command history retrieval."""
        user_id = str(uuid4())
        
        # Setup mock
        command_service.command_repo.get_user_commands_with_session.return_value = sample_commands
        command_service.command_repo.count_user_commands.return_value = len(sample_commands)

        # Execute
        result = await command_service.get_command_history(user_id=user_id, offset=0, limit=10)

        # Assert
        assert isinstance(result, CommandHistoryResponse)
        assert len(result.entries) == len(sample_commands)
        assert result.total == len(sample_commands)
        assert result.offset == 0
        assert result.limit == 10
        command_service.command_repo.get_user_commands_with_session.assert_called_once_with(
            user_id, offset=0, limit=10
        )

    async def test_get_command_history_with_session_filter(self, command_service, sample_commands):
        """Test command history with session filter."""
        user_id = str(uuid4())
        session_id = str(uuid4())
        
        command_service.command_repo.get_user_commands_with_session.return_value = sample_commands[:2]
        command_service.command_repo.count_user_commands.return_value = 2

        result = await command_service.get_command_history(
            user_id=user_id, 
            session_id=session_id,
            offset=0, 
            limit=10
        )

        assert isinstance(result, CommandHistoryResponse)
        assert len(result.entries) == 2
        assert result.filters_applied == {"session_id": session_id}

    async def test_get_command_history_skips_incomplete_commands(self, command_service):
        """Test that commands without required fields are skipped."""
        user_id = str(uuid4())
        
        # Create commands with missing fields
        incomplete_commands = [
            Command(id=uuid4(), command="test1"),  # No executed_at
            Command(id=uuid4(), command="test2", executed_at=datetime.now(timezone.utc)),  # No duration_ms
        ]
        
        command_service.command_repo.get_user_commands_with_session.return_value = incomplete_commands
        command_service.command_repo.count_user_commands.return_value = 2

        result = await command_service.get_command_history(user_id=user_id)

        assert isinstance(result, CommandHistoryResponse)
        assert len(result.entries) == 0  # Should skip incomplete commands
        assert result.total == 2  # But total count is still reported

    async def test_get_command_history_error_handling(self, command_service):
        """Test command history error handling."""
        user_id = str(uuid4())
        
        command_service.command_repo.get_user_commands_with_session.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_command_history(user_id=user_id)

        assert exc_info.value.status_code == 500
        assert "Failed to retrieve command history" in exc_info.value.detail

    # ============================================================================
    # Search Commands Tests
    # ============================================================================

    async def test_search_commands_basic(self, command_service, sample_commands):
        """Test basic command search functionality."""
        user_id = str(uuid4())
        
        search_request = CommandSearchRequest(query="echo")
        command_service.command_repo.search_commands.return_value = sample_commands
        command_service.command_repo.count_commands_with_criteria.return_value = len(sample_commands)

        result, total = await command_service.search_commands(user_id, search_request)

        assert len(result) == len(sample_commands)
        assert total == len(sample_commands)
        command_service.command_repo.search_commands.assert_called_once()

    async def test_search_commands_with_filters(self, command_service, sample_commands):
        """Test command search with various filters."""
        user_id = str(uuid4())
        
        search_request = CommandSearchRequest(
            query="echo",
            command_type=CommandType.FILE,
            status=CommandStatus.COMPLETED,
            exit_code=0,
            executed_after=datetime.now(timezone.utc) - timedelta(days=7),
            executed_before=datetime.now(timezone.utc),
            min_duration_ms=50,
            max_duration_ms=200,
            has_output=True,
            has_error=False,
            output_contains="test",
            working_directory="/",
            include_dangerous=False,
            only_dangerous=False,
            sort_by="executed_at",
            sort_order="desc",
            offset=0,
            limit=20
        )
        
        command_service.command_repo.search_commands.return_value = sample_commands
        command_service.command_repo.count_commands_with_criteria.return_value = len(sample_commands)

        result, total = await command_service.search_commands(user_id, search_request)

        assert len(result) == len(sample_commands)
        assert total == len(sample_commands)
        
        # Verify search was called with correct criteria
        call_args = command_service.command_repo.search_commands.call_args
        criteria = call_args.kwargs['criteria']
        assert criteria['user_id'] == user_id
        assert criteria['command_type'] == CommandType.FILE.value
        assert criteria['status'] == CommandStatus.COMPLETED.value
        assert criteria['exit_code'] == 0

    async def test_search_commands_error_handling(self, command_service):
        """Test search commands error handling."""
        user_id = str(uuid4())
        search_request = CommandSearchRequest(query="test")
        
        command_service.command_repo.search_commands.side_effect = Exception("Search error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.search_commands(user_id, search_request)

        assert exc_info.value.status_code == 500
        assert "Failed to search commands" in exc_info.value.detail

    # ============================================================================
    # Command Details Tests
    # ============================================================================

    async def test_get_command_details_success(self, command_service, sample_commands):
        """Test successful command details retrieval."""
        command = sample_commands[0]
        user_id = str(command.session.user_id)  # Use the session's user_id
        
        command_service.command_repo.get_by_id.return_value = command

        result = await command_service.get_command_details(user_id, str(command.id))

        assert result.id == str(command.id)
        assert result.command == command.command
        command_service.command_repo.get_by_id.assert_called_once_with(str(command.id))

    async def test_get_command_details_not_found(self, command_service):
        """Test command details when command not found."""
        user_id = str(uuid4())
        command_id = str(uuid4())
        
        command_service.command_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_command_details(user_id, command_id)

        assert exc_info.value.status_code == 404
        assert "Command not found" in exc_info.value.detail

    async def test_get_command_details_wrong_user(self, command_service, sample_commands):
        """Test command details access by wrong user."""
        wrong_user_id = str(uuid4())
        command = sample_commands[0]
        # Set command session to have a different user_id
        command.session.user_id = uuid4()  # Different user
        
        command_service.command_repo.get_by_id.return_value = command

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_command_details(wrong_user_id, str(command.id))

        assert exc_info.value.status_code == 404
        assert "Command not found" in exc_info.value.detail

    # ============================================================================
    # Delete Command Tests
    # ============================================================================

    async def test_delete_command_success(self, command_service, sample_commands):
        """Test successful command deletion."""
        command = sample_commands[0]
        user_id = str(command.session.user_id)  # Use the session's user_id
        
        command_service.command_repo.get_by_id.return_value = command
        command_service.command_repo.delete.return_value = None

        result = await command_service.delete_command(user_id, str(command.id))

        assert result is True
        command_service.command_repo.delete.assert_called_once_with(str(command.id))
        command_service.session.commit.assert_called_once()

    async def test_delete_command_not_found(self, command_service):
        """Test command deletion when command not found."""
        user_id = str(uuid4())
        command_id = str(uuid4())
        
        command_service.command_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await command_service.delete_command(user_id, command_id)

        assert exc_info.value.status_code == 404
        assert "Command not found" in exc_info.value.detail

    async def test_delete_command_wrong_user(self, command_service, sample_commands):
        """Test command deletion by wrong user."""
        wrong_user_id = str(uuid4())
        command = sample_commands[0]
        # Set command session to have a different user_id
        command.session.user_id = uuid4()  # Different user
        
        command_service.command_repo.get_by_id.return_value = command

        with pytest.raises(HTTPException) as exc_info:
            await command_service.delete_command(wrong_user_id, str(command.id))

        assert exc_info.value.status_code == 404
        assert "Command not found" in exc_info.value.detail

    async def test_delete_command_repository_error(self, command_service, sample_commands):
        """Test delete command with repository error."""
        command = sample_commands[0]
        user_id = str(command.session.user_id)  # Use the session's user_id
        
        command_service.command_repo.get_by_id.return_value = command
        command_service.command_repo.delete.side_effect = Exception("Delete error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.delete_command(user_id, str(command.id))

        assert exc_info.value.status_code == 500
        assert "Failed to delete command" in exc_info.value.detail
        command_service.session.rollback.assert_called_once()

    # ============================================================================
    # Usage Stats Tests
    # ============================================================================

    async def test_get_usage_stats_success(self, command_service, sample_commands):
        """Test successful usage statistics retrieval."""
        user_id = str(uuid4())
        
        command_service.command_repo.get_user_commands.return_value = sample_commands

        result = await command_service.get_usage_stats(user_id)

        assert isinstance(result, CommandUsageStats)
        assert result.total_commands == len(sample_commands)
        assert result.unique_commands > 0
        command_service.command_repo.get_user_commands.assert_called_once_with(
            user_id, offset=0, limit=10000
        )

    async def test_get_usage_stats_empty_commands(self, command_service):
        """Test usage statistics with no commands."""
        user_id = str(uuid4())
        
        command_service.command_repo.get_user_commands.return_value = []

        result = await command_service.get_usage_stats(user_id)

        assert isinstance(result, CommandUsageStats)
        assert result.total_commands == 0
        assert result.unique_commands == 0
        assert result.successful_commands == 0
        assert result.failed_commands == 0

    async def test_get_usage_stats_error_handling(self, command_service):
        """Test usage statistics error handling."""
        user_id = str(uuid4())
        
        command_service.command_repo.get_user_commands.side_effect = Exception("Stats error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_usage_stats(user_id)

        assert exc_info.value.status_code == 500
        assert "Failed to get command usage statistics" in exc_info.value.detail

    # ============================================================================
    # Session Command Stats Tests
    # ============================================================================

    async def test_get_session_command_stats_success(self, command_service):
        """Test successful session command statistics retrieval."""
        user_id = str(uuid4())
        
        mock_stats = [
            {
                "session_id": str(uuid4()),
                "session_name": "session_1",
                "total_commands": 25,
                "successful_commands": 20,
                "failed_commands": 5,
                "average_duration_ms": 1200.5,
                "last_command_at": datetime.now(timezone.utc),
                "most_used_command": "ls -la"
            },
            {
                "session_id": str(uuid4()),
                "session_name": "session_2",
                "total_commands": 30,
                "successful_commands": 28,
                "failed_commands": 2,
                "average_duration_ms": 800.2,
                "last_command_at": datetime.now(timezone.utc),
                "most_used_command": "git status"
            }
        ]
        command_service.command_repo.get_session_command_stats.return_value = mock_stats

        result = await command_service.get_session_command_stats(user_id)

        assert len(result) == 2
        assert all(isinstance(stat, SessionCommandStats) for stat in result)
        assert result[0].total_commands == 25
        assert result[1].total_commands == 30
        command_service.command_repo.get_session_command_stats.assert_called_once_with(user_id)

    async def test_get_session_command_stats_error_handling(self, command_service):
        """Test session command statistics error handling."""
        user_id = str(uuid4())
        
        command_service.command_repo.get_session_command_stats.side_effect = Exception("Stats error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_session_command_stats(user_id)

        assert exc_info.value.status_code == 500
        assert "Failed to get session command statistics" in exc_info.value.detail

    # ============================================================================
    # Frequent Commands Tests
    # ============================================================================

    async def test_get_frequent_commands_success(self, command_service, sample_commands):
        """Test successful frequent commands retrieval."""
        user_id = str(uuid4())
        
        command_service.command_repo.get_user_commands_since.return_value = sample_commands

        result = await command_service.get_frequent_commands(user_id, days=30, min_usage=1)

        assert isinstance(result, FrequentCommandsResponse)
        assert result.analysis_period_days == 30
        assert result.total_analyzed == len(sample_commands)
        command_service.command_repo.get_user_commands_since.assert_called_once()

    async def test_get_frequent_commands_empty(self, command_service):
        """Test frequent commands with no data."""
        user_id = str(uuid4())
        
        command_service.command_repo.get_user_commands_since.return_value = []

        result = await command_service.get_frequent_commands(user_id)

        assert isinstance(result, FrequentCommandsResponse)
        assert len(result.commands) == 0
        assert result.total_analyzed == 0

    async def test_get_frequent_commands_error_handling(self, command_service):
        """Test frequent commands error handling."""
        user_id = str(uuid4())
        
        command_service.command_repo.get_user_commands_since.side_effect = Exception("Frequent error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_frequent_commands(user_id)

        assert exc_info.value.status_code == 500
        assert "Failed to analyze frequent commands" in exc_info.value.detail

    # ============================================================================
    # Command Suggestions Tests
    # ============================================================================

    async def test_get_command_suggestions_success(self, command_service, sample_commands):
        """Test successful command suggestions retrieval."""
        user_id = str(uuid4())
        
        request = CommandSuggestionRequest(
            context="show files in directory",
            max_suggestions=5
        )
        command_service.command_repo.get_user_recent_commands.return_value = sample_commands

        result = await command_service.get_command_suggestions(user_id, request)

        assert isinstance(result, list)
        assert len(result) <= request.max_suggestions
        command_service.command_repo.get_user_recent_commands.assert_called_once_with(user_id, limit=100)

    async def test_get_command_suggestions_file_operations(self, command_service):
        """Test command suggestions for file operations."""
        user_id = str(uuid4())
        
        request = CommandSuggestionRequest(
            context="list files in directory",
            max_suggestions=10
        )
        command_service.command_repo.get_user_recent_commands.return_value = []

        result = await command_service.get_command_suggestions(user_id, request)

        assert len(result) > 0
        # Should include file operation suggestions
        commands = [s.command for s in result]
        assert any("ls" in cmd for cmd in commands)

    async def test_get_command_suggestions_system_monitoring(self, command_service):
        """Test command suggestions for system monitoring."""
        user_id = str(uuid4())
        
        request = CommandSuggestionRequest(
            context="check process and memory usage",
            max_suggestions=10
        )
        command_service.command_repo.get_user_recent_commands.return_value = []

        result = await command_service.get_command_suggestions(user_id, request)

        assert len(result) > 0
        # Should include system monitoring suggestions
        commands = [s.command for s in result]
        assert any("ps" in cmd or "top" in cmd for cmd in commands)

    async def test_get_command_suggestions_network(self, command_service):
        """Test command suggestions for network operations."""
        user_id = str(uuid4())
        
        request = CommandSuggestionRequest(
            context="ping network connection",
            max_suggestions=10
        )
        command_service.command_repo.get_user_recent_commands.return_value = []

        result = await command_service.get_command_suggestions(user_id, request)

        assert len(result) > 0
        # Should include network suggestions
        commands = [s.command for s in result]
        assert any("ping" in cmd for cmd in commands)

    async def test_get_command_suggestions_git(self, command_service):
        """Test command suggestions for git operations."""
        user_id = str(uuid4())
        
        request = CommandSuggestionRequest(
            context="git status repository",
            max_suggestions=10
        )
        command_service.command_repo.get_user_recent_commands.return_value = []

        result = await command_service.get_command_suggestions(user_id, request)

        assert len(result) > 0
        # Should include git suggestions
        commands = [s.command for s in result]
        assert any("git status" in cmd for cmd in commands)

    async def test_get_command_suggestions_error_handling(self, command_service):
        """Test command suggestions error handling."""
        user_id = str(uuid4())
        request = CommandSuggestionRequest(context="test")
        
        command_service.command_repo.get_user_recent_commands.side_effect = Exception("Suggestions error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_command_suggestions(user_id, request)

        assert exc_info.value.status_code == 500
        assert "Failed to generate command suggestions" in exc_info.value.detail

    # ============================================================================
    # Command Metrics Tests
    # ============================================================================

    async def test_get_command_metrics_success(self, command_service, sample_commands):
        """Test successful command metrics retrieval."""
        user_id = str(uuid4())
        
        # Modify sample commands for metrics testing
        for i, cmd in enumerate(sample_commands):
            cmd.status = "completed" if i % 2 == 0 else "running"
            cmd.executed_at = datetime.now(timezone.utc) - timedelta(hours=i)
            cmd.exit_code = 0 if i % 3 != 0 else 1
            
        command_service.command_repo.get_user_commands_since.return_value = sample_commands

        result = await command_service.get_command_metrics(user_id)

        assert isinstance(result, CommandMetrics)
        assert result.active_commands >= 0
        assert result.completed_today >= 0
        assert result.failed_today >= 0
        assert isinstance(result.top_error_types, list)
        command_service.command_repo.get_user_commands_since.assert_called_once()

    async def test_get_command_metrics_error_handling(self, command_service):
        """Test command metrics error handling."""
        user_id = str(uuid4())
        
        command_service.command_repo.get_user_commands_since.side_effect = Exception("Metrics error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_command_metrics(user_id)

        assert exc_info.value.status_code == 500
        assert "Failed to get command metrics" in exc_info.value.detail

    # ============================================================================
    # Helper Method Tests
    # ============================================================================

    async def test_classify_command_file(self, command_service):
        """Test command classification for file operations."""
        assert command_service._classify_command("ls -la") == CommandType.FILE
        assert command_service._classify_command("cp file1 file2") == CommandType.FILE
        assert command_service._classify_command("rm -rf folder") == CommandType.FILE

    async def test_classify_command_system(self, command_service):
        """Test command classification for system operations."""
        assert command_service._classify_command("ps aux") == CommandType.SYSTEM
        assert command_service._classify_command("top") == CommandType.SYSTEM
        assert command_service._classify_command("uptime") == CommandType.SYSTEM

    async def test_classify_command_network(self, command_service):
        """Test command classification for network operations."""
        assert command_service._classify_command("ping google.com") == CommandType.NETWORK
        assert command_service._classify_command("curl http://example.com") == CommandType.NETWORK
        assert command_service._classify_command("ssh user@host") == CommandType.NETWORK

    async def test_classify_command_git(self, command_service):
        """Test command classification for git operations."""
        assert command_service._classify_command("git status") == CommandType.GIT
        assert command_service._classify_command("git commit -m 'test'") == CommandType.GIT
        assert command_service._classify_command("git push origin main") == CommandType.GIT

    async def test_classify_command_unknown(self, command_service):
        """Test command classification for unknown commands."""
        assert command_service._classify_command("unknowncommand") == CommandType.UNKNOWN
        assert command_service._classify_command("") == CommandType.UNKNOWN

    async def test_is_dangerous_command_true(self, command_service):
        """Test dangerous command detection for dangerous commands."""
        assert command_service._is_dangerous_command("sudo rm -rf /") is True
        assert command_service._is_dangerous_command("dd if=/dev/zero of=/dev/sda") is True
        assert command_service._is_dangerous_command("chmod 777 /") is True
        assert command_service._is_dangerous_command(":(){ :|:& };:") is True

    async def test_is_dangerous_command_false(self, command_service):
        """Test dangerous command detection for safe commands."""
        assert command_service._is_dangerous_command("ls -la") is False
        assert command_service._is_dangerous_command("cat file.txt") is False
        assert command_service._is_dangerous_command("git status") is False
        assert command_service._is_dangerous_command("echo 'hello'") is False

    async def test_matches_pattern(self, command_service):
        """Test pattern matching functionality."""
        assert command_service._matches_pattern("ls /home/user", "ls /path") is True
        assert command_service._matches_pattern("ping 192.168.1.1", "ping IP") is True
        assert command_service._matches_pattern("curl https://example.com", "curl URL") is True

    async def test_create_command_pattern(self, command_service):
        """Test command pattern creation."""
        pattern = command_service._create_command_pattern("ls /home/user/documents")
        assert "/path" in pattern
        
        pattern = command_service._create_command_pattern("ping 192.168.1.1")
        assert "IP" in pattern
        
        pattern = command_service._create_command_pattern("curl https://example.com/api/v1/users/123")
        assert "URL" in pattern
        
        pattern = command_service._create_command_pattern("kill 12345")
        assert "N" in pattern