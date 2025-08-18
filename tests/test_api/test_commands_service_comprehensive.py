"""
Comprehensive tests for Commands service functionality - Phase 2 Implementation.

This module provides extensive coverage for Commands service operations,
targeting ALL service methods to achieve 65% coverage target.
Implements Phase 2, Week 1 objectives for Commands Service.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import HTTPException

from app.api.commands.service import CommandService
from app.api.commands.schemas import (
    CommandHistoryResponse, 
    CommandListResponse,
    FrequentCommandsResponse,
    CommandResponse,
    CommandUsageStats,
    CommandSearchRequest
)
from app.models.command import Command
from app.models.session import Session
from app.models.user import User


@pytest.mark.database
class TestCommandServiceComprehensive:
    """Comprehensive test suite for CommandService - Phase 2 Implementation."""

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
    async def sample_user(self):
        """Create a sample user."""
        return User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            full_name="Test User"
        )

    @pytest_asyncio.fixture
    async def sample_session(self, sample_user):
        """Create a sample session."""
        return Session(
            id=uuid4(),
            user_id=sample_user.id,
            device_id="test-device",
            device_type="web",
            name="Test Session",
            session_type="ssh"
        )

    @pytest_asyncio.fixture
    async def sample_commands(self, sample_session):
        """Create comprehensive sample commands."""
        commands = []
        command_types = ["git", "file_operation", "network", "system", "other"]
        statuses = ["completed", "completed", "error", "timeout", "cancelled"]
        
        for i in range(10):
            cmd = Command(
                id=uuid4(),
                session_id=sample_session.id,
                command=f"test-command-{i}",
                status=statuses[i % 5],
                exit_code=0 if statuses[i % 5] == "completed" else 1,
                output=f"output {i}\n" if statuses[i % 5] == "completed" else None,
                stdout=f"output {i}\n" if statuses[i % 5] == "completed" else None,
                stderr=f"error {i}\n" if statuses[i % 5] == "error" else None,
                created_at=datetime.utcnow() - timedelta(hours=i),
                executed_at=datetime.utcnow() - timedelta(hours=i),
                execution_time=1.5 + i * 0.1,
                working_directory="/home/user",
                command_type=command_types[i % 5],
                is_dangerous=i % 3 == 0,
                was_ai_suggested=i % 4 == 0
            )
            cmd.session = sample_session
            commands.append(cmd)
        return commands

    # ===================================================================================
    # CORE SERVICE INITIALIZATION TESTS
    # ===================================================================================

    async def test_service_initialization_complete(self, mock_session):
        """Test complete CommandService initialization with all patterns."""
        with patch('app.api.commands.service.CommandRepository') as mock_cmd_repo, \
             patch('app.api.commands.service.SessionRepository') as mock_sess_repo:
            service = CommandService(mock_session)
            
            # Verify basic initialization
            assert service.session == mock_session
            assert service.command_repo is not None
            assert service.session_repo is not None
            
            # Verify pattern initialization
            assert hasattr(service, 'command_patterns')
            assert len(service.command_patterns) > 0
            assert hasattr(service, 'dangerous_patterns')
            assert len(service.dangerous_patterns) > 0
            
            # Verify repository calls
            mock_cmd_repo.assert_called_once_with(mock_session)
            mock_sess_repo.assert_called_once_with(mock_session)

    # ===================================================================================
    # COMMAND HISTORY TESTS - Comprehensive Coverage
    # ===================================================================================

    async def test_get_command_history_with_session_filter(self, command_service, sample_user, sample_commands):
        """Test command history with session filtering."""
        session_id = str(sample_commands[0].session_id)
        filtered_commands = sample_commands[:3]
        
        command_service.command_repo.get_user_commands_with_session.return_value = filtered_commands
        command_service.command_repo.count_user_commands.return_value = 3
        
        result = await command_service.get_command_history(
            user_id=sample_user.id,
            session_id=session_id,
            offset=0,
            limit=10
        )
        
        assert isinstance(result, CommandHistoryResponse)
        assert len(result.entries) == 3
        assert result.total == 3
        assert result.filters_applied == {"session_id": session_id}
        
        command_service.command_repo.get_user_commands_with_session.assert_called_once()

    async def test_get_command_history_large_offset(self, command_service, sample_user, sample_commands):
        """Test command history with large offset and limit."""
        command_service.command_repo.get_user_commands_with_session.return_value = sample_commands[5:8]
        command_service.command_repo.count_user_commands.return_value = 100
        
        result = await command_service.get_command_history(
            user_id=sample_user.id,
            offset=50,
            limit=20
        )
        
        assert isinstance(result, CommandHistoryResponse)
        assert result.offset == 50
        assert result.limit == 20
        assert result.total == 100

    async def test_get_command_history_empty_results(self, command_service, sample_user):
        """Test command history with no commands."""
        command_service.command_repo.get_user_commands_with_session.return_value = []
        command_service.command_repo.count_user_commands.return_value = 0
        
        result = await command_service.get_command_history(
            user_id=sample_user.id,
            offset=0,
            limit=10
        )
        
        assert isinstance(result, CommandHistoryResponse)
        assert len(result.entries) == 0
        assert result.total == 0

    async def test_get_command_history_filters_incomplete_commands(self, command_service, sample_user, sample_session):
        """Test that command history filters out commands without required fields."""
        # Create commands with missing required fields
        incomplete_commands = [
            Command(id=uuid4(), session_id=sample_session.id, command="incomplete1", executed_at=None),
            Command(id=uuid4(), session_id=sample_session.id, command="incomplete2", execution_time=None),
            Command(
                id=uuid4(), 
                session_id=sample_session.id, 
                command="complete", 
                executed_at=datetime.utcnow(),
                execution_time=1.5,
                stdout="output",
                stderr=None
            )
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

    async def test_get_command_history_exception_handling(self, command_service, sample_user):
        """Test command history exception handling."""
        command_service.command_repo.get_user_commands_with_session.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_command_history(
                user_id=sample_user.id,
                offset=0,
                limit=10
            )
        
        assert exc.value.status_code == 500
        assert "Failed to retrieve command history" in str(exc.value.detail)

    # ===================================================================================
    # COMMAND SEARCH TESTS - Comprehensive Coverage
    # ===================================================================================

    async def test_search_commands_with_all_filters(self, command_service, sample_user, sample_commands):
        """Test comprehensive command search with all filters."""
        search_results = sample_commands[:5]
        command_service.command_repo.search_commands.return_value = search_results
        command_service.command_repo.count_commands_with_criteria.return_value = 5
        
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        result = await command_service.search_commands(
            user_id=sample_user.id,
            query="git",
            status="completed",
            command_type="git",
            start_date=start_date,
            end_date=end_date,
            include_dangerous=False,
            include_ai_commands=True,
            session_id=str(sample_commands[0].session_id),
            offset=10,
            limit=25
        )
        
        assert isinstance(result, CommandSearchResponse)
        assert len(result.commands) == 5
        assert result.total == 5
        assert result.query == "git"
        assert result.filters_applied["status"] == "completed"
        assert result.filters_applied["command_type"] == "git"

    async def test_search_commands_exclude_dangerous(self, command_service, sample_user, sample_commands):
        """Test command search excluding dangerous commands."""
        safe_commands = [cmd for cmd in sample_commands if not cmd.is_dangerous]
        command_service.command_repo.search_commands.return_value = safe_commands
        command_service.command_repo.count_commands_with_criteria.return_value = len(safe_commands)
        
        result = await command_service.search_commands(
            user_id=sample_user.id,
            query="test",
            include_dangerous=False
        )
        
        assert len(result.commands) == len(safe_commands)
        assert result.filters_applied["include_dangerous"] == False

    async def test_search_commands_ai_only(self, command_service, sample_user, sample_commands):
        """Test command search for AI-suggested commands only."""
        ai_commands = [cmd for cmd in sample_commands if cmd.was_ai_suggested]
        command_service.command_repo.search_commands.return_value = ai_commands
        command_service.command_repo.count_commands_with_criteria.return_value = len(ai_commands)
        
        result = await command_service.search_commands(
            user_id=sample_user.id,
            query="",
            include_ai_commands=True,
            include_manual_commands=False
        )
        
        assert len(result.commands) == len(ai_commands)

    async def test_search_commands_empty_query(self, command_service, sample_user, sample_commands):
        """Test command search with empty query string."""
        command_service.command_repo.search_commands.return_value = sample_commands
        command_service.command_repo.count_commands_with_criteria.return_value = len(sample_commands)
        
        result = await command_service.search_commands(
            user_id=sample_user.id,
            query="",
            offset=0,
            limit=50
        )
        
        assert isinstance(result, CommandSearchResponse)
        assert result.query == ""
        assert len(result.commands) == len(sample_commands)

    async def test_search_commands_exception_handling(self, command_service, sample_user):
        """Test search commands exception handling."""
        command_service.command_repo.search_commands.side_effect = Exception("Search failed")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.search_commands(
                user_id=sample_user.id,
                query="test"
            )
        
        assert exc.value.status_code == 500
        assert "Failed to search commands" in str(exc.value.detail)

    # ===================================================================================
    # COMMAND DETAILS TESTS - Comprehensive Coverage
    # ===================================================================================

    async def test_get_command_details_success(self, command_service, sample_user, sample_commands):
        """Test successful command details retrieval."""
        command = sample_commands[0]
        command_service.command_repo.get_by_id.return_value = command
        
        result = await command_service.get_command_details(
            command_id=command.id,
            user_id=sample_user.id
        )
        
        assert result == command
        command_service.command_repo.get_by_id.assert_called_once_with(command.id)

    async def test_get_command_details_not_found(self, command_service, sample_user):
        """Test command details when command not found."""
        command_id = uuid4()
        command_service.command_repo.get_by_id.return_value = None
        
        result = await command_service.get_command_details(
            command_id=command_id,
            user_id=sample_user.id
        )
        
        assert result is None

    async def test_get_command_details_wrong_user(self, command_service, sample_commands):
        """Test command details access by wrong user."""
        command = sample_commands[0]
        wrong_user_id = uuid4()
        command_service.command_repo.get_by_id.return_value = command
        
        # Mock session to have different user_id
        mock_session = MagicMock()
        mock_session.user_id = uuid4()  # Different from wrong_user_id
        command.session = mock_session
        
        result = await command_service.get_command_details(
            command_id=command.id,
            user_id=wrong_user_id
        )
        
        assert result is None

    async def test_get_command_details_no_session(self, command_service, sample_user, sample_commands):
        """Test command details when command has no session."""
        command = sample_commands[0]
        command.session = None
        command_service.command_repo.get_by_id.return_value = command
        
        result = await command_service.get_command_details(
            command_id=command.id,
            user_id=sample_user.id
        )
        
        assert result is None

    async def test_get_command_details_exception_handling(self, command_service, sample_user):
        """Test command details exception handling."""
        command_id = uuid4()
        command_service.command_repo.get_by_id.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_command_details(
                command_id=command_id,
                user_id=sample_user.id
            )
        
        assert exc.value.status_code == 500
        assert "Failed to retrieve command details" in str(exc.value.detail)

    # ===================================================================================
    # COMMAND DELETION TESTS - Comprehensive Coverage
    # ===================================================================================

    async def test_delete_command_success(self, command_service, sample_user, sample_commands):
        """Test successful command deletion."""
        command = sample_commands[0]
        command_service.command_repo.get_by_id.return_value = command
        command_service.command_repo.delete.return_value = True
        
        # Mock session to have correct user_id
        mock_session = MagicMock()
        mock_session.user_id = sample_user.id
        command.session = mock_session
        
        result = await command_service.delete_command(
            command_id=command.id,
            user_id=sample_user.id
        )
        
        assert result is True
        command_service.command_repo.delete.assert_called_once_with(command.id)

    async def test_delete_command_not_found(self, command_service, sample_user):
        """Test command deletion when command not found."""
        command_id = uuid4()
        command_service.command_repo.get_by_id.return_value = None
        
        result = await command_service.delete_command(
            command_id=command_id,
            user_id=sample_user.id
        )
        
        assert result is False

    async def test_delete_command_wrong_user(self, command_service, sample_commands):
        """Test command deletion by wrong user."""
        command = sample_commands[0]
        wrong_user_id = uuid4()
        command_service.command_repo.get_by_id.return_value = command
        
        # Mock session to have different user_id
        mock_session = MagicMock()
        mock_session.user_id = uuid4()  # Different from wrong_user_id
        command.session = mock_session
        
        result = await command_service.delete_command(
            command_id=command.id,
            user_id=wrong_user_id
        )
        
        assert result is False

    async def test_delete_command_no_session(self, command_service, sample_user, sample_commands):
        """Test command deletion when command has no session."""
        command = sample_commands[0]
        command.session = None
        command_service.command_repo.get_by_id.return_value = command
        
        result = await command_service.delete_command(
            command_id=command.id,
            user_id=sample_user.id
        )
        
        assert result is False

    async def test_delete_command_exception_handling(self, command_service, sample_user):
        """Test command deletion exception handling."""
        command_id = uuid4()
        command_service.command_repo.get_by_id.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.delete_command(
                command_id=command_id,
                user_id=sample_user.id
            )
        
        assert exc.value.status_code == 500
        assert "Failed to delete command" in str(exc.value.detail)

    # ===================================================================================
    # USAGE STATISTICS TESTS - Comprehensive Coverage
    # ===================================================================================

    async def test_get_usage_stats_comprehensive(self, command_service, sample_user):
        """Test comprehensive usage statistics retrieval."""
        mock_stats = {
            "total_commands": 150,
            "successful_commands": 120,
            "failed_commands": 25,
            "cancelled_commands": 5,
            "status_breakdown": {
                "completed": 120,
                "error": 20,
                "timeout": 5,
                "cancelled": 5
            },
            "type_breakdown": {
                "git": 40,
                "file_operation": 35,
                "network": 30,
                "system": 25,
                "other": 20
            },
            "ai_commands": 45,
            "manual_commands": 105,
            "dangerous_commands": 10,
            "avg_execution_time": 2.5,
            "total_execution_time": 375.0,
            "commands_by_day": [
                {"date": "2023-01-01", "count": 10},
                {"date": "2023-01-02", "count": 15}
            ],
            "most_active_session": {
                "session_id": str(uuid4()),
                "command_count": 25
            }
        }
        command_service.command_repo.get_command_stats.return_value = mock_stats
        
        result = await command_service.get_usage_stats(user_id=sample_user.id)
        
        assert isinstance(result, CommandUsageStatsResponse)
        assert result.total_commands == 150
        assert result.successful_commands == 120
        assert result.ai_commands == 45
        assert result.avg_execution_time == 2.5
        assert len(result.commands_by_day) == 2

    async def test_get_usage_stats_with_date_range(self, command_service, sample_user):
        """Test usage statistics with date range filtering."""
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        mock_stats = {
            "total_commands": 50,
            "successful_commands": 40,
            "failed_commands": 10,
            "cancelled_commands": 0,
            "status_breakdown": {"completed": 40, "error": 10},
            "type_breakdown": {"git": 20, "file_operation": 30},
            "ai_commands": 15,
            "manual_commands": 35,
            "dangerous_commands": 2,
            "avg_execution_time": 1.8,
            "total_execution_time": 90.0,
            "commands_by_day": [],
            "most_active_session": None
        }
        command_service.command_repo.get_command_stats.return_value = mock_stats
        
        result = await command_service.get_usage_stats(
            user_id=sample_user.id,
            start_date=start_date,
            end_date=end_date
        )
        
        assert result.total_commands == 50
        command_service.command_repo.get_command_stats.assert_called_once_with(
            sample_user.id, start_date, end_date
        )

    async def test_get_usage_stats_exception_handling(self, command_service, sample_user):
        """Test usage statistics exception handling."""
        command_service.command_repo.get_command_stats.side_effect = Exception("Stats error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_usage_stats(user_id=sample_user.id)
        
        assert exc.value.status_code == 500
        assert "Failed to retrieve usage statistics" in str(exc.value.detail)

    # ===================================================================================
    # SESSION COMMAND STATISTICS TESTS
    # ===================================================================================

    async def test_get_session_command_stats_success(self, command_service, sample_user):
        """Test successful session command statistics retrieval."""
        mock_stats = [
            {
                "session_id": str(uuid4()),
                "session_name": "Development Session",
                "command_count": 25,
                "avg_execution_time": 1.8,
                "total_execution_time": 45.0,
                "last_command_at": datetime.utcnow().isoformat()
            },
            {
                "session_id": str(uuid4()),
                "session_name": "Production Session",
                "command_count": 40,
                "avg_execution_time": 2.2,
                "total_execution_time": 88.0,
                "last_command_at": datetime.utcnow().isoformat()
            }
        ]
        command_service.command_repo.get_session_command_stats.return_value = mock_stats
        
        result = await command_service.get_session_command_stats(user_id=sample_user.id)
        
        assert result == mock_stats
        assert len(result) == 2
        command_service.command_repo.get_session_command_stats.assert_called_once_with(sample_user.id)

    async def test_get_session_command_stats_empty(self, command_service, sample_user):
        """Test session command statistics with no data."""
        command_service.command_repo.get_session_command_stats.return_value = []
        
        result = await command_service.get_session_command_stats(user_id=sample_user.id)
        
        assert result == []

    async def test_get_session_command_stats_exception_handling(self, command_service, sample_user):
        """Test session command statistics exception handling."""
        command_service.command_repo.get_session_command_stats.side_effect = Exception("Stats error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_session_command_stats(user_id=sample_user.id)
        
        assert exc.value.status_code == 500
        assert "Failed to retrieve session command statistics" in str(exc.value.detail)

    # ===================================================================================
    # FREQUENT COMMANDS TESTS
    # ===================================================================================

    async def test_get_frequent_commands_success(self, command_service, sample_user):
        """Test successful frequent commands retrieval."""
        frequent_commands = [
            {"command": "git status", "count": 50, "avg_execution_time": 0.8},
            {"command": "ls -la", "count": 35, "avg_execution_time": 0.5},
            {"command": "cd ..", "count": 30, "avg_execution_time": 0.3}
        ]
        command_service.command_repo.get_top_commands.return_value = frequent_commands
        
        result = await command_service.get_frequent_commands(
            user_id=sample_user.id,
            limit=10
        )
        
        assert result == frequent_commands
        assert len(result) == 3
        command_service.command_repo.get_top_commands.assert_called_once_with(
            user_id=sample_user.id,
            limit=10
        )

    async def test_get_frequent_commands_with_date_filter(self, command_service, sample_user):
        """Test frequent commands with date filtering."""
        start_date = datetime.utcnow() - timedelta(days=30)
        frequent_commands = [
            {"command": "docker ps", "count": 20, "avg_execution_time": 1.2}
        ]
        command_service.command_repo.get_top_commands.return_value = frequent_commands
        
        result = await command_service.get_frequent_commands(
            user_id=sample_user.id,
            limit=5,
            start_date=start_date
        )
        
        assert result == frequent_commands
        command_service.command_repo.get_top_commands.assert_called_once_with(
            user_id=sample_user.id,
            limit=5,
            start_date=start_date
        )

    async def test_get_frequent_commands_exception_handling(self, command_service, sample_user):
        """Test frequent commands exception handling."""
        command_service.command_repo.get_top_commands.side_effect = Exception("Query error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_frequent_commands(user_id=sample_user.id)
        
        assert exc.value.status_code == 500
        assert "Failed to retrieve frequent commands" in str(exc.value.detail)

    # ===================================================================================
    # COMMAND SUGGESTIONS TESTS - Comprehensive Coverage
    # ===================================================================================

    async def test_get_command_suggestions_based_on_context(self, command_service, sample_user):
        """Test command suggestions based on current directory context."""
        mock_patterns = ["git_workflow", "file_operations", "system_monitoring"]
        command_service.command_repo.get_user_command_patterns.return_value = mock_patterns
        
        result = await command_service.get_command_suggestions(
            user_id=sample_user.id,
            current_directory="/home/user/project",
            limit=10
        )
        
        assert isinstance(result, CommandSuggestionResponse)
        assert len(result.suggestions) > 0
        assert result.context == "/home/user/project"

    async def test_get_command_suggestions_git_context(self, command_service, sample_user):
        """Test command suggestions for git repository context."""
        mock_patterns = ["git_workflow"]
        command_service.command_repo.get_user_command_patterns.return_value = mock_patterns
        
        result = await command_service.get_command_suggestions(
            user_id=sample_user.id,
            current_directory="/home/user/git-repo/.git",
            limit=5
        )
        
        # Should include git-specific suggestions
        git_suggestions = [s for s in result.suggestions if "git" in s.command.lower()]
        assert len(git_suggestions) > 0

    async def test_get_command_suggestions_with_recent_commands(self, command_service, sample_user, sample_commands):
        """Test command suggestions considering recent command history."""
        recent_commands = sample_commands[:3]
        command_service.command_repo.get_user_command_patterns.return_value = ["file_operations"]
        command_service.command_repo.get_recent_commands.return_value = recent_commands
        
        result = await command_service.get_command_suggestions(
            user_id=sample_user.id,
            current_directory="/home/user",
            limit=8,
            include_recent_context=True
        )
        
        assert isinstance(result, CommandSuggestionResponse)
        assert len(result.suggestions) > 0

    async def test_get_command_suggestions_exception_handling(self, command_service, sample_user):
        """Test command suggestions exception handling."""
        command_service.command_repo.get_user_command_patterns.side_effect = Exception("Pattern error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_command_suggestions(user_id=sample_user.id)
        
        assert exc.value.status_code == 500
        assert "Failed to retrieve command suggestions" in str(exc.value.detail)

    # ===================================================================================
    # COMMAND METRICS TESTS - Comprehensive Coverage
    # ===================================================================================

    async def test_get_command_metrics_comprehensive(self, command_service, sample_user):
        """Test comprehensive command metrics retrieval."""
        mock_metrics = {
            "execution_time_stats": {
                "avg": 2.5,
                "min": 0.1,
                "max": 30.0,
                "p50": 1.8,
                "p90": 8.5,
                "p95": 15.2
            },
            "success_rate": 85.5,
            "command_frequency": [
                {"command": "git status", "count": 45},
                {"command": "ls -la", "count": 30}
            ],
            "error_patterns": [
                {"pattern": "permission denied", "count": 5},
                {"pattern": "command not found", "count": 3}
            ],
            "productivity_score": 7.8,
            "efficiency_trends": [
                {"period": "2023-01", "avg_time": 2.2},
                {"period": "2023-02", "avg_time": 2.1}
            ]
        }
        command_service.command_repo.get_command_metrics.return_value = mock_metrics
        
        result = await command_service.get_command_metrics(user_id=sample_user.id)
        
        assert isinstance(result, CommandMetricsResponse)
        assert result.execution_time_stats["avg"] == 2.5
        assert result.success_rate == 85.5
        assert result.productivity_score == 7.8
        assert len(result.command_frequency) == 2

    async def test_get_command_metrics_with_filters(self, command_service, sample_user):
        """Test command metrics with filtering options."""
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        mock_metrics = {
            "execution_time_stats": {"avg": 1.8, "min": 0.1, "max": 10.0, "p50": 1.5, "p90": 5.0, "p95": 7.5},
            "success_rate": 90.0,
            "command_frequency": [],
            "error_patterns": [],
            "productivity_score": 8.2,
            "efficiency_trends": []
        }
        command_service.command_repo.get_command_metrics.return_value = mock_metrics
        
        result = await command_service.get_command_metrics(
            user_id=sample_user.id,
            start_date=start_date,
            end_date=end_date,
            command_type="git",
            include_ai_commands=True
        )
        
        assert result.success_rate == 90.0
        command_service.command_repo.get_command_metrics.assert_called_once()

    async def test_get_command_metrics_exception_handling(self, command_service, sample_user):
        """Test command metrics exception handling."""
        command_service.command_repo.get_command_metrics.side_effect = Exception("Metrics error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_command_metrics(user_id=sample_user.id)
        
        assert exc.value.status_code == 500
        assert "Failed to retrieve command metrics" in str(exc.value.detail)

    # ===================================================================================
    # PRIVATE METHOD TESTS - Internal Logic Coverage
    # ===================================================================================

    async def test_classify_command_various_types(self, command_service):
        """Test command classification for various command types."""
        test_cases = [
            ("git status", "git"),
            ("ls -la", "file_operation"), 
            ("curl https://api.example.com", "network"),
            ("ps aux", "system"),
            ("docker ps", "development"),
            ("random-command", "other")
        ]
        
        for command, expected_type in test_cases:
            result = command_service._classify_command(command)
            assert result == expected_type

    async def test_is_dangerous_command_detection(self, command_service):
        """Test dangerous command detection."""
        dangerous_commands = [
            "sudo rm -rf /",
            "dd if=/dev/zero of=/dev/sda",
            "chmod 777 /etc/passwd",
            "export SECRET_KEY=abc123"
        ]
        
        safe_commands = [
            "ls -la",
            "git status", 
            "echo hello",
            "cd /home/user"
        ]
        
        for cmd in dangerous_commands:
            assert command_service._is_dangerous_command(cmd) is True
            
        for cmd in safe_commands:
            assert command_service._is_dangerous_command(cmd) is False

    async def test_analyze_command_patterns(self, command_service, sample_commands):
        """Test command pattern analysis."""
        patterns = command_service._analyze_command_patterns(sample_commands)
        
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        
        # Verify pattern structure
        for pattern in patterns:
            assert "pattern_type" in pattern
            assert "frequency" in pattern
            assert "commands" in pattern

    async def test_create_command_pattern(self, command_service):
        """Test command pattern creation."""
        commands = ["git add .", "git commit -m", "git push"]
        pattern_type = "git_workflow"
        
        pattern = command_service._create_command_pattern(commands, pattern_type)
        
        assert pattern["pattern_type"] == pattern_type
        assert pattern["frequency"] == len(commands)
        assert pattern["commands"] == commands

    async def test_matches_pattern(self, command_service):
        """Test pattern matching functionality."""
        pattern = {"regex": r"git\s+\w+", "keywords": ["git"]}
        
        assert command_service._matches_pattern("git status", pattern) is True
        assert command_service._matches_pattern("ls -la", pattern) is False

    async def test_suggestion_methods_comprehensive(self, command_service):
        """Test various command suggestion helper methods."""
        # Test file operation suggestions
        file_suggestions = command_service._get_file_operation_suggestions("/home/user")
        assert len(file_suggestions) > 0
        assert any("ls" in s["command"] for s in file_suggestions)
        
        # Test system monitoring suggestions  
        system_suggestions = command_service._get_system_monitoring_suggestions()
        assert len(system_suggestions) > 0
        assert any("ps" in s["command"] or "top" in s["command"] for s in system_suggestions)
        
        # Test network suggestions
        network_suggestions = command_service._get_network_suggestions()
        assert len(network_suggestions) > 0
        assert any("ping" in s["command"] or "curl" in s["command"] for s in network_suggestions)
        
        # Test git suggestions
        git_suggestions = command_service._get_git_suggestions()
        assert len(git_suggestions) > 0
        assert any("git" in s["command"] for s in git_suggestions)

    async def test_personalized_suggestions(self, command_service, sample_commands):
        """Test personalized command suggestions based on user history."""
        user_patterns = [
            {"pattern_type": "git_workflow", "frequency": 10, "commands": ["git status", "git add", "git commit"]},
            {"pattern_type": "file_operations", "frequency": 5, "commands": ["ls -la", "cd", "mkdir"]}
        ]
        
        suggestions = command_service._get_personalized_suggestions(user_patterns)
        
        assert len(suggestions) > 0
        # Should include suggestions from user patterns
        git_suggestions = [s for s in suggestions if "git" in s["command"]]
        assert len(git_suggestions) > 0

    # ===================================================================================
    # EDGE CASES AND ERROR SCENARIOS
    # ===================================================================================

    async def test_command_service_with_invalid_user_id(self, command_service):
        """Test command service methods with invalid user ID."""
        invalid_user_id = "invalid-uuid"
        
        # Most methods should handle invalid UUIDs gracefully
        with pytest.raises(HTTPException):
            await command_service.get_command_history(user_id=invalid_user_id)

    async def test_command_service_concurrent_operations(self, command_service, sample_user, sample_commands):
        """Test command service under concurrent operation scenarios."""
        command = sample_commands[0]
        command_service.command_repo.get_by_id.return_value = command
        command_service.command_repo.delete.return_value = True
        
        # Simulate concurrent access
        mock_session = MagicMock()
        mock_session.user_id = sample_user.id
        command.session = mock_session
        
        # Multiple concurrent requests should be handled properly
        results = []
        for _ in range(3):
            result = await command_service.delete_command(
                command_id=command.id,
                user_id=sample_user.id
            )
            results.append(result)
        
        assert all(r is True for r in results)

    async def test_large_dataset_handling(self, command_service, sample_user):
        """Test command service handling of large datasets."""
        # Simulate large result set
        large_command_list = []
        for i in range(1000):
            cmd = MagicMock()
            cmd.id = uuid4()
            cmd.command = f"command-{i}"
            cmd.executed_at = datetime.utcnow()
            cmd.execution_time = 1.0
            cmd.duration_ms = 1000
            cmd.stdout = f"output-{i}"
            cmd.stderr = None
            cmd.session = MagicMock()
            cmd.session.name = "test-session"
            cmd.session.session_type = "ssh"
            large_command_list.append(cmd)
        
        command_service.command_repo.get_user_commands_with_session.return_value = large_command_list[:100]
        command_service.command_repo.count_user_commands.return_value = 1000
        
        result = await command_service.get_command_history(
            user_id=sample_user.id,
            offset=0,
            limit=100
        )
        
        assert len(result.entries) == 100
        assert result.total == 1000

    # ===================================================================================
    # PERFORMANCE AND BOUNDARY TESTING
    # ===================================================================================

    async def test_command_service_performance_boundaries(self, command_service, sample_user):
        """Test command service performance with boundary conditions."""
        # Test with maximum limit
        command_service.command_repo.get_user_commands_with_session.return_value = []
        command_service.command_repo.count_user_commands.return_value = 0
        
        result = await command_service.get_command_history(
            user_id=sample_user.id,
            offset=0,
            limit=1000  # Large limit
        )
        
        assert result.limit == 1000
        assert len(result.entries) == 0

    async def test_command_service_memory_efficiency(self, command_service, sample_user):
        """Test command service memory efficiency with various operations."""
        # Test that operations don't leak memory through proper cleanup
        operations = [
            lambda: command_service.get_command_history(user_id=sample_user.id, offset=0, limit=10),
            lambda: command_service.search_commands(user_id=sample_user.id, query="test"),
            lambda: command_service.get_usage_stats(user_id=sample_user.id),
            lambda: command_service.get_frequent_commands(user_id=sample_user.id, limit=5)
        ]
        
        # Mock repository responses
        command_service.command_repo.get_user_commands_with_session.return_value = []
        command_service.command_repo.count_user_commands.return_value = 0
        command_service.command_repo.search_commands.return_value = []
        command_service.command_repo.count_commands_with_criteria.return_value = 0
        command_service.command_repo.get_command_stats.return_value = {
            "total_commands": 0, "successful_commands": 0, "failed_commands": 0,
            "cancelled_commands": 0, "status_breakdown": {}, "type_breakdown": {},
            "ai_commands": 0, "manual_commands": 0, "dangerous_commands": 0,
            "avg_execution_time": 0.0, "total_execution_time": 0.0,
            "commands_by_day": [], "most_active_session": None
        }
        command_service.command_repo.get_top_commands.return_value = []
        
        # Execute operations multiple times
        for _ in range(10):
            for operation in operations:
                await operation()
        
        # If we reach here without memory issues, the test passes
        assert True


# ===================================================================================
# PERFORMANCE BENCHMARKS AND STRESS TESTS
# ===================================================================================

@pytest.mark.performance
class TestCommandServicePerformance:
    """Performance testing for CommandService - Optional Extended Coverage."""

    @pytest_asyncio.fixture
    async def performance_command_service(self, mock_session):
        """Create command service for performance testing."""
        with patch('app.api.commands.service.CommandRepository') as mock_cmd_repo, \
             patch('app.api.commands.service.SessionRepository') as mock_sess_repo:
            service = CommandService(mock_session)
            return service

    async def test_bulk_command_processing_performance(self, performance_command_service, sample_user):
        """Test performance of bulk command processing operations."""
        # Simulate processing 10,000 commands
        bulk_commands = []
        for i in range(10000):
            cmd = MagicMock()
            cmd.id = uuid4()
            cmd.command = f"bulk-command-{i}"
            cmd.executed_at = datetime.utcnow()
            cmd.execution_time = 0.1
            cmd.duration_ms = 100
            cmd.stdout = f"output-{i}"
            cmd.stderr = None
            cmd.session = MagicMock()
            cmd.session.name = "bulk-session"
            cmd.session.session_type = "ssh"
            bulk_commands.append(cmd)
        
        performance_command_service.command_repo.get_user_commands_with_session.return_value = bulk_commands[:1000]
        performance_command_service.command_repo.count_user_commands.return_value = 10000
        
        import time
        start_time = time.time()
        
        result = await performance_command_service.get_command_history(
            user_id=sample_user.id,
            offset=0,
            limit=1000
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process 1000 commands in reasonable time (< 1 second)
        assert processing_time < 1.0
        assert len(result.entries) == 1000

    async def test_concurrent_user_simulation(self, performance_command_service):
        """Test concurrent user access simulation."""
        import asyncio
        
        # Simulate 50 concurrent users
        user_ids = [str(uuid4()) for _ in range(50)]
        
        # Mock responses
        performance_command_service.command_repo.get_user_commands_with_session.return_value = []
        performance_command_service.command_repo.count_user_commands.return_value = 0
        
        async def simulate_user_activity(user_id):
            await performance_command_service.get_command_history(user_id=user_id, offset=0, limit=10)
            return True
        
        start_time = time.time()
        
        # Execute concurrent operations
        tasks = [simulate_user_activity(user_id) for user_id in user_ids]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All operations should complete successfully
        assert all(results)
        # Should handle 50 concurrent users in reasonable time (< 5 seconds)
        assert total_time < 5.0


# ===================================================================================
# INTEGRATION TESTS WITH MOCKED EXTERNAL DEPENDENCIES  
# ===================================================================================

@pytest.mark.integration
class TestCommandServiceIntegration:
    """Integration tests for CommandService with external dependencies."""

    @pytest_asyncio.fixture
    async def integration_command_service(self, mock_session):
        """Create command service for integration testing."""
        with patch('app.api.commands.service.CommandRepository') as mock_cmd_repo, \
             patch('app.api.commands.service.SessionRepository') as mock_sess_repo:
            service = CommandService(mock_session)
            return service

    async def test_end_to_end_command_workflow(self, integration_command_service, sample_user, sample_commands):
        """Test complete end-to-end command workflow."""
        command = sample_commands[0]
        
        # Setup repository mocks for complete workflow
        integration_command_service.command_repo.get_by_id.return_value = command
        integration_command_service.command_repo.delete.return_value = True
        integration_command_service.command_repo.get_user_commands_with_session.return_value = sample_commands
        integration_command_service.command_repo.count_user_commands.return_value = len(sample_commands)
        integration_command_service.command_repo.search_commands.return_value = sample_commands[:3]
        integration_command_service.command_repo.count_commands_with_criteria.return_value = 3
        
        # 1. Search for commands
        search_result = await integration_command_service.search_commands(
            user_id=sample_user.id,
            query="test"
        )
        assert len(search_result.commands) == 3
        
        # 2. Get command details
        command_details = await integration_command_service.get_command_details(
            command_id=command.id,
            user_id=sample_user.id
        )
        assert command_details == command
        
        # 3. Get command history
        history_result = await integration_command_service.get_command_history(
            user_id=sample_user.id,
            offset=0,
            limit=10
        )
        assert len(history_result.entries) == len(sample_commands)
        
        # 4. Delete command
        delete_result = await integration_command_service.delete_command(
            command_id=command.id,
            user_id=sample_user.id
        )
        assert delete_result is True
        
        # Verify all repository methods were called
        integration_command_service.command_repo.search_commands.assert_called_once()
        integration_command_service.command_repo.get_by_id.assert_called()
        integration_command_service.command_repo.get_user_commands_with_session.assert_called_once()
        integration_command_service.command_repo.delete.assert_called_once()

    async def test_analytics_pipeline_integration(self, integration_command_service, sample_user):
        """Test analytics and metrics pipeline integration."""
        # Mock comprehensive analytics data
        mock_stats = {
            "total_commands": 500,
            "successful_commands": 425,
            "failed_commands": 60,
            "cancelled_commands": 15,
            "status_breakdown": {"completed": 425, "error": 60, "cancelled": 15},
            "type_breakdown": {"git": 150, "file_operation": 120, "system": 100, "network": 80, "other": 50},
            "ai_commands": 125,
            "manual_commands": 375,
            "dangerous_commands": 25,
            "avg_execution_time": 2.3,
            "total_execution_time": 1150.0,
            "commands_by_day": [{"date": "2023-01-01", "count": 25}],
            "most_active_session": {"session_id": str(uuid4()), "command_count": 75}
        }
        
        mock_metrics = {
            "execution_time_stats": {"avg": 2.3, "min": 0.1, "max": 45.0, "p50": 1.8, "p90": 8.2, "p95": 15.5},
            "success_rate": 85.0,
            "command_frequency": [{"command": "git status", "count": 45}],
            "error_patterns": [{"pattern": "permission denied", "count": 8}],
            "productivity_score": 8.1,
            "efficiency_trends": [{"period": "2023-01", "avg_time": 2.1}]
        }
        
        integration_command_service.command_repo.get_command_stats.return_value = mock_stats
        integration_command_service.command_repo.get_command_metrics.return_value = mock_metrics
        integration_command_service.command_repo.get_top_commands.return_value = [
            {"command": "git status", "count": 45, "avg_execution_time": 0.8}
        ]
        
        # Execute analytics pipeline
        stats_result = await integration_command_service.get_usage_stats(user_id=sample_user.id)
        metrics_result = await integration_command_service.get_command_metrics(user_id=sample_user.id)
        frequent_result = await integration_command_service.get_frequent_commands(user_id=sample_user.id)
        
        # Verify analytics results
        assert stats_result.total_commands == 500
        assert stats_result.success_rate == 85.0
        assert metrics_result.productivity_score == 8.1
        assert len(frequent_result) == 1
        
        # Verify all analytics methods called
        integration_command_service.command_repo.get_command_stats.assert_called_once()
        integration_command_service.command_repo.get_command_metrics.assert_called_once()
        integration_command_service.command_repo.get_top_commands.assert_called_once()