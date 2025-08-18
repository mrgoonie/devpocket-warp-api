"""
Comprehensive tests for CommandRepository to improve coverage.

This test suite focuses on improving test coverage for the CommandRepository class
by testing all methods and code paths with proper mocking.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError

from app.models.command import Command
from app.repositories.command import CommandRepository


class TestCommandRepositoryComprehensive:
    """Comprehensive test coverage for CommandRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        # Mock the execute method to return a result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result
        session.add = Mock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.delete = AsyncMock()
        return session

    @pytest.fixture
    def command_repo(self, mock_session):
        """Create CommandRepository instance with mocked session."""
        return CommandRepository(session=mock_session)

    @pytest.fixture
    def sample_command(self):
        """Create sample command for testing."""
        return Command(
            id=uuid4(),
            session_id=str(uuid4()),
            command="ls -la",
            output="file1.txt\nfile2.txt",
            exit_code=0,
            status="completed",
            created_at=datetime.now(),
            executed_at=datetime.now(),
        )

    def test_init(self, mock_session):
        """Test CommandRepository initialization."""
        repo = CommandRepository(session=mock_session)
        assert repo.session == mock_session
        assert repo.model == Command

    @pytest.mark.asyncio
    async def test_get_session_commands_basic(self, command_repo, mock_session, sample_command):
        """Test get_session_commands basic functionality."""
        # Mock the result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_command]
        mock_session.execute.return_value = mock_result
        
        session_id = "test-session-123"
        result = await command_repo.get_session_commands(session_id)
        
        assert result == [sample_command]
        mock_session.execute.assert_called_once()
        
        # Verify the query was built correctly
        call_args = mock_session.execute.call_args[0][0]
        assert str(call_args).lower().count("command.session_id") > 0

    @pytest.mark.asyncio
    async def test_get_session_commands_with_status_filter(self, command_repo, mock_session):
        """Test get_session_commands with status filter."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        session_id = "test-session-123"
        status_filter = "completed"
        
        result = await command_repo.get_session_commands(
            session_id, status_filter=status_filter
        )
        
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_commands_with_pagination(self, command_repo, mock_session):
        """Test get_session_commands with pagination parameters."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        session_id = "test-session-123"
        
        result = await command_repo.get_session_commands(
            session_id, offset=10, limit=50
        )
        
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_command_history_basic(self, command_repo, mock_session):
        """Test get_user_command_history basic functionality."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        
        result = await command_repo.get_user_command_history(user_id)
        
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_command_history_with_search(self, command_repo, mock_session, sample_command):
        """Test get_user_command_history with search term."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_command]
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        search_term = "ls"
        
        result = await command_repo.get_user_command_history(
            user_id, search_term=search_term
        )
        
        assert result == [sample_command]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_command_history_with_pagination(self, command_repo, mock_session):
        """Test get_user_command_history with pagination."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        
        result = await command_repo.get_user_command_history(
            user_id, offset=20, limit=25
        )
        
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_commands_basic(self, command_repo, mock_session):
        """Test get_recent_commands basic functionality."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        
        result = await command_repo.get_recent_commands(user_id)
        
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_commands_with_limit(self, command_repo, mock_session):
        """Test get_recent_commands with custom limit."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        
        result = await command_repo.get_recent_commands(user_id, limit=5)
        
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_command_statistics_basic(self, command_repo, mock_session):
        """Test get_command_statistics basic functionality."""
        # Mock different results for different queries
        mock_results = [
            Mock(scalar=Mock(return_value=50)),  # total_commands
            Mock(scalar=Mock(return_value=45)),  # successful_commands
            Mock(scalar=Mock(return_value=5)),   # failed_commands
            Mock(scalar=Mock(return_value=3)),   # unique_commands
        ]
        mock_session.execute.side_effect = mock_results
        
        user_id = str(uuid4())
        
        result = await command_repo.get_command_statistics(user_id)
        
        expected = {
            "total_commands": 50,
            "successful_commands": 45,
            "failed_commands": 5,
            "unique_commands": 3,
        }
        assert result == expected
        assert mock_session.execute.call_count == 4

    @pytest.mark.asyncio
    async def test_get_command_statistics_with_date_range(self, command_repo, mock_session):
        """Test get_command_statistics with date range."""
        mock_results = [
            Mock(scalar=Mock(return_value=25)),
            Mock(scalar=Mock(return_value=20)),
            Mock(scalar=Mock(return_value=5)),
            Mock(scalar=Mock(return_value=2)),
        ]
        mock_session.execute.side_effect = mock_results
        
        user_id = str(uuid4())
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        result = await command_repo.get_command_statistics(
            user_id, start_date=start_date, end_date=end_date
        )
        
        expected = {
            "total_commands": 25,
            "successful_commands": 20,
            "failed_commands": 5,
            "unique_commands": 2,
        }
        assert result == expected

    @pytest.mark.asyncio
    async def test_search_commands_basic(self, command_repo, mock_session, sample_command):
        """Test search_commands basic functionality."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_command]
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        query = "ls"
        
        result = await command_repo.search_commands(user_id, query)
        
        assert result == [sample_command]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_commands_with_pagination(self, command_repo, mock_session):
        """Test search_commands with pagination."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        query = "grep"
        
        result = await command_repo.search_commands(
            user_id, query, offset=10, limit=20
        )
        
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_popular_commands_basic(self, command_repo, mock_session):
        """Test get_popular_commands basic functionality."""
        mock_result = Mock()
        mock_result.all.return_value = [
            ("ls", 10),
            ("cd", 8),
            ("grep", 5),
        ]
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        
        result = await command_repo.get_popular_commands(user_id)
        
        expected = [
            {"command": "ls", "count": 10},
            {"command": "cd", "count": 8},
            {"command": "grep", "count": 5},
        ]
        assert result == expected
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_popular_commands_with_limit(self, command_repo, mock_session):
        """Test get_popular_commands with custom limit."""
        mock_result = Mock()
        mock_result.all.return_value = [("ls", 10)]
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        
        result = await command_repo.get_popular_commands(user_id, limit=1)
        
        expected = [{"command": "ls", "count": 10}]
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_popular_commands_with_date_range(self, command_repo, mock_session):
        """Test get_popular_commands with date range."""
        mock_result = Mock()
        mock_result.all.return_value = [("ls", 5)]
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        result = await command_repo.get_popular_commands(
            user_id, start_date=start_date, end_date=end_date
        )
        
        expected = [{"command": "ls", "count": 5}]
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_command_usage_by_hour_basic(self, command_repo, mock_session):
        """Test get_command_usage_by_hour basic functionality."""
        mock_result = Mock()
        mock_result.all.return_value = [
            (9, 15),   # 9 AM: 15 commands
            (14, 22),  # 2 PM: 22 commands
            (18, 8),   # 6 PM: 8 commands
        ]
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        
        result = await command_repo.get_command_usage_by_hour(user_id)
        
        expected = [
            {"hour": 9, "count": 15},
            {"hour": 14, "count": 22},
            {"hour": 18, "count": 8},
        ]
        assert result == expected
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_command_usage_by_hour_with_date_range(self, command_repo, mock_session):
        """Test get_command_usage_by_hour with date range."""
        mock_result = Mock()
        mock_result.all.return_value = [(10, 12)]
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()
        
        result = await command_repo.get_command_usage_by_hour(
            user_id, start_date=start_date, end_date=end_date
        )
        
        expected = [{"hour": 10, "count": 12}]
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_failed_commands_basic(self, command_repo, mock_session, sample_command):
        """Test get_failed_commands basic functionality."""
        failed_command = Command(
            id=uuid4(),
            session_id=str(uuid4()),
            command="invalid_command",
            output="command not found",
            exit_code=1,
            status="failed",
            created_at=datetime.now(),
        )
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [failed_command]
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        
        result = await command_repo.get_failed_commands(user_id)
        
        assert result == [failed_command]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_failed_commands_with_pagination(self, command_repo, mock_session):
        """Test get_failed_commands with pagination."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        
        result = await command_repo.get_failed_commands(
            user_id, offset=5, limit=10
        )
        
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_long_running_commands_basic(self, command_repo, mock_session):
        """Test get_long_running_commands basic functionality."""
        long_command = Command(
            id=uuid4(),
            session_id=str(uuid4()),
            command="long_process",
            output="processing...",
            exit_code=0,
            status="completed",
            created_at=datetime.now() - timedelta(minutes=5),
            executed_at=datetime.now(),
            execution_time=300.0,  # 5 minutes
        )
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [long_command]
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        
        result = await command_repo.get_long_running_commands(user_id)
        
        assert result == [long_command]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_long_running_commands_with_threshold(self, command_repo, mock_session):
        """Test get_long_running_commands with custom threshold."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        threshold_seconds = 120  # 2 minutes
        
        result = await command_repo.get_long_running_commands(
            user_id, threshold_seconds=threshold_seconds
        )
        
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_old_commands_basic(self, command_repo, mock_session):
        """Test delete_old_commands basic functionality."""
        mock_result = Mock()
        mock_result.rowcount = 25
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        days_old = 30
        
        result = await command_repo.delete_old_commands(user_id, days_old)
        
        assert result == 25
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_old_commands_exception_handling(self, command_repo, mock_session):
        """Test delete_old_commands exception handling."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")
        
        user_id = str(uuid4())
        days_old = 30
        
        with pytest.raises(SQLAlchemyError):
            await command_repo.delete_old_commands(user_id, days_old)
        
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_update_status_basic(self, command_repo, mock_session):
        """Test bulk_update_status basic functionality."""
        mock_result = Mock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result
        
        command_ids = [uuid4(), uuid4(), uuid4()]
        new_status = "archived"
        
        result = await command_repo.bulk_update_status(command_ids, new_status)
        
        assert result == 5
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_update_status_exception_handling(self, command_repo, mock_session):
        """Test bulk_update_status exception handling."""
        mock_session.execute.side_effect = SQLAlchemyError("Update error")
        
        command_ids = [uuid4()]
        new_status = "archived"
        
        with pytest.raises(SQLAlchemyError):
            await command_repo.bulk_update_status(command_ids, new_status)
        
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_commands_by_session_and_status(self, command_repo, mock_session):
        """Test get_commands_by_session_and_status."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        session_id = str(uuid4())
        status = "running"
        
        result = await command_repo.get_commands_by_session_and_status(session_id, status)
        
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_commands_by_user_basic(self, command_repo, mock_session):
        """Test count_commands_by_user basic functionality."""
        mock_result = Mock()
        mock_result.scalar.return_value = 42
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        
        result = await command_repo.count_commands_by_user(user_id)
        
        assert result == 42
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_commands_by_user_with_status(self, command_repo, mock_session):
        """Test count_commands_by_user with status filter."""
        mock_result = Mock()
        mock_result.scalar.return_value = 15
        mock_session.execute.return_value = mock_result
        
        user_id = str(uuid4())
        status = "completed"
        
        result = await command_repo.count_commands_by_user(user_id, status=status)
        
        assert result == 15
        mock_session.execute.assert_called_once()