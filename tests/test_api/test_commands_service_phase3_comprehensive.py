"""
Comprehensive Commands Service Tests - Phase 3 Implementation.

This module provides extensive coverage for Commands service operations,
targeting 65% coverage for Commands Service to achieve Phase 3 objectives.
Implements Phase 3, Week 1 Priority 1 for Commands Service Enhancement.

Coverage Target: 9% → 65% coverage (+144 lines of coverage)
Expected Test Count: ~75-85 comprehensive tests
Focus: Core business logic, CRUD operations, search, analytics, suggestions
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4
from fastapi import HTTPException
from collections import Counter

from app.api.commands.service import CommandService
from app.api.commands.schemas import (
    CommandHistoryResponse,
    CommandHistoryEntry,
    CommandResponse,
    CommandUsageStats,
    CommandSearchRequest,
    CommandSuggestionRequest,
    CommandSuggestion,
    CommandMetrics,
    FrequentCommandsResponse,
    FrequentCommand,
    SessionCommandStats,
    CommandStatus,
    CommandType
)
from app.models.command import Command
from app.models.session import Session
from app.models.user import User


@pytest.mark.database
class TestCommandServicePhase3Comprehensive:
    """Comprehensive test suite for CommandService - Phase 3 Implementation."""

    @pytest_asyncio.fixture
    async def mock_session(self):
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
    async def command_service(self, mock_session, mock_command_repo, mock_session_repo):
        """Create command service instance with mocked dependencies."""
        with patch('app.api.commands.service.CommandRepository', return_value=mock_command_repo), \
             patch('app.api.commands.service.SessionRepository', return_value=mock_session_repo):
            service = CommandService(mock_session)
            return service

    @pytest_asyncio.fixture
    async def sample_user(self):
        """Create a sample user."""
        return User(
            id=str(uuid4()),
            username="testuser",
            email="test@example.com",
            full_name="Test User"
        )

    @pytest_asyncio.fixture
    async def sample_session(self, sample_user):
        """Create a sample session."""
        return Session(
            id=str(uuid4()),
            user_id=sample_user.id,
            name="Test Session",
            session_type="ssh",
            status="active"
        )

    @pytest_asyncio.fixture
    async def sample_commands(self, sample_session, sample_user):
        """Create comprehensive sample commands with all required fields."""
        commands = []
        now = datetime.now(UTC)
        
        for i in range(15):
            cmd = Command(
                id=str(uuid4()),
                user_id=sample_user.id,
                session_id=sample_session.id,
                command=f"test-command-{i}",
                status="completed" if i % 2 == 0 else "failed",
                exit_code=0 if i % 2 == 0 else 1,
                stdout=f"output {i}\n" if i % 2 == 0 else "",
                stderr="" if i % 2 == 0 else f"error {i}\n",
                working_directory="/home/user",
                command_type="git" if i % 3 == 0 else "file",
                is_dangerous=i % 5 == 0,
                executed_at=now - timedelta(hours=i),
                started_at=now - timedelta(hours=i, minutes=1),
                completed_at=now - timedelta(hours=i) + timedelta(seconds=30),
                duration_ms=1000 + i * 100,
                sequence_number=i,
                created_at=now - timedelta(hours=i, minutes=2)
            )
            cmd.session = sample_session
            commands.append(cmd)
        return commands

    # ===================================================================================
    # SERVICE INITIALIZATION TESTS
    # ===================================================================================

    async def test_service_initialization_patterns_complete(self, mock_session):
        """Test complete CommandService initialization with all patterns and configurations."""
        with patch('app.api.commands.service.CommandRepository') as mock_cmd_repo, \
             patch('app.api.commands.service.SessionRepository') as mock_sess_repo:
            service = CommandService(mock_session)
            
            # Verify basic initialization
            assert service.session == mock_session
            assert service.command_repo is not None
            assert service.session_repo is not None
            
            # Verify command patterns initialization
            assert hasattr(service, 'command_patterns')
            assert len(service.command_patterns) > 0
            assert CommandType.SYSTEM in service.command_patterns
            assert CommandType.FILE in service.command_patterns
            assert CommandType.NETWORK in service.command_patterns
            assert CommandType.GIT in service.command_patterns
            
            # Verify dangerous patterns initialization
            assert hasattr(service, 'dangerous_patterns')
            assert len(service.dangerous_patterns) > 0
            
            # Verify repository initialization calls
            mock_cmd_repo.assert_called_once_with(mock_session)
            mock_sess_repo.assert_called_once_with(mock_session)

    # ===================================================================================
    # COMMAND HISTORY TESTS - Comprehensive Business Logic Coverage
    # ===================================================================================

    async def test_get_command_history_with_complete_entries(self, command_service, sample_user, sample_commands):
        """Test command history retrieval with complete entry processing."""
        command_service.command_repo.get_user_commands_with_session.return_value = sample_commands
        command_service.command_repo.count_user_commands.return_value = len(sample_commands)
        
        result = await command_service.get_command_history(
            user_id=sample_user.id,
            session_id=str(sample_commands[0].session_id),
            offset=0,
            limit=20
        )
        
        assert isinstance(result, CommandHistoryResponse)
        assert len(result.entries) == len(sample_commands)
        assert result.total == len(sample_commands)
        assert result.filters_applied == {"session_id": str(sample_commands[0].session_id)}
        
        # Verify entry completeness
        for i, entry in enumerate(result.entries):
            assert entry.id == str(sample_commands[i].id)
            assert entry.command == sample_commands[i].command
            assert entry.status == CommandStatus(sample_commands[i].status)
            assert entry.command_type == CommandType(sample_commands[i].command_type)
            
        command_service.command_repo.get_user_commands_with_session.assert_called_once_with(
            sample_user.id, offset=0, limit=20
        )

    async def test_get_command_history_filters_incomplete_entries(self, command_service, sample_user, sample_session):
        """Test command history filters out commands with missing required fields."""
        # Create commands with missing fields
        incomplete_commands = [
            Command(id=str(uuid4()), session_id=sample_session.id, command="incomplete1", 
                   executed_at=None, duration_ms=1000),  # Missing executed_at
            Command(id=str(uuid4()), session_id=sample_session.id, command="incomplete2",
                   executed_at=datetime.now(UTC), duration_ms=None),  # Missing duration_ms
            Command(id=str(uuid4()), session_id=sample_session.id, command="complete",
                   executed_at=datetime.now(UTC), duration_ms=1500, stdout="output", stderr="")
        ]
        for cmd in incomplete_commands:
            cmd.session = sample_session

        command_service.command_repo.get_user_commands_with_session.return_value = incomplete_commands
        command_service.command_repo.count_user_commands.return_value = 3
        
        result = await command_service.get_command_history(
            user_id=sample_user.id,
            offset=0,
            limit=10
        )
        
        # Only the complete command should be included
        assert len(result.entries) == 1
        assert result.entries[0].command == "complete"
        assert result.total == 3  # Total count includes all commands

    async def test_get_command_history_pagination_boundaries(self, command_service, sample_user, sample_commands):
        """Test command history with various pagination scenarios."""
        command_service.command_repo.get_user_commands_with_session.return_value = sample_commands[5:10]
        command_service.command_repo.count_user_commands.return_value = 1000
        
        result = await command_service.get_command_history(
            user_id=sample_user.id,
            offset=500,
            limit=100
        )
        
        assert result.offset == 500
        assert result.limit == 100
        assert result.total == 1000
        assert len(result.entries) == 5  # Only 5 commands returned

    async def test_get_command_history_with_session_filtering(self, command_service, sample_user, sample_commands):
        """Test command history with session filtering applied."""
        session_id = str(sample_commands[0].session_id)
        filtered_commands = sample_commands[:8]
        
        command_service.command_repo.get_user_commands_with_session.return_value = filtered_commands
        command_service.command_repo.count_user_commands.return_value = 8
        
        result = await command_service.get_command_history(
            user_id=sample_user.id,
            session_id=session_id,
            offset=0,
            limit=50
        )
        
        assert result.filters_applied == {"session_id": session_id}
        assert len(result.entries) == 8
        # Verify all entries have proper session information
        for entry in result.entries:
            assert entry.session_id == session_id

    async def test_get_command_history_error_handling(self, command_service, sample_user):
        """Test command history comprehensive error handling."""
        command_service.command_repo.get_user_commands_with_session.side_effect = Exception("Database connection failed")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_command_history(
                user_id=sample_user.id,
                offset=0,
                limit=10
            )
        
        assert exc.value.status_code == 500
        assert "Failed to retrieve command history" in str(exc.value.detail)

    # ===================================================================================
    # COMMAND SEARCH TESTS - Advanced Search Functionality
    # ===================================================================================

    async def test_search_commands_comprehensive_filters(self, command_service, sample_user, sample_commands):
        """Test command search with comprehensive filtering options."""
        search_results = sample_commands[:5]
        command_service.command_repo.search_commands.return_value = search_results
        command_service.command_repo.count_commands_with_criteria.return_value = 5
        
        search_request = CommandSearchRequest(
            query="git",
            session_id=str(sample_commands[0].session_id),
            command_type=CommandType.GIT,
            status=CommandStatus.COMPLETED,
            exit_code=0,
            executed_after=datetime.now(UTC) - timedelta(days=30),
            executed_before=datetime.now(UTC),
            min_duration_ms=100,
            max_duration_ms=5000,
            has_output=True,
            has_error=False,
            output_contains="success",
            working_directory="/home/user",
            include_dangerous=False,
            only_dangerous=False,
            sort_by="executed_at",
            sort_order="desc",
            offset=0,
            limit=25
        )
        
        commands, total = await command_service.search_commands(
            user_id=sample_user.id,
            search_request=search_request
        )
        
        assert len(commands) == 5
        assert total == 5
        assert all(isinstance(cmd, CommandResponse) for cmd in commands)
        
        # Verify search was called with correct criteria
        command_service.command_repo.search_commands.assert_called_once()
        call_args = command_service.command_repo.search_commands.call_args[1]
        assert call_args["query"] == "git"
        assert call_args["has_output"] is True
        assert call_args["include_dangerous"] is False

    async def test_search_commands_with_complex_criteria(self, command_service, sample_user, sample_commands):
        """Test command search with complex search criteria combinations."""
        search_results = sample_commands[2:7]
        command_service.command_repo.search_commands.return_value = search_results
        command_service.command_repo.count_commands_with_criteria.return_value = 5
        
        search_request = CommandSearchRequest(
            query="test",
            command_type=CommandType.FILE,
            status=CommandStatus.FAILED,
            has_error=True,
            only_dangerous=True,
            sort_by="duration_ms",
            sort_order="desc"
        )
        
        commands, total = await command_service.search_commands(
            user_id=sample_user.id,
            search_request=search_request
        )
        
        assert len(commands) == 5
        # Verify all commands are properly converted to CommandResponse
        for cmd in commands:
            assert isinstance(cmd, CommandResponse)
            assert cmd.user_id == sample_user.id

    async def test_search_commands_empty_results(self, command_service, sample_user):
        """Test command search with no matching results."""
        command_service.command_repo.search_commands.return_value = []
        command_service.command_repo.count_commands_with_criteria.return_value = 0
        
        search_request = CommandSearchRequest(query="nonexistent")
        
        commands, total = await command_service.search_commands(
            user_id=sample_user.id,
            search_request=search_request
        )
        
        assert len(commands) == 0
        assert total == 0

    async def test_search_commands_error_handling(self, command_service, sample_user):
        """Test search commands error handling scenarios."""
        command_service.command_repo.search_commands.side_effect = Exception("Search index corrupted")
        
        search_request = CommandSearchRequest(query="test")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.search_commands(
                user_id=sample_user.id,
                search_request=search_request
            )
        
        assert exc.value.status_code == 500
        assert "Failed to search commands" in str(exc.value.detail)

    # ===================================================================================
    # COMMAND DETAILS TESTS - Individual Command Access
    # ===================================================================================

    async def test_get_command_details_complete_response(self, command_service, sample_user, sample_commands):
        """Test detailed command information retrieval with complete response."""
        command = sample_commands[0]
        command.user_id = sample_user.id
        command_service.command_repo.get_by_id.return_value = command
        
        result = await command_service.get_command_details(
            user_id=sample_user.id,
            command_id=str(command.id)
        )
        
        assert isinstance(result, CommandResponse)
        assert result.id == str(command.id)
        assert result.user_id == str(command.user_id)
        assert result.command == command.command
        assert result.status == CommandStatus(command.status)
        assert result.command_type == CommandType(command.command_type)
        assert result.duration_ms == command.duration_ms
        assert result.is_dangerous == command.is_dangerous

    async def test_get_command_details_not_found(self, command_service, sample_user):
        """Test command details when command doesn't exist."""
        command_id = str(uuid4())
        command_service.command_repo.get_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_command_details(
                user_id=sample_user.id,
                command_id=command_id
            )
        
        assert exc.value.status_code == 404
        assert "Command not found" in str(exc.value.detail)

    async def test_get_command_details_unauthorized_access(self, command_service, sample_commands):
        """Test command details access by unauthorized user."""
        command = sample_commands[0]
        wrong_user_id = str(uuid4())
        command.user_id = str(uuid4())  # Different user
        command_service.command_repo.get_by_id.return_value = command
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_command_details(
                user_id=wrong_user_id,
                command_id=str(command.id)
            )
        
        assert exc.value.status_code == 404
        assert "Command not found" in str(exc.value.detail)

    async def test_get_command_details_with_signal_parsing(self, command_service, sample_user, sample_commands):
        """Test command details with signal parsing for terminated commands."""
        command = sample_commands[0]
        command.user_id = sample_user.id
        command.signal = "15"  # SIGTERM
        command_service.command_repo.get_by_id.return_value = command
        
        result = await command_service.get_command_details(
            user_id=sample_user.id,
            command_id=str(command.id)
        )
        
        assert result.signal == 15

    async def test_get_command_details_with_invalid_signal(self, command_service, sample_user, sample_commands):
        """Test command details with invalid signal handling."""
        command = sample_commands[0]
        command.user_id = sample_user.id
        command.signal = "invalid"
        command_service.command_repo.get_by_id.return_value = command
        
        result = await command_service.get_command_details(
            user_id=sample_user.id,
            command_id=str(command.id)
        )
        
        assert result.signal is None

    # ===================================================================================
    # COMMAND DELETION TESTS - Authorization and Cleanup
    # ===================================================================================

    async def test_delete_command_success_with_authorization(self, command_service, sample_user, sample_commands):
        """Test successful command deletion with proper authorization."""
        command = sample_commands[0]
        command.user_id = sample_user.id
        command_service.command_repo.get_by_id.return_value = command
        command_service.command_repo.delete.return_value = None
        
        result = await command_service.delete_command(
            user_id=sample_user.id,
            command_id=str(command.id)
        )
        
        assert result is True
        command_service.command_repo.delete.assert_called_once_with(str(command.id))
        command_service.session.commit.assert_called_once()

    async def test_delete_command_not_found(self, command_service, sample_user):
        """Test command deletion when command doesn't exist."""
        command_id = str(uuid4())
        command_service.command_repo.get_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc:
            await command_service.delete_command(
                user_id=sample_user.id,
                command_id=command_id
            )
        
        assert exc.value.status_code == 404
        assert "Command not found" in str(exc.value.detail)

    async def test_delete_command_unauthorized_access(self, command_service, sample_commands):
        """Test command deletion by unauthorized user."""
        command = sample_commands[0]
        wrong_user_id = str(uuid4())
        command.user_id = str(uuid4())  # Different user
        command_service.command_repo.get_by_id.return_value = command
        
        with pytest.raises(HTTPException) as exc:
            await command_service.delete_command(
                user_id=wrong_user_id,
                command_id=str(command.id)
            )
        
        assert exc.value.status_code == 404
        assert "Command not found" in str(exc.value.detail)

    async def test_delete_command_database_error_rollback(self, command_service, sample_user, sample_commands):
        """Test command deletion with database error and rollback."""
        command = sample_commands[0]
        command.user_id = sample_user.id
        command_service.command_repo.get_by_id.return_value = command
        command_service.command_repo.delete.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.delete_command(
                user_id=sample_user.id,
                command_id=str(command.id)
            )
        
        assert exc.value.status_code == 500
        assert "Failed to delete command" in str(exc.value.detail)
        command_service.session.rollback.assert_called_once()

    # ===================================================================================
    # USAGE STATISTICS TESTS - Analytics and Reporting
    # ===================================================================================

    async def test_get_usage_stats_comprehensive_analysis(self, command_service, sample_user):
        """Test comprehensive usage statistics with complete analysis."""
        # Create realistic command data for statistics
        now = datetime.now(UTC)
        mock_commands = []
        
        for i in range(50):
            cmd = MagicMock()
            cmd.command = f"command-{i % 10}"  # Create repeated patterns
            cmd.exit_code = 0 if i % 4 != 0 else 1  # 75% success rate
            cmd.duration_ms = 1000 + (i * 100) % 5000  # Varying durations
            cmd.executed_at = now - timedelta(hours=i % 48)  # Last 2 days
            cmd.command_type = ["git", "file", "system"][i % 3]
            cmd.status = "completed" if cmd.exit_code == 0 else "failed"
            cmd.stdout = f"output-{i}" if cmd.exit_code == 0 else None
            cmd.stderr = f"error-{i}" if cmd.exit_code != 0 else None
            mock_commands.append(cmd)
        
        command_service.command_repo.get_user_commands.return_value = mock_commands
        
        result = await command_service.get_usage_stats(user_id=sample_user.id)
        
        assert isinstance(result, CommandUsageStats)
        assert result.total_commands == 50
        assert result.unique_commands == 10  # 10 unique command patterns
        assert result.successful_commands == 38  # 75% of 50 (rounded)
        assert result.failed_commands == 12
        
        # Verify calculated metrics
        assert result.average_duration_ms > 0
        assert result.median_duration_ms > 0
        assert len(result.most_used_commands) > 0
        assert len(result.longest_running_commands) > 0
        
        # Verify breakdowns
        assert "git" in result.commands_by_type
        assert "completed" in result.commands_by_status

    async def test_get_usage_stats_empty_dataset(self, command_service, sample_user):
        """Test usage statistics with no commands."""
        command_service.command_repo.get_user_commands.return_value = []
        
        result = await command_service.get_usage_stats(user_id=sample_user.id)
        
        assert isinstance(result, CommandUsageStats)
        assert result.total_commands == 0
        assert result.unique_commands == 0
        assert result.successful_commands == 0
        assert result.failed_commands == 0
        assert result.average_duration_ms == 0
        assert result.median_duration_ms == 0
        assert result.total_execution_time_ms == 0
        assert len(result.most_used_commands) == 0
        assert len(result.longest_running_commands) == 0

    async def test_get_usage_stats_time_based_analysis(self, command_service, sample_user):
        """Test usage statistics with time-based command analysis."""
        now = datetime.now(UTC)
        today = now.date()
        
        mock_commands = []
        # Commands from today
        for i in range(5):
            cmd = MagicMock()
            cmd.command = f"today-{i}"
            cmd.exit_code = 0
            cmd.duration_ms = 1000
            cmd.executed_at = datetime.combine(today, datetime.min.time().replace(tzinfo=UTC)) + timedelta(hours=i)
            cmd.command_type = "git"
            cmd.status = "completed"
            cmd.stdout = f"output-{i}"
            cmd.stderr = None
            mock_commands.append(cmd)
        
        # Commands from this week
        for i in range(10):
            cmd = MagicMock()
            cmd.command = f"week-{i}"
            cmd.exit_code = 0
            cmd.duration_ms = 1500
            cmd.executed_at = now - timedelta(days=i % 7)
            cmd.command_type = "file"
            cmd.status = "completed"
            cmd.stdout = f"output-{i}"
            cmd.stderr = None
            mock_commands.append(cmd)
        
        command_service.command_repo.get_user_commands.return_value = mock_commands
        
        result = await command_service.get_usage_stats(user_id=sample_user.id)
        
        assert result.commands_today >= 5
        assert result.commands_this_week >= 10
        assert result.commands_this_month >= 15

    async def test_get_usage_stats_error_handling(self, command_service, sample_user):
        """Test usage statistics error handling."""
        command_service.command_repo.get_user_commands.side_effect = Exception("Analytics service unavailable")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_usage_stats(user_id=sample_user.id)
        
        assert exc.value.status_code == 500
        assert "Failed to get command usage statistics" in str(exc.value.detail)

    # ===================================================================================
    # SESSION COMMAND STATISTICS TESTS
    # ===================================================================================

    async def test_get_session_command_stats_comprehensive(self, command_service, sample_user):
        """Test session command statistics with comprehensive data."""
        mock_stats_data = [
            {
                "session_id": str(uuid4()),
                "session_name": "Dev Session",
                "total_commands": 25,
                "successful_commands": 20,
                "failed_commands": 5,
                "average_duration_ms": 1500,
                "last_command_at": datetime.now(UTC),
                "most_used_command": "git status"
            },
            {
                "session_id": str(uuid4()),
                "session_name": "Prod Session",
                "total_commands": 15,
                "successful_commands": 12,
                "failed_commands": 3,
                "average_duration_ms": 2000,
                "last_command_at": datetime.now(UTC) - timedelta(hours=1),
                "most_used_command": "docker ps"
            }
        ]
        
        command_service.command_repo.get_session_command_stats.return_value = mock_stats_data
        
        result = await command_service.get_session_command_stats(
            user_id=sample_user.id,
            _session_id=None
        )
        
        assert len(result) == 2
        for i, stats in enumerate(result):
            assert isinstance(stats, SessionCommandStats)
            assert stats.session_id == mock_stats_data[i]["session_id"]
            assert stats.session_name == mock_stats_data[i]["session_name"]
            assert stats.total_commands == mock_stats_data[i]["total_commands"]
            assert stats.successful_commands == mock_stats_data[i]["successful_commands"]
            assert stats.failed_commands == mock_stats_data[i]["failed_commands"]
            assert stats.most_used_command == mock_stats_data[i]["most_used_command"]

    async def test_get_session_command_stats_empty_data(self, command_service, sample_user):
        """Test session command statistics with no data."""
        command_service.command_repo.get_session_command_stats.return_value = []
        
        result = await command_service.get_session_command_stats(user_id=sample_user.id)
        
        assert len(result) == 0

    async def test_get_session_command_stats_error_handling(self, command_service, sample_user):
        """Test session command statistics error handling."""
        command_service.command_repo.get_session_command_stats.side_effect = Exception("Session stats error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_session_command_stats(user_id=sample_user.id)
        
        assert exc.value.status_code == 500
        assert "Failed to get session command statistics" in str(exc.value.detail)

    # ===================================================================================
    # FREQUENT COMMANDS TESTS - Pattern Analysis
    # ===================================================================================

    async def test_get_frequent_commands_with_analysis(self, command_service, sample_user):
        """Test frequent commands with pattern analysis."""
        now = datetime.now(UTC)
        cutoff_date = now - timedelta(days=30)
        
        # Create mock commands for pattern analysis
        mock_commands = []
        commands_data = [
            ("git status", 10, 0, 800),
            ("git add .", 8, 0, 500),
            ("ls -la", 15, 0, 200),
            ("cd /home/user", 12, 0, 100),
            ("git commit -m 'update'", 5, 0, 1200)
        ]
        
        for cmd_text, count, exit_code, duration in commands_data:
            for i in range(count):
                cmd = MagicMock()
                cmd.command = cmd_text
                cmd.exit_code = exit_code
                cmd.duration_ms = duration
                cmd.executed_at = now - timedelta(days=i % 25)
                cmd.session_id = str(uuid4())
                mock_commands.append(cmd)
        
        command_service.command_repo.get_user_commands_since.return_value = mock_commands
        
        result = await command_service.get_frequent_commands(
            user_id=sample_user.id,
            days=30,
            min_usage=3
        )
        
        assert isinstance(result, FrequentCommandsResponse)
        assert result.analysis_period_days == 30
        assert len(result.commands) > 0
        assert result.total_analyzed == len(mock_commands)
        
        # Verify frequent commands structure
        for freq_cmd in result.commands:
            assert isinstance(freq_cmd, FrequentCommand)
            assert freq_cmd.usage_count >= 3
            assert freq_cmd.success_rate >= 0
            assert len(freq_cmd.variations) > 0

    async def test_get_frequent_commands_empty_dataset(self, command_service, sample_user):
        """Test frequent commands with no data."""
        command_service.command_repo.get_user_commands_since.return_value = []
        
        result = await command_service.get_frequent_commands(
            user_id=sample_user.id,
            days=30,
            min_usage=3
        )
        
        assert isinstance(result, FrequentCommandsResponse)
        assert len(result.commands) == 0
        assert result.total_analyzed == 0
        assert result.analysis_period_days == 30

    async def test_get_frequent_commands_error_handling(self, command_service, sample_user):
        """Test frequent commands error handling."""
        command_service.command_repo.get_user_commands_since.side_effect = Exception("Pattern analysis failed")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_frequent_commands(
                user_id=sample_user.id,
                days=30,
                min_usage=3
            )
        
        assert exc.value.status_code == 500
        assert "Failed to analyze frequent commands" in str(exc.value.detail)

    # ===================================================================================
    # COMMAND SUGGESTIONS TESTS - AI-Powered Suggestions
    # ===================================================================================

    async def test_get_command_suggestions_context_based(self, command_service, sample_user):
        """Test command suggestions based on various contexts."""
        # Mock recent commands for context
        recent_commands = []
        for i in range(10):
            cmd = MagicMock()
            cmd.command = f"git command-{i}"
            recent_commands.append(cmd)
        
        command_service.command_repo.get_user_recent_commands.return_value = recent_commands
        
        request = CommandSuggestionRequest(
            context="list files in directory",
            max_suggestions=10
        )
        
        result = await command_service.get_command_suggestions(
            user_id=sample_user.id,
            request=request
        )
        
        assert isinstance(result, list)
        assert len(result) <= 10
        
        # Verify suggestions structure
        for suggestion in result:
            assert isinstance(suggestion, CommandSuggestion)
            assert suggestion.command is not None
            assert suggestion.description is not None
            assert 0 <= suggestion.confidence <= 1
            assert suggestion.category in CommandType

    async def test_get_command_suggestions_git_context(self, command_service, sample_user):
        """Test command suggestions for git repository context."""
        command_service.command_repo.get_user_recent_commands.return_value = []
        
        request = CommandSuggestionRequest(
            context="git repository status branch",
            max_suggestions=5
        )
        
        result = await command_service.get_command_suggestions(
            user_id=sample_user.id,
            request=request
        )
        
        # Should include git-specific suggestions
        git_suggestions = [s for s in result if "git" in s.command.lower()]
        assert len(git_suggestions) > 0
        
        # Find git status suggestion
        git_status = next((s for s in git_suggestions if "status" in s.command), None)
        assert git_status is not None
        assert git_status.category == CommandType.GIT

    async def test_get_command_suggestions_system_monitoring_context(self, command_service, sample_user):
        """Test command suggestions for system monitoring context."""
        command_service.command_repo.get_user_recent_commands.return_value = []
        
        request = CommandSuggestionRequest(
            context="monitor system processes cpu memory",
            max_suggestions=8
        )
        
        result = await command_service.get_command_suggestions(
            user_id=sample_user.id,
            request=request
        )
        
        # Should include system monitoring suggestions
        system_suggestions = [s for s in result if s.category == CommandType.SYSTEM]
        assert len(system_suggestions) > 0
        
        # Check for common system commands
        commands = [s.command.lower() for s in system_suggestions]
        assert any("ps" in cmd or "top" in cmd for cmd in commands)

    async def test_get_command_suggestions_personalized(self, command_service, sample_user):
        """Test personalized command suggestions based on user history."""
        # Create mock recent commands with patterns
        recent_commands = []
        frequent_commands = ["git status", "ls -la", "docker ps", "npm start"]
        
        for cmd_text in frequent_commands:
            for i in range(5):  # Each command used 5 times
                cmd = MagicMock()
                cmd.command = cmd_text
                recent_commands.append(cmd)
        
        command_service.command_repo.get_user_recent_commands.return_value = recent_commands
        
        request = CommandSuggestionRequest(
            context="git status repository",
            max_suggestions=10
        )
        
        result = await command_service.get_command_suggestions(
            user_id=sample_user.id,
            request=request
        )
        
        # Should include personalized suggestions based on history
        personalized = [s for s in result if "git status" in s.command]
        assert len(personalized) > 0

    async def test_get_command_suggestions_error_handling(self, command_service, sample_user):
        """Test command suggestions error handling."""
        command_service.command_repo.get_user_recent_commands.side_effect = Exception("Suggestion engine error")
        
        request = CommandSuggestionRequest(
            context="test context",
            max_suggestions=5
        )
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_command_suggestions(
                user_id=sample_user.id,
                request=request
            )
        
        assert exc.value.status_code == 500
        assert "Failed to generate command suggestions" in str(exc.value.detail)

    # ===================================================================================
    # COMMAND METRICS TESTS - Real-time Metrics
    # ===================================================================================

    async def test_get_command_metrics_comprehensive(self, command_service, sample_user):
        """Test comprehensive command metrics calculation."""
        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)
        
        # Create mock recent commands for metrics
        recent_commands = []
        
        # Active/running commands
        for i in range(3):
            cmd = MagicMock()
            cmd.status = "running"
            cmd.executed_at = now - timedelta(minutes=i*10)
            recent_commands.append(cmd)
        
        # Completed commands today
        for i in range(15):
            cmd = MagicMock()
            cmd.status = "completed"
            cmd.exit_code = 0
            cmd.duration_ms = 1000 + i*100
            cmd.executed_at = datetime.combine(now.date(), datetime.min.time().replace(tzinfo=UTC)) + timedelta(hours=i%12)
            cmd.stderr = None
            recent_commands.append(cmd)
        
        # Failed commands today
        for i in range(5):
            cmd = MagicMock()
            cmd.status = "failed"
            cmd.exit_code = 1
            cmd.duration_ms = 500 + i*50
            cmd.executed_at = datetime.combine(now.date(), datetime.min.time().replace(tzinfo=UTC)) + timedelta(hours=i*2)
            cmd.stderr = "permission denied" if i % 2 == 0 else "not found"
            recent_commands.append(cmd)
        
        command_service.command_repo.get_user_commands_since.return_value = recent_commands
        
        result = await command_service.get_command_metrics(user_id=sample_user.id)
        
        assert isinstance(result, CommandMetrics)
        assert result.active_commands == 3
        assert result.completed_today == 15
        assert result.failed_today == 5
        assert result.avg_response_time_ms > 0
        assert 0 <= result.success_rate_24h <= 100
        assert len(result.top_error_types) > 0
        
        # Verify error analysis
        error_types = {error['error_type'] for error in result.top_error_types}
        assert "permission_denied" in error_types or "not_found" in error_types

    async def test_get_command_metrics_empty_dataset(self, command_service, sample_user):
        """Test command metrics with no recent commands."""
        command_service.command_repo.get_user_commands_since.return_value = []
        
        result = await command_service.get_command_metrics(user_id=sample_user.id)
        
        assert isinstance(result, CommandMetrics)
        assert result.active_commands == 0
        assert result.completed_today == 0
        assert result.failed_today == 0
        assert result.avg_response_time_ms == 0
        assert result.success_rate_24h == 100  # Default when no commands
        assert result.total_cpu_time_ms == 0

    async def test_get_command_metrics_error_handling(self, command_service, sample_user):
        """Test command metrics error handling."""
        command_service.command_repo.get_user_commands_since.side_effect = Exception("Metrics service down")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_command_metrics(user_id=sample_user.id)
        
        assert exc.value.status_code == 500
        assert "Failed to get command metrics" in str(exc.value.detail)

    # ===================================================================================
    # PRIVATE HELPER METHOD TESTS - Internal Logic Coverage
    # ===================================================================================

    async def test_classify_command_comprehensive(self, command_service):
        """Test command classification for all supported types."""
        test_cases = [
            # System commands
            ("ps aux", CommandType.SYSTEM),
            ("top -c", CommandType.SYSTEM),
            ("kill -9 1234", CommandType.SYSTEM),
            ("uptime", CommandType.SYSTEM),
            ("whoami", CommandType.SYSTEM),
            
            # File operations
            ("ls -la", CommandType.FILE),
            ("cp file1 file2", CommandType.FILE),
            ("rm -f file", CommandType.FILE),
            ("chmod 755 script", CommandType.FILE),
            ("find . -name '*.py'", CommandType.FILE),
            
            # Network commands
            ("ping google.com", CommandType.NETWORK),
            ("curl -X GET api.example.com", CommandType.NETWORK),
            ("ssh user@host", CommandType.NETWORK),
            ("wget https://example.com/file", CommandType.NETWORK),
            
            # Git commands
            ("git status", CommandType.GIT),
            ("git commit -m 'message'", CommandType.GIT),
            ("git push origin main", CommandType.GIT),
            
            # Package management
            ("apt update", CommandType.PACKAGE),
            ("pip install requests", CommandType.PACKAGE),
            ("npm install", CommandType.PACKAGE),
            
            # Database commands
            ("mysql -u user -p", CommandType.DATABASE),
            ("psql -h localhost", CommandType.DATABASE),
            
            # Unknown commands
            ("custom-tool --help", CommandType.UNKNOWN),
            ("random-command", CommandType.UNKNOWN)
        ]
        
        for command, expected_type in test_cases:
            result = command_service._classify_command(command)
            assert result == expected_type, f"Failed to classify '{command}' as {expected_type}, got {result}"

    async def test_is_dangerous_command_detection(self, command_service):
        """Test comprehensive dangerous command detection."""
        dangerous_commands = [
            "sudo rm -rf /",
            "rm -rf --no-preserve-root /",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1",
            "chmod 777 /etc/passwd",
            "chown -R user:user /",
            ":(){ :|:& };:",  # Fork bomb
            "mv /etc/passwd /dev/null",
            "> /dev/sda",
            "sudo shutdown now",
            "sudo reboot",
            "fdisk /dev/sda"
        ]
        
        safe_commands = [
            "ls -la",
            "git status",
            "echo 'hello'",
            "cd /home/user",
            "cat /etc/hosts",
            "ps aux",
            "mkdir test",
            "touch file.txt",
            "chmod 644 file.txt",
            "grep pattern file.txt"
        ]
        
        for cmd in dangerous_commands:
            assert command_service._is_dangerous_command(cmd) is True, f"Failed to detect '{cmd}' as dangerous"
            
        for cmd in safe_commands:
            assert command_service._is_dangerous_command(cmd) is False, f"Incorrectly flagged '{cmd}' as dangerous"

    async def test_create_command_pattern_generation(self, command_service):
        """Test command pattern generation for template matching."""
        test_cases = [
            ("ls /home/user/documents", "ls /path"),
            ("git clone https://github.com/user/repo.git", "git clone URL"),
            ("curl -X GET https://api.example.com/users/123", "curl -X GET URL"),
            ("ping 192.168.1.1", "ping IP"),
            ("kill -9 12345", "kill -9 N"),
            ("chmod 755 /path/to/file", "chmod N /path"),
            ("docker run -p 8080:80 nginx", "docker run -p N:N nginx")
        ]
        
        for original, expected_pattern in test_cases:
            result = command_service._create_command_pattern(original)
            assert result == expected_pattern, f"Pattern for '{original}' should be '{expected_pattern}', got '{result}'"

    async def test_analyze_command_patterns_comprehensive(self, command_service):
        """Test comprehensive command pattern analysis."""
        # Create realistic command data for pattern analysis
        commands = []
        base_commands = [
            "git status",
            "git add .",
            "git commit -m 'update'",
            "ls -la",
            "ls /home/user",
            "cd /home/user",
            "cd /var/log"
        ]
        
        for cmd_text in base_commands:
            for i in range(3):  # Each command appears 3 times
                cmd = MagicMock()
                cmd.command = cmd_text
                cmd.exit_code = 0 if i < 2 else 1  # 2/3 success rate
                cmd.duration_ms = 1000 + i*100
                cmd.executed_at = datetime.now(UTC) - timedelta(hours=i)
                commands.append(cmd)
        
        result = command_service._analyze_command_patterns(commands, min_usage=2)
        
        assert isinstance(result, dict)
        assert len(result) > 0
        
        # Verify pattern analysis results
        for pattern, data in result.items():
            assert data["count"] >= 2
            assert 0 <= data["success_rate"] <= 100
            assert data["average_duration"] > 0
            assert len(data["variations"]) > 0

    async def test_suggestion_helper_methods_comprehensive(self, command_service):
        """Test all command suggestion helper methods."""
        # Test file operation suggestions
        file_suggestions = command_service._get_file_operation_suggestions("list files directory")
        assert len(file_suggestions) > 0
        assert any("ls" in s.command for s in file_suggestions)
        
        # Test system monitoring suggestions
        system_suggestions = command_service._get_system_monitoring_suggestions("process memory cpu")
        assert len(system_suggestions) > 0
        assert any("ps" in s.command or "top" in s.command for s in system_suggestions)
        
        # Test network suggestions
        network_suggestions = command_service._get_network_suggestions("ping connection")
        assert len(network_suggestions) > 0
        assert any("ping" in s.command for s in network_suggestions)
        
        # Test git suggestions
        git_suggestions = command_service._get_git_suggestions("repository status")
        assert len(git_suggestions) > 0
        assert any("git" in s.command for s in git_suggestions)

    async def test_personalized_suggestions_with_history(self, command_service):
        """Test personalized suggestions based on command history."""
        # Create mock command history
        recent_commands = []
        frequent_cmds = ["git status", "docker ps", "npm test", "ls -la"]
        
        for cmd_text in frequent_cmds:
            for i in range(5):
                cmd = MagicMock()
                cmd.command = cmd_text
                recent_commands.append(cmd)
        
        suggestions = command_service._get_personalized_suggestions(recent_commands, "git repository")
        
        assert len(suggestions) > 0
        # Should include git status since it's frequent and matches context
        git_suggestions = [s for s in suggestions if "git status" in s.command]
        assert len(git_suggestions) > 0

    # ===================================================================================
    # INTEGRATION AND WORKFLOW TESTS
    # ===================================================================================

    async def test_complete_command_lifecycle_workflow(self, command_service, sample_user, sample_commands):
        """Test complete command service workflow integration."""
        command = sample_commands[0]
        command.user_id = sample_user.id
        
        # Setup mocks for full workflow
        command_service.command_repo.search_commands.return_value = sample_commands[:3]
        command_service.command_repo.count_commands_with_criteria.return_value = 3
        command_service.command_repo.get_by_id.return_value = command
        command_service.command_repo.delete.return_value = None
        command_service.command_repo.get_user_commands_with_session.return_value = sample_commands
        command_service.command_repo.count_user_commands.return_value = len(sample_commands)
        
        # 1. Search for commands
        search_request = CommandSearchRequest(query="test")
        search_results, total = await command_service.search_commands(
            user_id=sample_user.id,
            search_request=search_request
        )
        assert len(search_results) == 3
        assert total == 3
        
        # 2. Get command details
        details = await command_service.get_command_details(
            user_id=sample_user.id,
            command_id=str(command.id)
        )
        assert details.id == str(command.id)
        
        # 3. Get command history
        history = await command_service.get_command_history(
            user_id=sample_user.id,
            offset=0,
            limit=50
        )
        assert len(history.entries) == len(sample_commands)
        
        # 4. Delete command
        delete_result = await command_service.delete_command(
            user_id=sample_user.id,
            command_id=str(command.id)
        )
        assert delete_result is True
        
        # Verify all repository methods were called
        command_service.command_repo.search_commands.assert_called_once()
        command_service.command_repo.get_by_id.assert_called()
        command_service.command_repo.delete.assert_called_once()

    async def test_concurrent_operations_handling(self, command_service, sample_user, sample_commands):
        """Test command service handling of concurrent operations."""
        import asyncio
        
        command = sample_commands[0]
        command.user_id = sample_user.id
        command_service.command_repo.get_by_id.return_value = command
        
        # Simulate concurrent command detail requests
        tasks = []
        for _ in range(10):
            task = asyncio.create_task(
                command_service.get_command_details(
                    user_id=sample_user.id,
                    command_id=str(command.id)
                )
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should succeed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 10
        
        # All should return the same command
        for result in successful_results:
            assert result.id == str(command.id)

    async def test_error_recovery_and_consistency(self, command_service, sample_user):
        """Test error recovery and data consistency."""
        # Test database error with proper rollback
        command_service.command_repo.get_user_commands_with_session.side_effect = Exception("DB Error")
        
        with pytest.raises(HTTPException):
            await command_service.get_command_history(
                user_id=sample_user.id,
                offset=0,
                limit=10
            )
        
        # Reset mock and test recovery
        command_service.command_repo.get_user_commands_with_session.side_effect = None
        command_service.command_repo.get_user_commands_with_session.return_value = []
        command_service.command_repo.count_user_commands.return_value = 0
        
        # Should work after error recovery
        result = await command_service.get_command_history(
            user_id=sample_user.id,
            offset=0,
            limit=10
        )
        assert len(result.entries) == 0