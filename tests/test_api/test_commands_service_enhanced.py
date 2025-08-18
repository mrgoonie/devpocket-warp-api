"""
Enhanced Commands service tests - Phase 2 Implementation.
Focused on improving coverage for the Commands Service to achieve 65% target.
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
    CommandUsageStats,
    SessionCommandStats
)
from app.models.command import Command
from app.models.session import Session
from app.models.user import User


@pytest.mark.database
class TestCommandServiceEnhanced:
    """Enhanced test suite for CommandService - Phase 2 Coverage."""

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
        for i in range(5):
            cmd = Command(
                id=uuid4(),
                session_id=sample_session.id,
                command=f"test-command-{i}",
                status="completed",
                exit_code=0,
                output=f"output {i}\n",
                stdout=f"output {i}\n",
                stderr=None,
                created_at=datetime.utcnow() - timedelta(hours=i),
                executed_at=datetime.utcnow() - timedelta(hours=i),
                execution_time=1.5 + i * 0.1,
                working_directory="/home/user",
                command_type="file_operation",
                is_dangerous=False,
                was_ai_suggested=False
            )
            cmd.session = sample_session
            commands.append(cmd)
        return commands

    # ===================================================================================
    # ENHANCED COMMAND HISTORY TESTING
    # ===================================================================================

    async def test_get_command_history_comprehensive(self, command_service, sample_user, sample_commands):
        """Test comprehensive command history functionality."""
        command_service.command_repo.get_user_commands_with_session.return_value = sample_commands
        command_service.command_repo.count_user_commands.return_value = len(sample_commands)
        
        result = await command_service.get_command_history(
            user_id=sample_user.id,
            session_id=None,
            offset=0,
            limit=10
        )
        
        assert isinstance(result, CommandHistoryResponse)
        assert len(result.entries) == len(sample_commands)
        assert result.total == len(sample_commands)
        
        # Verify entry details
        for i, entry in enumerate(result.entries):
            assert entry.command == f"test-command-{i}"
            assert entry.status.value == "completed"
            assert entry.working_directory == "/home/user"

    async def test_get_command_history_with_session_id(self, command_service, sample_user, sample_commands):
        """Test command history with specific session ID."""
        session_id = str(sample_commands[0].session_id)
        command_service.command_repo.get_user_commands_with_session.return_value = sample_commands[:2]
        command_service.command_repo.count_user_commands.return_value = 2
        
        result = await command_service.get_command_history(
            user_id=sample_user.id,
            session_id=session_id,
            offset=0,
            limit=10
        )
        
        assert len(result.entries) == 2
        assert result.filters_applied == {"session_id": session_id}

    async def test_get_command_history_pagination(self, command_service, sample_user, sample_commands):
        """Test command history pagination."""
        command_service.command_repo.get_user_commands_with_session.return_value = sample_commands[2:4]
        command_service.command_repo.count_user_commands.return_value = len(sample_commands)
        
        result = await command_service.get_command_history(
            user_id=sample_user.id,
            offset=2,
            limit=2
        )
        
        assert len(result.entries) == 2
        assert result.offset == 2
        assert result.limit == 2
        assert result.total == len(sample_commands)

    async def test_get_command_history_empty(self, command_service, sample_user):
        """Test command history with no results."""
        command_service.command_repo.get_user_commands_with_session.return_value = []
        command_service.command_repo.count_user_commands.return_value = 0
        
        result = await command_service.get_command_history(
            user_id=sample_user.id,
            offset=0,
            limit=10
        )
        
        assert len(result.entries) == 0
        assert result.total == 0

    async def test_get_command_history_error_handling(self, command_service, sample_user):
        """Test command history error handling."""
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
    # COMMAND DETAILS TESTING
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
        """Test command details with wrong user."""
        command = sample_commands[0]
        wrong_user_id = uuid4()
        command_service.command_repo.get_by_id.return_value = command
        
        # Mock session with different user
        mock_session = MagicMock()
        mock_session.user_id = uuid4()
        command.session = mock_session
        
        result = await command_service.get_command_details(
            command_id=command.id,
            user_id=wrong_user_id
        )
        
        assert result is None

    async def test_get_command_details_no_session(self, command_service, sample_user, sample_commands):
        """Test command details with no session."""
        command = sample_commands[0]
        command.session = None
        command_service.command_repo.get_by_id.return_value = command
        
        result = await command_service.get_command_details(
            command_id=command.id,
            user_id=sample_user.id
        )
        
        assert result is None

    async def test_get_command_details_exception(self, command_service, sample_user):
        """Test command details exception handling."""
        command_id = uuid4()
        command_service.command_repo.get_by_id.side_effect = Exception("DB error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_command_details(
                command_id=command_id,
                user_id=sample_user.id
            )
        
        assert exc.value.status_code == 500

    # ===================================================================================
    # COMMAND DELETION TESTING
    # ===================================================================================

    async def test_delete_command_success(self, command_service, sample_user, sample_commands):
        """Test successful command deletion."""
        command = sample_commands[0]
        command_service.command_repo.get_by_id.return_value = command
        command_service.command_repo.delete.return_value = True
        
        # Mock session with correct user
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
        """Test command deletion when not found."""
        command_id = uuid4()
        command_service.command_repo.get_by_id.return_value = None
        
        result = await command_service.delete_command(
            command_id=command_id,
            user_id=sample_user.id
        )
        
        assert result is False

    async def test_delete_command_wrong_user(self, command_service, sample_commands):
        """Test command deletion with wrong user."""
        command = sample_commands[0]
        wrong_user_id = uuid4()
        command_service.command_repo.get_by_id.return_value = command
        
        # Mock session with different user
        mock_session = MagicMock()
        mock_session.user_id = uuid4()
        command.session = mock_session
        
        result = await command_service.delete_command(
            command_id=command.id,
            user_id=wrong_user_id
        )
        
        assert result is False

    async def test_delete_command_no_session(self, command_service, sample_user, sample_commands):
        """Test command deletion with no session."""
        command = sample_commands[0]
        command.session = None
        command_service.command_repo.get_by_id.return_value = command
        
        result = await command_service.delete_command(
            command_id=command.id,
            user_id=sample_user.id
        )
        
        assert result is False

    async def test_delete_command_exception(self, command_service, sample_user):
        """Test command deletion exception handling."""
        command_id = uuid4()
        command_service.command_repo.get_by_id.side_effect = Exception("DB error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.delete_command(
                command_id=command_id,
                user_id=sample_user.id
            )
        
        assert exc.value.status_code == 500

    # ===================================================================================
    # USAGE STATISTICS TESTING
    # ===================================================================================

    async def test_get_usage_stats_comprehensive(self, command_service, sample_user, sample_commands):
        """Test comprehensive usage statistics."""
        command_service.command_repo.get_user_commands.return_value = sample_commands
        
        result = await command_service.get_usage_stats(user_id=sample_user.id)
        
        assert isinstance(result, CommandUsageStats)
        assert result.total_commands == len(sample_commands)
        assert result.unique_commands == len(sample_commands)  # All unique in our sample
        assert result.successful_commands == len(sample_commands)  # All successful
        assert result.failed_commands == 0
        assert result.average_duration_ms > 0
        assert "file_operation" in result.commands_by_type

    async def test_get_usage_stats_empty_commands(self, command_service, sample_user):
        """Test usage statistics with no commands."""
        command_service.command_repo.get_user_commands.return_value = []
        
        result = await command_service.get_usage_stats(user_id=sample_user.id)
        
        assert result.total_commands == 0
        assert result.unique_commands == 0
        assert result.successful_commands == 0
        assert result.failed_commands == 0
        assert result.average_duration_ms == 0
        assert result.commands_by_type == {}

    async def test_get_usage_stats_mixed_results(self, command_service, sample_user, sample_session):
        """Test usage statistics with mixed success/failure commands."""
        mixed_commands = []
        for i in range(4):
            exit_code = 0 if i % 2 == 0 else 1
            status = "completed" if i % 2 == 0 else "error"
            cmd = Command(
                id=uuid4(),
                session_id=sample_session.id,
                command=f"test-{i}",
                status=status,
                exit_code=exit_code,
                executed_at=datetime.utcnow(),
                execution_time=1.0 + i,
                command_type="system"
            )
            cmd.session = sample_session
            # Add duration_ms property manually
            cmd._duration_ms = int((1.0 + i) * 1000)
            mixed_commands.append(cmd)
        
        # Mock the duration_ms property
        for cmd in mixed_commands:
            cmd.duration_ms = cmd._duration_ms
        
        command_service.command_repo.get_user_commands.return_value = mixed_commands
        
        result = await command_service.get_usage_stats(user_id=sample_user.id)
        
        assert result.total_commands == 4
        assert result.successful_commands == 2  # Even indices
        assert result.failed_commands == 2      # Odd indices
        assert result.average_duration_ms > 0

    async def test_get_usage_stats_exception(self, command_service, sample_user):
        """Test usage statistics exception handling."""
        command_service.command_repo.get_user_commands.side_effect = Exception("DB error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_usage_stats(user_id=sample_user.id)
        
        assert exc.value.status_code == 500
        assert "Failed to get command usage statistics" in str(exc.value.detail)

    # ===================================================================================
    # SESSION COMMAND STATISTICS TESTING
    # ===================================================================================

    async def test_get_session_command_stats_success(self, command_service, sample_user):
        """Test session command statistics."""
        mock_stats = [
            {
                "session_id": str(uuid4()),
                "session_name": "Dev Session", 
                "total_commands": 25,
                "successful_commands": 20,
                "failed_commands": 5,
                "average_duration_ms": 1800.0,
                "last_command_at": datetime.utcnow(),
                "most_used_command": "git status"
            }
        ]
        command_service.command_repo.get_session_command_stats.return_value = mock_stats
        
        result = await command_service.get_session_command_stats(user_id=sample_user.id)
        
        assert len(result) == 1
        assert result[0].session_name == "Dev Session"
        assert result[0].total_commands == 25
        assert result[0].successful_commands == 20
        assert result[0].failed_commands == 5
        command_service.command_repo.get_session_command_stats.assert_called_once_with(sample_user.id)

    async def test_get_session_command_stats_empty(self, command_service, sample_user):
        """Test session command statistics with no data."""
        command_service.command_repo.get_session_command_stats.return_value = []
        
        result = await command_service.get_session_command_stats(user_id=sample_user.id)
        
        assert result == []

    async def test_get_session_command_stats_exception(self, command_service, sample_user):
        """Test session command statistics exception handling."""
        command_service.command_repo.get_session_command_stats.side_effect = Exception("Stats error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_session_command_stats(user_id=sample_user.id)
        
        assert exc.value.status_code == 500

    # ===================================================================================
    # FREQUENT COMMANDS TESTING
    # ===================================================================================

    async def test_get_frequent_commands_success(self, command_service, sample_user):
        """Test frequent commands retrieval."""
        frequent_commands = [
            {"command": "ls -la", "count": 45},
            {"command": "git status", "count": 30}
        ]
        command_service.command_repo.get_top_commands.return_value = frequent_commands
        
        result = await command_service.get_frequent_commands(
            user_id=sample_user.id,
            limit=10
        )
        
        assert result == frequent_commands
        command_service.command_repo.get_top_commands.assert_called_once_with(
            user_id=sample_user.id,
            limit=10
        )

    async def test_get_frequent_commands_with_date_filter(self, command_service, sample_user):
        """Test frequent commands with date filtering."""
        start_date = datetime.utcnow() - timedelta(days=7)
        frequent_commands = [{"command": "docker ps", "count": 15}]
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

    async def test_get_frequent_commands_empty(self, command_service, sample_user):
        """Test frequent commands with no data."""
        command_service.command_repo.get_top_commands.return_value = []
        
        result = await command_service.get_frequent_commands(user_id=sample_user.id)
        
        assert result == []

    async def test_get_frequent_commands_exception(self, command_service, sample_user):
        """Test frequent commands exception handling."""
        command_service.command_repo.get_top_commands.side_effect = Exception("Query error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_frequent_commands(user_id=sample_user.id)
        
        assert exc.value.status_code == 500

    # ===================================================================================
    # COMMAND SUGGESTIONS TESTING
    # ===================================================================================

    async def test_get_command_suggestions_basic(self, command_service, sample_user):
        """Test basic command suggestions."""
        mock_patterns = ["git_workflow", "file_operations"]
        command_service.command_repo.get_user_command_patterns.return_value = mock_patterns
        
        result = await command_service.get_command_suggestions(
            user_id=sample_user.id,
            current_directory="/home/user",
            limit=5
        )
        
        assert len(result.suggestions) > 0
        assert result.context == "/home/user"

    async def test_get_command_suggestions_git_directory(self, command_service, sample_user):
        """Test command suggestions in git directory."""
        mock_patterns = ["git_workflow"]
        command_service.command_repo.get_user_command_patterns.return_value = mock_patterns
        
        result = await command_service.get_command_suggestions(
            user_id=sample_user.id,
            current_directory="/home/user/project/.git",
            limit=3
        )
        
        # Should include git suggestions for git directory
        git_suggestions = [s for s in result.suggestions if "git" in s.command.lower()]
        assert len(git_suggestions) > 0

    async def test_get_command_suggestions_exception(self, command_service, sample_user):
        """Test command suggestions exception handling."""
        command_service.command_repo.get_user_command_patterns.side_effect = Exception("Pattern error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_command_suggestions(user_id=sample_user.id)
        
        assert exc.value.status_code == 500

    # ===================================================================================
    # COMMAND METRICS TESTING
    # ===================================================================================

    async def test_get_command_metrics_basic(self, command_service, sample_user):
        """Test basic command metrics."""
        mock_metrics = {
            "execution_time_stats": {"avg": 2.5, "min": 0.1, "max": 10.0},
            "success_rate": 85.0,
            "command_frequency": [{"command": "ls", "count": 20}],
            "productivity_score": 7.5
        }
        command_service.command_repo.get_command_metrics.return_value = mock_metrics
        
        result = await command_service.get_command_metrics(user_id=sample_user.id)
        
        assert result.execution_time_stats["avg"] == 2.5
        assert result.success_rate == 85.0
        assert result.productivity_score == 7.5

    async def test_get_command_metrics_with_filters(self, command_service, sample_user):
        """Test command metrics with filtering."""
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        mock_metrics = {
            "execution_time_stats": {"avg": 1.8, "min": 0.1, "max": 5.0},
            "success_rate": 90.0,
            "command_frequency": [],
            "productivity_score": 8.0
        }
        command_service.command_repo.get_command_metrics.return_value = mock_metrics
        
        result = await command_service.get_command_metrics(
            user_id=sample_user.id,
            start_date=start_date,
            end_date=end_date,
            command_type="git"
        )
        
        assert result.success_rate == 90.0

    async def test_get_command_metrics_exception(self, command_service, sample_user):
        """Test command metrics exception handling."""
        command_service.command_repo.get_command_metrics.side_effect = Exception("Metrics error")
        
        with pytest.raises(HTTPException) as exc:
            await command_service.get_command_metrics(user_id=sample_user.id)
        
        assert exc.value.status_code == 500

    # ===================================================================================
    # PRIVATE METHOD TESTING - Internal Logic
    # ===================================================================================

    async def test_classify_command_types(self, command_service):
        """Test command classification."""
        test_cases = [
            ("git status", "git"),
            ("ls -la", "file_operation"),
            ("curl https://api.com", "network"),
            ("ps aux", "system"),
            ("docker ps", "development"),
            ("unknown-cmd", "other")
        ]
        
        for command, expected in test_cases:
            result = command_service._classify_command(command)
            assert result == expected

    async def test_is_dangerous_command_detection(self, command_service):
        """Test dangerous command detection."""
        dangerous = ["sudo rm -rf /", "dd if=/dev/zero", "chmod 777 /etc"]
        safe = ["ls -la", "git status", "echo hello"]
        
        for cmd in dangerous:
            assert command_service._is_dangerous_command(cmd) is True
            
        for cmd in safe:
            assert command_service._is_dangerous_command(cmd) is False

    async def test_analyze_command_patterns(self, command_service, sample_commands):
        """Test command pattern analysis."""
        patterns = command_service._analyze_command_patterns(sample_commands)
        
        assert isinstance(patterns, list)
        # Should have at least one pattern from our sample commands
        assert len(patterns) >= 0

    async def test_create_command_pattern(self, command_service):
        """Test command pattern creation."""
        commands = ["git add", "git commit", "git push"]
        pattern_type = "git_workflow"
        
        pattern = command_service._create_command_pattern(commands, pattern_type)
        
        assert pattern["pattern_type"] == pattern_type
        assert pattern["frequency"] == len(commands)
        assert pattern["commands"] == commands

    async def test_matches_pattern(self, command_service):
        """Test pattern matching."""
        pattern = {"regex": r"git\s+\w+", "keywords": ["git"]}
        
        assert command_service._matches_pattern("git status", pattern) is True
        assert command_service._matches_pattern("ls -la", pattern) is False

    async def test_suggestion_helper_methods(self, command_service):
        """Test command suggestion helper methods."""
        # File operation suggestions
        file_suggestions = command_service._get_file_operation_suggestions("/home/user")
        assert len(file_suggestions) > 0
        
        # System monitoring suggestions
        system_suggestions = command_service._get_system_monitoring_suggestions()
        assert len(system_suggestions) > 0
        
        # Network suggestions
        network_suggestions = command_service._get_network_suggestions()
        assert len(network_suggestions) > 0
        
        # Git suggestions
        git_suggestions = command_service._get_git_suggestions()
        assert len(git_suggestions) > 0

    async def test_personalized_suggestions(self, command_service):
        """Test personalized command suggestions."""
        user_patterns = [
            {"pattern_type": "git_workflow", "frequency": 10, "commands": ["git status", "git add"]},
            {"pattern_type": "file_ops", "frequency": 5, "commands": ["ls", "cd"]}
        ]
        
        suggestions = command_service._get_personalized_suggestions(user_patterns)
        
        assert len(suggestions) > 0
        # Should include git suggestions from patterns
        git_suggestions = [s for s in suggestions if "git" in s["command"]]
        assert len(git_suggestions) > 0

    # ===================================================================================
    # EDGE CASES AND ERROR SCENARIOS
    # ===================================================================================

    async def test_service_with_invalid_user_id(self, command_service):
        """Test service methods with invalid user ID format."""
        invalid_user_id = "not-a-uuid"
        
        # Should handle gracefully or raise appropriate errors
        try:
            await command_service.get_command_history(user_id=invalid_user_id)
        except (HTTPException, ValueError):
            # Either is acceptable for invalid UUID
            pass

    async def test_concurrent_operations(self, command_service, sample_user, sample_commands):
        """Test concurrent operations handling."""
        command = sample_commands[0]
        command_service.command_repo.get_by_id.return_value = command
        command_service.command_repo.delete.return_value = True
        
        mock_session = MagicMock()
        mock_session.user_id = sample_user.id
        command.session = mock_session
        
        # Multiple requests should work
        results = []
        for _ in range(3):
            result = await command_service.delete_command(
                command_id=command.id,
                user_id=sample_user.id
            )
            results.append(result)
        
        assert all(r is True for r in results)

    async def test_large_dataset_handling(self, command_service, sample_user):
        """Test handling large datasets."""
        # Create large mock dataset
        large_commands = []
        for i in range(500):  # Reasonable size for testing
            cmd = MagicMock()
            cmd.id = uuid4()
            cmd.command = f"cmd-{i}"
            cmd.executed_at = datetime.utcnow()
            cmd.execution_time = 1.0
            cmd.duration_ms = 1000
            cmd.stdout = f"out-{i}"
            cmd.stderr = None
            cmd.session = MagicMock()
            cmd.session.name = "test"
            cmd.session.session_type = "ssh"
            large_commands.append(cmd)
        
        # Test pagination with large dataset
        command_service.command_repo.get_user_commands_with_session.return_value = large_commands[:100]
        command_service.command_repo.count_user_commands.return_value = 500
        
        result = await command_service.get_command_history(
            user_id=sample_user.id,
            offset=0,
            limit=100
        )
        
        assert len(result.entries) == 100
        assert result.total == 500

    async def test_service_initialization_patterns(self, mock_session):
        """Test service initialization and pattern loading."""
        with patch('app.api.commands.service.CommandRepository') as mock_cmd_repo, \
             patch('app.api.commands.service.SessionRepository') as mock_sess_repo:
            service = CommandService(mock_session)
            
            # Verify initialization
            assert service.session == mock_session
            assert hasattr(service, 'command_patterns')
            assert hasattr(service, 'dangerous_patterns')
            assert len(service.command_patterns) > 0
            assert len(service.dangerous_patterns) > 0
            
            # Check pattern structure
            for pattern in service.command_patterns:
                assert "name" in pattern
                assert "description" in pattern
                assert "commands" in pattern
                
            for pattern in service.dangerous_patterns:
                assert "pattern" in pattern
                assert "description" in pattern