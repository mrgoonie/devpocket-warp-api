"""
Comprehensive tests for Commands service functionality.

This module provides extensive coverage for Commands service operations,
targeting the high-impact methods to achieve significant coverage gains.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.api.commands.service import CommandService
from app.models.command import Command
from app.models.session import Session
from app.models.user import User


@pytest.mark.database
class TestCommandService:
    """Comprehensive test suite for CommandService."""

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
            device_type="web"
        )

    @pytest_asyncio.fixture
    async def sample_commands(self, sample_session):
        """Create sample commands."""
        commands = []
        for i in range(5):
            cmd = Command(
                id=uuid4(),
                session_id=sample_session.id,
                command=f"echo 'test {i}'",
                status="completed",
                exit_code=0,
                output=f"test {i}\n",
                created_at=datetime.utcnow() - timedelta(hours=i)
            )
            commands.append(cmd)
        return commands

    async def test_service_initialization(self, mock_session):
        """Test CommandService initialization."""
        with patch('app.api.commands.service.CommandRepository') as mock_cmd_repo, \
             patch('app.api.commands.service.SessionRepository') as mock_sess_repo:
            service = CommandService(mock_session)
            
            assert service.session == mock_session
            assert service.command_repo is not None
            assert service.session_repo is not None
            mock_cmd_repo.assert_called_once_with(mock_session)
            mock_sess_repo.assert_called_once_with(mock_session)

    async def test_command_patterns_initialization(self, command_service):
        """Test that command patterns are properly initialized."""
        assert hasattr(command_service, 'command_patterns')
        assert len(command_service.command_patterns) > 0
        assert hasattr(command_service, 'dangerous_patterns')
        assert len(command_service.dangerous_patterns) > 0

    async def test_get_command_history_success(self, command_service, sample_user, sample_commands):
        """Test successful command history retrieval."""
        # Setup mock
        command_service.command_repo.get_user_command_history.return_value = sample_commands
        command_service.command_repo.count_user_commands.return_value = len(sample_commands)

        # Execute
        result = await command_service.get_command_history(
            user_id=sample_user.id,
            offset=0,
            limit=10
        )

        # Assert
        assert result is not None
        assert "commands" in result
        assert "total" in result
        assert len(result["commands"]) == len(sample_commands)
        assert result["total"] == len(sample_commands)
        command_service.command_repo.get_user_command_history.assert_called_once()

    async def test_get_command_history_with_search(self, command_service, sample_user):
        """Test command history with search term."""
        filtered_commands = [Command(
            id=uuid4(),
            session_id=uuid4(),
            command="ls -la",
            status="completed"
        )]
        
        command_service.command_repo.get_user_command_history.return_value = filtered_commands
        command_service.command_repo.count_user_commands.return_value = 1

        result = await command_service.get_command_history(
            user_id=sample_user.id,
            search_term="ls",
            offset=0,
            limit=10
        )

        assert len(result["commands"]) == 1
        assert result["total"] == 1
        command_service.command_repo.get_user_command_history.assert_called_once_with(
            user_id=sample_user.id,
            search_term="ls",
            offset=0,
            limit=10
        )

    async def test_get_command_history_pagination(self, command_service, sample_user, sample_commands):
        """Test command history with pagination."""
        page_commands = sample_commands[:2]
        command_service.command_repo.get_user_command_history.return_value = page_commands
        command_service.command_repo.count_user_commands.return_value = len(sample_commands)

        result = await command_service.get_command_history(
            user_id=sample_user.id,
            offset=0,
            limit=2
        )

        assert len(result["commands"]) == 2
        assert result["total"] == len(sample_commands)

    async def test_search_commands_basic(self, command_service, sample_user, sample_commands):
        """Test basic command search functionality."""
        command_service.command_repo.search_commands.return_value = sample_commands
        command_service.command_repo.count_commands_with_criteria.return_value = len(sample_commands)

        result = await command_service.search_commands(
            user_id=sample_user.id,
            query="echo"
        )

        assert result is not None
        assert "commands" in result
        assert "total" in result
        assert len(result["commands"]) == len(sample_commands)
        command_service.command_repo.search_commands.assert_called_once()

    async def test_search_commands_with_filters(self, command_service, sample_user, sample_commands):
        """Test command search with various filters."""
        command_service.command_repo.search_commands.return_value = sample_commands
        command_service.command_repo.count_commands_with_criteria.return_value = len(sample_commands)

        result = await command_service.search_commands(
            user_id=sample_user.id,
            query="echo",
            status="completed",
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow(),
            include_dangerous=False,
            offset=0,
            limit=20
        )

        assert result is not None
        assert "commands" in result
        assert "total" in result
        command_service.command_repo.search_commands.assert_called_once()

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

    async def test_get_usage_stats_success(self, command_service, sample_user):
        """Test successful usage statistics retrieval."""
        mock_stats = {
            "total_commands": 100,
            "status_breakdown": {"completed": 80, "failed": 15, "running": 5},
            "type_breakdown": {"manual": 60, "ai": 40},
            "ai_commands": 40,
            "avg_execution_time": 1500.5
        }
        command_service.command_repo.get_command_stats.return_value = mock_stats

        result = await command_service.get_usage_stats(user_id=sample_user.id)

        assert result == mock_stats
        command_service.command_repo.get_command_stats.assert_called_once_with(sample_user.id)

    async def test_get_session_command_stats_success(self, command_service, sample_user):
        """Test successful session command statistics retrieval."""
        mock_stats = [
            {"session_id": uuid4(), "command_count": 25, "avg_duration": 1200},
            {"session_id": uuid4(), "command_count": 30, "avg_duration": 1800}
        ]
        command_service.command_repo.get_session_command_stats.return_value = mock_stats

        result = await command_service.get_session_command_stats(user_id=sample_user.id)

        assert result == mock_stats
        command_service.command_repo.get_session_command_stats.assert_called_once_with(sample_user.id)

    async def test_get_frequent_commands_success(self, command_service, sample_user):
        """Test successful frequent commands retrieval."""
        frequent_commands = [
            {"command": "ls -la", "count": 50},
            {"command": "git status", "count": 35},
            {"command": "cd", "count": 30}
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

    async def test_get_command_suggestions_success(self, command_service, sample_user):
        """Test successful command suggestions retrieval."""
        mock_recent_commands = [
            Command(command="ls -la", working_directory="/home/user"),
            Command(command="git status", working_directory="/home/user/project"),
            Command(command="npm install", working_directory="/home/user/project")
        ]
        command_service.command_repo.get_user_recent_commands.return_value = mock_recent_commands

        result = await command_service.get_command_suggestions(
            user_id=sample_user.id,
            context="file_operations"
        )

        assert result is not None
        assert isinstance(result, list)
        command_service.command_repo.get_user_recent_commands.assert_called_once()

    async def test_get_command_suggestions_with_context(self, command_service, sample_user):
        """Test command suggestions with specific context."""
        mock_recent_commands = [
            Command(command="top", working_directory="/home/user"),
            Command(command="ps aux", working_directory="/home/user")
        ]
        command_service.command_repo.get_user_recent_commands.return_value = mock_recent_commands

        result = await command_service.get_command_suggestions(
            user_id=sample_user.id,
            context="system_monitoring"
        )

        assert result is not None
        assert isinstance(result, list)

    async def test_get_command_metrics_success(self, command_service, sample_user):
        """Test successful command metrics retrieval."""
        # Mock repository responses
        command_service.command_repo.get_user_commands_since.return_value = [
            Command(command="ls", created_at=datetime.utcnow()),
            Command(command="cd", created_at=datetime.utcnow() - timedelta(hours=1))
        ]
        command_service.command_repo.get_commands_by_status.return_value = [
            Command(status="completed"),
            Command(status="completed")
        ]
        command_service.command_repo.get_failed_commands.return_value = []
        command_service.command_repo.get_ai_suggested_commands.return_value = [
            Command(was_ai_suggested=True)
        ]

        result = await command_service.get_command_metrics(
            user_id=sample_user.id,
            days=7
        )

        assert result is not None
        assert "total_commands" in result
        assert "success_rate" in result
        assert "avg_commands_per_day" in result
        assert "ai_usage_percentage" in result

    async def test_classify_command_dangerous(self, command_service):
        """Test command classification for dangerous commands."""
        dangerous_command = "rm -rf /"
        result = command_service._classify_command(dangerous_command)
        
        assert result["is_dangerous"] is True

    async def test_classify_command_safe(self, command_service):
        """Test command classification for safe commands."""
        safe_command = "ls -la"
        result = command_service._classify_command(safe_command)
        
        assert result["is_dangerous"] is False

    async def test_is_dangerous_command_true(self, command_service):
        """Test dangerous command detection - positive case."""
        dangerous_commands = [
            "rm -rf /",
            "sudo rm -rf *",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1"
        ]
        
        for cmd in dangerous_commands:
            result = command_service._is_dangerous_command(cmd)
            assert result is True, f"Command '{cmd}' should be detected as dangerous"

    async def test_is_dangerous_command_false(self, command_service):
        """Test dangerous command detection - negative case."""
        safe_commands = [
            "ls -la",
            "git status",
            "cat file.txt",
            "echo 'hello world'"
        ]
        
        for cmd in safe_commands:
            result = command_service._is_dangerous_command(cmd)
            assert result is False, f"Command '{cmd}' should not be detected as dangerous"

    async def test_analyze_command_patterns_success(self, command_service):
        """Test command pattern analysis."""
        commands = [
            Command(command="ls -la", working_directory="/home/user"),
            Command(command="cd project", working_directory="/home/user"),
            Command(command="git status", working_directory="/home/user/project"),
            Command(command="npm install", working_directory="/home/user/project")
        ]
        
        result = command_service._analyze_command_patterns(commands)
        
        assert result is not None
        assert isinstance(result, dict)
        assert "common_directories" in result
        assert "common_tools" in result
        assert "workflow_patterns" in result

    async def test_create_command_pattern(self, command_service):
        """Test command pattern creation."""
        commands = ["git status", "git add .", "git commit -m 'update'"]
        pattern_type = "git_workflow"
        
        result = command_service._create_command_pattern(commands, pattern_type)
        
        assert result is not None
        assert "pattern" in result
        assert "type" in result
        assert result["type"] == pattern_type

    async def test_matches_pattern(self, command_service):
        """Test pattern matching."""
        command = "git status"
        pattern = {"pattern": "git.*", "type": "git"}
        
        result = command_service._matches_pattern(command, pattern)
        
        assert isinstance(result, bool)

    async def test_get_file_operation_suggestions(self, command_service):
        """Test file operation suggestions."""
        commands = [
            Command(command="ls -la", working_directory="/home/user"),
            Command(command="cat file.txt", working_directory="/home/user")
        ]
        
        result = command_service._get_file_operation_suggestions(commands)
        
        assert result is not None
        assert isinstance(result, list)

    async def test_get_system_monitoring_suggestions(self, command_service):
        """Test system monitoring suggestions."""
        commands = [
            Command(command="top", working_directory="/home/user"),
            Command(command="ps aux", working_directory="/home/user")
        ]
        
        result = command_service._get_system_monitoring_suggestions(commands)
        
        assert result is not None
        assert isinstance(result, list)

    async def test_get_network_suggestions(self, command_service):
        """Test network suggestions."""
        commands = [
            Command(command="ping google.com", working_directory="/home/user"),
            Command(command="netstat -tuln", working_directory="/home/user")
        ]
        
        result = command_service._get_network_suggestions(commands)
        
        assert result is not None
        assert isinstance(result, list)

    async def test_get_git_suggestions(self, command_service):
        """Test git suggestions."""
        commands = [
            Command(command="git status", working_directory="/home/user/project"),
            Command(command="git add .", working_directory="/home/user/project")
        ]
        
        result = command_service._get_git_suggestions(commands)
        
        assert result is not None
        assert isinstance(result, list)

    async def test_get_personalized_suggestions(self, command_service):
        """Test personalized suggestions."""
        commands = [
            Command(command="ls -la", working_directory="/home/user"),
            Command(command="git status", working_directory="/home/user/project"),
            Command(command="npm install", working_directory="/home/user/project")
        ]
        
        result = command_service._get_personalized_suggestions(commands)
        
        assert result is not None
        assert isinstance(result, list)

    async def test_edge_cases_empty_lists(self, command_service, sample_user):
        """Test edge cases with empty command lists."""
        command_service.command_repo.get_user_command_history.return_value = []
        command_service.command_repo.count_user_commands.return_value = 0

        result = await command_service.get_command_history(
            user_id=sample_user.id,
            offset=0,
            limit=10
        )

        assert result["commands"] == []
        assert result["total"] == 0

    async def test_large_offset_pagination(self, command_service, sample_user):
        """Test pagination with large offset."""
        command_service.command_repo.get_user_command_history.return_value = []
        command_service.command_repo.count_user_commands.return_value = 1000

        result = await command_service.get_command_history(
            user_id=sample_user.id,
            offset=950,
            limit=100
        )

        assert result["commands"] == []
        assert result["total"] == 1000

    async def test_command_suggestions_no_context(self, command_service, sample_user):
        """Test command suggestions without context."""
        command_service.command_repo.get_user_recent_commands.return_value = []

        result = await command_service.get_command_suggestions(
            user_id=sample_user.id
        )

        assert result is not None
        assert isinstance(result, list)

    async def test_repository_error_handling(self, command_service, sample_user):
        """Test error handling when repository throws exception."""
        command_service.command_repo.get_user_command_history.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await command_service.get_command_history(
                user_id=sample_user.id,
                offset=0,
                limit=10
            )

    async def test_service_with_real_patterns(self, command_service):
        """Test service methods with realistic command patterns."""
        # Test that the service initializes with real patterns
        assert len(command_service.command_patterns) > 0
        assert len(command_service.dangerous_patterns) > 0
        
        # Test some real pattern matching
        assert command_service._is_dangerous_command("rm -rf /") is True
        assert command_service._is_dangerous_command("ls -la") is False