"""
Comprehensive tests for Commands service functionality with proper API matching.

This module provides extensive coverage for Commands service operations,
targeting high-impact methods to achieve significant coverage gains.
"""

import pytest
import pytest_asyncio
from collections import Counter
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status

from app.api.commands.service import CommandService
from app.api.commands.schemas import (
    CommandHistoryResponse,
    CommandSearchRequest,
    CommandResponse,
    CommandStatus,
    CommandType,
    CommandUsageStats,
    SessionCommandStats,
    FrequentCommandsResponse,
    CommandSuggestionRequest,
    CommandSuggestion,
    CommandMetrics,
)
from app.models.command import Command
from app.models.session import Session
from app.models.user import User
from tests.factories import UserFactory, CommandFactory, SessionFactory


@pytest.mark.database
@pytest.mark.api
class TestCommandServiceComprehensive:
    """Comprehensive test suite for CommandService with proper API coverage."""

    @pytest_asyncio.fixture
    async def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
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
    async def command_service(self, mock_db_session, mock_command_repo, mock_session_repo):
        """Create command service instance with mocked dependencies."""
        with patch('app.api.commands.service.CommandRepository', return_value=mock_command_repo), \
             patch('app.api.commands.service.SessionRepository', return_value=mock_session_repo):
            service = CommandService(mock_db_session)
            service.command_repo = mock_command_repo
            service.session_repo = mock_session_repo
            return service

    @pytest_asyncio.fixture
    async def sample_user(self):
        """Create a sample user."""
        return UserFactory()

    @pytest_asyncio.fixture
    async def sample_session(self, sample_user):
        """Create a sample session."""
        session = SessionFactory()
        session.user_id = sample_user.id
        return session

    @pytest_asyncio.fixture
    async def sample_commands(self, sample_user, sample_session):
        """Create sample commands with proper relationships."""
        commands = []
        for i in range(5):
            cmd = CommandFactory()
            cmd.user_id = sample_user.id
            cmd.session_id = sample_session.id
            cmd.command = f"echo 'test {i}'"
            cmd.status = "completed"
            cmd.exit_code = 0
            cmd.stdout = f"test {i}\n"
            cmd.stderr = ""
            cmd.duration_ms = 100 + i * 50
            cmd.executed_at = datetime.now(UTC) - timedelta(hours=i)
            cmd.command_type = "system"
            cmd.is_dangerous = False
            # Add session relationship
            cmd.session = sample_session
            commands.append(cmd)
        return commands

    # Service Initialization Tests
    async def test_service_initialization(self, mock_db_session):
        """Test CommandService initialization with proper dependencies."""
        with patch('app.api.commands.service.CommandRepository') as mock_cmd_repo, \
             patch('app.api.commands.service.SessionRepository') as mock_sess_repo:
            service = CommandService(mock_db_session)
            
            assert service.session == mock_db_session
            assert service.command_repo is not None
            assert service.session_repo is not None
            assert hasattr(service, 'command_patterns')
            assert hasattr(service, 'dangerous_patterns')
            mock_cmd_repo.assert_called_once_with(mock_db_session)
            mock_sess_repo.assert_called_once_with(mock_db_session)

    async def test_command_patterns_initialization(self, command_service):
        """Test that command patterns are properly initialized."""
        assert len(command_service.command_patterns) > 0
        assert CommandType.SYSTEM in command_service.command_patterns
        assert CommandType.FILE in command_service.command_patterns
        assert CommandType.NETWORK in command_service.command_patterns
        assert CommandType.GIT in command_service.command_patterns
        assert len(command_service.dangerous_patterns) > 0

    # Command History Tests
    async def test_get_command_history_success(self, command_service, sample_user, sample_commands):
        """Test successful command history retrieval."""
        # Setup mocks
        command_service.command_repo.get_user_commands_with_session.return_value = sample_commands
        command_service.command_repo.count_user_commands.return_value = len(sample_commands)

        # Execute
        result = await command_service.get_command_history(
            user=sample_user,
            session_id=None,
            offset=0,
            limit=100
        )

        # Assert
        assert isinstance(result, CommandHistoryResponse)
        assert len(result.entries) == len(sample_commands)
        assert result.total == len(sample_commands)
        assert result.offset == 0
        assert result.limit == 100
        command_service.command_repo.get_user_commands_with_session.assert_called_once()

    async def test_get_command_history_with_session_filter(self, command_service, sample_user, sample_commands):
        """Test command history with session filter."""
        session_id = str(sample_commands[0].session_id)
        filtered_commands = [sample_commands[0]]
        
        command_service.command_repo.get_user_commands_with_session.return_value = filtered_commands
        command_service.command_repo.count_user_commands.return_value = 1

        result = await command_service.get_command_history(
            user=sample_user,
            session_id=session_id,
            offset=0,
            limit=100
        )

        assert len(result.entries) == 1
        assert result.filters_applied == {"session_id": session_id}

    async def test_get_command_history_empty_result(self, command_service, sample_user):
        """Test command history with no commands."""
        command_service.command_repo.get_user_commands_with_session.return_value = []
        command_service.command_repo.count_user_commands.return_value = 0

        result = await command_service.get_command_history(
            user=sample_user,
            session_id=None,
            offset=0,
            limit=100
        )

        assert len(result.entries) == 0
        assert result.total == 0

    async def test_get_command_history_exception_handling(self, command_service, sample_user):
        """Test command history error handling."""
        command_service.command_repo.get_user_commands_with_session.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_command_history(
                user=sample_user,
                session_id=None,
                offset=0,
                limit=100
            )
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve command history" in exc_info.value.detail

    # Command Search Tests
    async def test_search_commands_basic(self, command_service, sample_user, sample_commands):
        """Test basic command search functionality."""
        search_request = CommandSearchRequest(
            query="echo",
            offset=0,
            limit=50
        )
        
        command_service.command_repo.search_commands.return_value = sample_commands
        command_service.command_repo.count_commands_with_criteria.return_value = len(sample_commands)

        commands, total = await command_service.search_commands(sample_user, search_request)

        assert len(commands) == len(sample_commands)
        assert total == len(sample_commands)
        assert all(isinstance(cmd, CommandResponse) for cmd in commands)

    async def test_search_commands_with_filters(self, command_service, sample_user, sample_commands):
        """Test command search with comprehensive filters."""
        search_request = CommandSearchRequest(
            query="echo",
            session_id=str(sample_commands[0].session_id),
            command_type=CommandType.SYSTEM,
            status=CommandStatus.COMPLETED,
            exit_code=0,
            executed_after=datetime.now(UTC) - timedelta(days=7),
            executed_before=datetime.now(UTC),
            min_duration_ms=50,
            max_duration_ms=1000,
            has_output=True,
            has_error=False,
            working_directory="/home/user",
            include_dangerous=False,
            only_dangerous=False,
            sort_by="executed_at",
            sort_order="desc",
            offset=0,
            limit=20
        )
        
        command_service.command_repo.search_commands.return_value = sample_commands
        command_service.command_repo.count_commands_with_criteria.return_value = len(sample_commands)

        commands, total = await command_service.search_commands(sample_user, search_request)

        assert len(commands) == len(sample_commands)
        assert total == len(sample_commands)
        command_service.command_repo.search_commands.assert_called_once()

    async def test_search_commands_exception_handling(self, command_service, sample_user):
        """Test search commands error handling."""
        search_request = CommandSearchRequest(query="test")
        command_service.command_repo.search_commands.side_effect = Exception("Search error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.search_commands(sample_user, search_request)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to search commands" in exc_info.value.detail

    # Command Details Tests
    async def test_get_command_details_success(self, command_service, sample_user, sample_commands):
        """Test successful command details retrieval."""
        command = sample_commands[0]
        command_service.command_repo.get_by_id.return_value = command

        result = await command_service.get_command_details(sample_user, str(command.id))

        assert isinstance(result, CommandResponse)
        assert result.id == str(command.id)
        assert result.command == command.command
        assert result.status == CommandStatus(command.status)

    async def test_get_command_details_not_found(self, command_service, sample_user):
        """Test command details when command not found."""
        command_service.command_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_command_details(sample_user, "nonexistent-id")
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Command not found" in exc_info.value.detail

    async def test_get_command_details_wrong_user(self, command_service, sample_commands):
        """Test command details access by wrong user."""
        command = sample_commands[0]
        wrong_user = UserFactory()
        command_service.command_repo.get_by_id.return_value = command

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_command_details(wrong_user, str(command.id))
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_command_details_exception_handling(self, command_service, sample_user):
        """Test command details error handling."""
        command_service.command_repo.get_by_id.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_command_details(sample_user, "test-id")
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Delete Command Tests
    async def test_delete_command_success(self, command_service, sample_user, sample_commands):
        """Test successful command deletion."""
        command = sample_commands[0]
        command_service.command_repo.get_by_id.return_value = command
        command_service.command_repo.delete.return_value = True

        result = await command_service.delete_command(sample_user, str(command.id))

        assert result is True
        command_service.command_repo.delete.assert_called_once_with(str(command.id))
        command_service.session.commit.assert_called_once()

    async def test_delete_command_not_found(self, command_service, sample_user):
        """Test command deletion when command not found."""
        command_service.command_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await command_service.delete_command(sample_user, "nonexistent-id")
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_command_exception_handling(self, command_service, sample_user, sample_commands):
        """Test delete command error handling."""
        command = sample_commands[0]
        command_service.command_repo.get_by_id.return_value = command
        command_service.command_repo.delete.side_effect = Exception("Delete error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.delete_command(sample_user, str(command.id))
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        command_service.session.rollback.assert_called_once()

    # Usage Statistics Tests
    async def test_get_usage_stats_comprehensive(self, command_service, sample_user, sample_commands):
        """Test comprehensive usage statistics calculation."""
        # Create diverse command set for testing
        diverse_commands = []
        for i in range(10):
            cmd = CommandFactory()
            cmd.user_id = sample_user.id
            cmd.command = ["ls -la", "git status", "echo test", "pwd", "top"][i % 5]
            cmd.exit_code = 0 if i % 3 != 0 else 1  # Some failures
            cmd.duration_ms = 100 + i * 50
            cmd.executed_at = datetime.now(UTC) - timedelta(hours=i)
            cmd.command_type = ["system", "git", "file"][i % 3]
            cmd.status = "completed" if cmd.exit_code == 0 else "failed"
            diverse_commands.append(cmd)

        command_service.command_repo.get_user_commands.return_value = diverse_commands

        result = await command_service.get_usage_stats(sample_user)

        assert isinstance(result, CommandUsageStats)
        assert result.total_commands == len(diverse_commands)
        assert result.unique_commands <= result.total_commands
        assert result.successful_commands + result.failed_commands == result.total_commands
        assert result.average_duration_ms > 0
        assert result.commands_by_type is not None
        assert result.commands_by_status is not None

    async def test_get_usage_stats_empty_commands(self, command_service, sample_user):
        """Test usage statistics with no commands."""
        command_service.command_repo.get_user_commands.return_value = []

        result = await command_service.get_usage_stats(sample_user)

        assert isinstance(result, CommandUsageStats)
        assert result.total_commands == 0
        assert result.unique_commands == 0
        assert result.successful_commands == 0
        assert result.failed_commands == 0
        assert result.average_duration_ms == 0

    async def test_get_usage_stats_exception_handling(self, command_service, sample_user):
        """Test usage statistics error handling."""
        command_service.command_repo.get_user_commands.side_effect = Exception("Stats error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_usage_stats(sample_user)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Session Command Statistics Tests
    async def test_get_session_command_stats_success(self, command_service, sample_user):
        """Test session command statistics retrieval."""
        mock_stats_data = [
            {
                "session_id": "session-1",
                "session_name": "Main Session",
                "total_commands": 25,
                "successful_commands": 20,
                "failed_commands": 5,
                "average_duration_ms": 1200.5,
                "last_command_at": datetime.now(UTC) - timedelta(hours=1),
                "most_used_command": "ls -la"
            },
            {
                "session_id": "session-2",
                "session_name": "Dev Session",
                "total_commands": 15,
                "successful_commands": 14,
                "failed_commands": 1,
                "average_duration_ms": 800.0,
                "last_command_at": datetime.now(UTC) - timedelta(hours=2),
                "most_used_command": "git status"
            }
        ]
        command_service.command_repo.get_session_command_stats.return_value = mock_stats_data

        result = await command_service.get_session_command_stats(sample_user)

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(stat, SessionCommandStats) for stat in result)
        assert result[0].session_id == "session-1"
        assert result[0].total_commands == 25

    async def test_get_session_command_stats_exception_handling(self, command_service, sample_user):
        """Test session command statistics error handling."""
        command_service.command_repo.get_session_command_stats.side_effect = Exception("Stats error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_session_command_stats(sample_user)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Frequent Commands Tests
    async def test_get_frequent_commands_success(self, command_service, sample_user):
        """Test frequent commands analysis."""
        # Create commands with patterns
        frequent_commands = []
        for i in range(20):
            cmd = CommandFactory()
            cmd.user_id = sample_user.id
            cmd.command = ["ls -la", "git status", "echo test"][i % 3]
            cmd.executed_at = datetime.now(UTC) - timedelta(days=i)
            cmd.exit_code = 0 if i % 5 != 0 else 1
            cmd.duration_ms = 100 + i * 10
            frequent_commands.append(cmd)

        command_service.command_repo.get_user_commands_since.return_value = frequent_commands

        result = await command_service.get_frequent_commands(sample_user, days=30, min_usage=3)

        assert isinstance(result, FrequentCommandsResponse)
        assert len(result.commands) > 0
        assert result.total_analyzed == len(frequent_commands)
        assert result.analysis_period_days == 30

    async def test_get_frequent_commands_empty_result(self, command_service, sample_user):
        """Test frequent commands with no commands."""
        command_service.command_repo.get_user_commands_since.return_value = []

        result = await command_service.get_frequent_commands(sample_user)

        assert isinstance(result, FrequentCommandsResponse)
        assert len(result.commands) == 0
        assert result.total_analyzed == 0

    async def test_get_frequent_commands_exception_handling(self, command_service, sample_user):
        """Test frequent commands error handling."""
        command_service.command_repo.get_user_commands_since.side_effect = Exception("Analysis error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_frequent_commands(sample_user)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Command Suggestions Tests
    async def test_get_command_suggestions_file_context(self, command_service, sample_user):
        """Test command suggestions for file operations."""
        recent_commands = [
            CommandFactory(command="ls -la", working_directory="/home/user"),
            CommandFactory(command="cat file.txt", working_directory="/home/user")
        ]
        command_service.command_repo.get_user_recent_commands.return_value = recent_commands

        request = CommandSuggestionRequest(
            context="list files in directory",
            max_suggestions=5
        )

        result = await command_service.get_command_suggestions(sample_user, request)

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(suggestion, CommandSuggestion) for suggestion in result)

    async def test_get_command_suggestions_system_context(self, command_service, sample_user):
        """Test command suggestions for system monitoring."""
        recent_commands = [
            CommandFactory(command="top", working_directory="/home/user"),
            CommandFactory(command="ps aux", working_directory="/home/user")
        ]
        command_service.command_repo.get_user_recent_commands.return_value = recent_commands

        request = CommandSuggestionRequest(
            context="monitor system processes and memory",
            max_suggestions=5
        )

        result = await command_service.get_command_suggestions(sample_user, request)

        assert isinstance(result, list)
        assert len(result) > 0

    async def test_get_command_suggestions_exception_handling(self, command_service, sample_user):
        """Test command suggestions error handling."""
        request = CommandSuggestionRequest(context="test")
        command_service.command_repo.get_user_recent_commands.side_effect = Exception("Suggestion error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_command_suggestions(sample_user, request)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Command Metrics Tests
    async def test_get_command_metrics_comprehensive(self, command_service, sample_user):
        """Test comprehensive command metrics calculation."""
        # Create recent commands for metrics
        recent_commands = []
        now = datetime.now(UTC)
        for i in range(10):
            cmd = CommandFactory()
            cmd.user_id = sample_user.id
            cmd.executed_at = now - timedelta(hours=i)
            cmd.status = "completed" if i % 3 != 0 else "failed"
            cmd.exit_code = 0 if cmd.status == "completed" else 1
            cmd.duration_ms = 100 + i * 50
            cmd.stderr = "error message" if cmd.status == "failed" else ""
            recent_commands.append(cmd)

        command_service.command_repo.get_user_commands_since.return_value = recent_commands

        result = await command_service.get_command_metrics(sample_user)

        assert isinstance(result, CommandMetrics)
        assert result.active_commands >= 0
        assert result.completed_today >= 0
        assert result.failed_today >= 0
        assert result.avg_response_time_ms >= 0
        assert 0 <= result.success_rate_24h <= 100
        assert result.timestamp is not None

    async def test_get_command_metrics_exception_handling(self, command_service, sample_user):
        """Test command metrics error handling."""
        command_service.command_repo.get_user_commands_since.side_effect = Exception("Metrics error")

        with pytest.raises(HTTPException) as exc_info:
            await command_service.get_command_metrics(sample_user)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Helper Method Tests
    async def test_classify_command_types(self, command_service):
        """Test command classification by type."""
        test_cases = [
            ("ls -la", CommandType.FILE),
            ("git status", CommandType.GIT),
            ("ping google.com", CommandType.NETWORK),
            ("ps aux", CommandType.SYSTEM),
            ("apt install package", CommandType.PACKAGE),
            ("mysql -u root", CommandType.DATABASE),
            ("unknown command", CommandType.UNKNOWN)
        ]

        for command, expected_type in test_cases:
            result = command_service._classify_command(command)
            assert result == expected_type

    async def test_is_dangerous_command_detection(self, command_service):
        """Test dangerous command detection."""
        dangerous_commands = [
            "rm -rf /",
            "sudo rm -rf *",
            "dd if=/dev/zero of=/dev/sda",
            "chmod 777 /etc/passwd",
            ":(){ :|:& };:",  # Fork bomb
            "sudo shutdown now"
        ]

        safe_commands = [
            "ls -la",
            "git status",
            "cat file.txt",
            "echo hello world",
            "cd /home/user"
        ]

        for cmd in dangerous_commands:
            assert command_service._is_dangerous_command(cmd) is True

        for cmd in safe_commands:
            assert command_service._is_dangerous_command(cmd) is False

    async def test_analyze_command_patterns(self, command_service):
        """Test command pattern analysis."""
        commands = [
            CommandFactory(command="ls -la /home/user", executed_at=datetime.now(UTC), exit_code=0, duration_ms=100),
            CommandFactory(command="ls -la /home/project", executed_at=datetime.now(UTC), exit_code=0, duration_ms=120),
            CommandFactory(command="ls -la /var/log", executed_at=datetime.now(UTC), exit_code=0, duration_ms=110),
            CommandFactory(command="git status", executed_at=datetime.now(UTC), exit_code=0, duration_ms=200),
            CommandFactory(command="git add .", executed_at=datetime.now(UTC), exit_code=0, duration_ms=150),
        ]

        result = command_service._analyze_command_patterns(commands, min_usage=2)

        assert isinstance(result, dict)
        # Should find ls pattern
        ls_pattern_found = any("ls" in pattern for pattern in result.keys())
        assert ls_pattern_found

    async def test_create_command_pattern(self, command_service):
        """Test command pattern creation."""
        test_cases = [
            ("ls -la /home/user/documents", "ls -la /path"),
            ("ping 192.168.1.1", "ping N.N.N.N"),  # Numbers replaced before IP pattern
            ("curl https://example.com/api", "curl URL"),
            ("kill 1234", "kill N"),
        ]

        for original, expected_pattern in test_cases:
            result = command_service._create_command_pattern(original)
            assert result == expected_pattern

    async def test_helper_suggestion_methods(self, command_service):
        """Test helper methods for command suggestions."""
        # Test file operation suggestions
        file_suggestions = command_service._get_file_operation_suggestions("list files")
        assert isinstance(file_suggestions, list)
        assert len(file_suggestions) > 0

        # Test system monitoring suggestions
        system_suggestions = command_service._get_system_monitoring_suggestions("monitor processes")
        assert isinstance(system_suggestions, list)

        # Test network suggestions
        network_suggestions = command_service._get_network_suggestions("ping network")
        assert isinstance(network_suggestions, list)

        # Test git suggestions
        git_suggestions = command_service._get_git_suggestions("git status check")
        assert isinstance(git_suggestions, list)

        # Test personalized suggestions
        recent_commands = [
            CommandFactory(command="ls -la"),
            CommandFactory(command="git status"),
        ]
        personalized = command_service._get_personalized_suggestions(recent_commands, "git")
        assert isinstance(personalized, list)

    # Edge Cases and Error Scenarios
    async def test_edge_cases_large_datasets(self, command_service, sample_user):
        """Test service behavior with large datasets."""
        # Test with large command history
        large_command_set = [CommandFactory() for _ in range(1000)]
        command_service.command_repo.get_user_commands.return_value = large_command_set

        result = await command_service.get_usage_stats(sample_user)
        assert isinstance(result, CommandUsageStats)
        assert result.total_commands == 1000

    async def test_edge_cases_invalid_data(self, command_service, sample_user):
        """Test service behavior with invalid or incomplete data."""
        # Commands without required fields
        incomplete_commands = []
        for i in range(3):
            cmd = CommandFactory()
            cmd.executed_at = None  # Missing execution time
            cmd.duration_ms = None  # Missing duration
            incomplete_commands.append(cmd)

        command_service.command_repo.get_user_commands_with_session.return_value = incomplete_commands
        command_service.command_repo.count_user_commands.return_value = len(incomplete_commands)

        result = await command_service.get_command_history(sample_user)
        
        # Should handle incomplete data gracefully
        assert isinstance(result, CommandHistoryResponse)
        # Commands without required fields should be skipped
        assert len(result.entries) == 0

    async def test_concurrent_access_simulation(self, command_service, sample_user):
        """Test service behavior under concurrent access patterns."""
        # Simulate multiple operations happening concurrently
        command_service.command_repo.get_user_commands.return_value = []
        command_service.command_repo.count_user_commands.return_value = 0

        # Multiple calls should not interfere with each other
        result1 = await command_service.get_usage_stats(sample_user)
        result2 = await command_service.get_usage_stats(sample_user)

        assert isinstance(result1, CommandUsageStats)
        assert isinstance(result2, CommandUsageStats)
        assert result1.total_commands == result2.total_commands