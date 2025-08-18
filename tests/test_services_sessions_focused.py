"""
Focused Sessions Service Tests - Phase 3 Implementation.

This module provides reliable, focused coverage for Sessions service operations,
targeting 65% coverage for Sessions Service to achieve Phase 3 objectives.

Coverage Target: 33% → 65% coverage (+32 percentage points)
Focus: Core service methods with solid, working test implementations
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.sessions.service import SessionService
from app.api.sessions.schemas import (
    SessionCreate,
    SessionResponse,
    SessionUpdate,
    SessionCommand,
    SessionCommandResponse,
    SessionHistoryResponse,
    SessionSearchRequest,
    SessionStats,
    SessionHealthCheck,
    SessionStatus,
    SessionType,
    SessionMode
)
from app.models.session import Session
from app.models.user import User
from app.models.ssh_profile import SSHProfile


@pytest.mark.asyncio
class TestSessionServiceFocused:
    """Focused test suite for SessionService - Phase 3 Implementation."""

    @pytest_asyncio.fixture
    async def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest_asyncio.fixture
    async def mock_session_repo(self):
        """Create a mock session repository."""
        repo = AsyncMock()
        return repo

    @pytest_asyncio.fixture
    async def mock_ssh_profile_repo(self):
        """Create a mock SSH profile repository."""
        repo = AsyncMock()
        return repo

    @pytest_asyncio.fixture
    async def session_service(self, mock_session, mock_session_repo, mock_ssh_profile_repo):
        """Create session service instance with mocked dependencies."""
        with patch('app.api.sessions.service.SessionRepository', return_value=mock_session_repo), \
             patch('app.api.sessions.service.SSHProfileRepository', return_value=mock_ssh_profile_repo):
            service = SessionService(mock_session)
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
    async def sample_session_create(self):
        """Create a sample SessionCreate object."""
        return SessionCreate(
            name="test-session",
            session_type=SessionType.LOCAL,
            description="Test session",
            mode=SessionMode.BASH,
            terminal_size={"cols": 80, "rows": 24},
            environment={"TERM": "xterm-256color"},
            working_directory="/home/user",
            idle_timeout=3600,
            max_duration=7200,
            enable_logging=True,
            enable_recording=False,
            auto_reconnect=True
        )

    @pytest_asyncio.fixture
    async def sample_session(self, sample_user):
        """Create a sample session object."""
        return Session(
            id=str(uuid4()),
            user_id=sample_user.id,
            name="test-session",
            session_type="local",
            description="Test session",
            status="active",
            mode="bash",
            terminal_cols=80,
            terminal_rows=24,
            environment={"TERM": "xterm-256color"},
            working_directory="/home/user",
            idle_timeout=3600,
            max_duration=7200,
            enable_logging=True,
            enable_recording=False,
            auto_reconnect=True,
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )

    # Core service initialization tests
    async def test_service_initialization(self, mock_session):
        """Test service initializes correctly."""
        with patch('app.api.sessions.service.SessionRepository') as mock_repo_class, \
             patch('app.api.sessions.service.SSHProfileRepository') as mock_ssh_repo_class:
            
            service = SessionService(mock_session)
            
            assert service.session == mock_session
            assert service._active_sessions == {}
            assert service._background_tasks == set()
            mock_repo_class.assert_called_once_with(mock_session)
            mock_ssh_repo_class.assert_called_once_with(mock_session)

    # Create session tests
    async def test_create_session_success(self, session_service, sample_user, sample_session_create, mock_session_repo, mock_session):
        """Test successful session creation."""
        # Setup mocks
        mock_session_repo.get_user_session_by_name.return_value = None
        mock_session_repo.create.return_value = Session(
            id="test-session-id",
            user_id=sample_user.id,
            name=sample_session_create.name,
            session_type=sample_session_create.session_type.value,
            status="pending",
            mode=sample_session_create.mode.value,
            is_active=True
        )
        
        with patch.object(session_service, '_initialize_session') as mock_initialize:
            result = await session_service.create_session(sample_user, sample_session_create)
            
            assert isinstance(result, SessionResponse)
            assert result.name == sample_session_create.name
            mock_session_repo.create.assert_called_once()
            mock_session.commit.assert_called_once()
            mock_initialize.assert_called_once()

    async def test_create_session_with_ssh_profile(self, session_service, sample_user, sample_session_create, mock_ssh_profile_repo, mock_session_repo, mock_session):
        """Test session creation with SSH profile."""
        # Setup SSH profile
        ssh_profile = SSHProfile(
            id="ssh-profile-id",
            user_id=sample_user.id,
            name="Test SSH",
            host="example.com",
            port=22,
            username="user"
        )
        
        sample_session_create.ssh_profile_id = ssh_profile.id
        
        # Setup mocks
        mock_ssh_profile_repo.get_by_id.return_value = ssh_profile
        mock_session_repo.get_user_session_by_name.return_value = None
        mock_session_repo.create.return_value = Session(
            id="test-session-id",
            user_id=sample_user.id,
            name=sample_session_create.name,
            ssh_profile_id=ssh_profile.id,
            status="pending",
            is_active=True
        )
        
        with patch.object(session_service, '_initialize_session'):
            result = await session_service.create_session(sample_user, sample_session_create)
            
            assert isinstance(result, SessionResponse)
            mock_ssh_profile_repo.get_by_id.assert_called_once_with(ssh_profile.id)
            mock_session_repo.create.assert_called_once()

    async def test_create_session_ssh_profile_not_found(self, session_service, sample_user, sample_session_create, mock_ssh_profile_repo):
        """Test session creation with non-existent SSH profile."""
        sample_session_create.ssh_profile_id = "non-existent-id"
        mock_ssh_profile_repo.get_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.create_session(sample_user, sample_session_create)
        
        assert exc_info.value.status_code == 404
        assert "SSH profile not found" in exc_info.value.detail

    async def test_create_session_duplicate_name(self, session_service, sample_user, sample_session_create, mock_session_repo):
        """Test session creation with duplicate active name."""
        # Mock existing active session
        existing_session = Session(
            id="existing-id",
            user_id=sample_user.id,
            name=sample_session_create.name,
            status="active"
        )
        mock_session_repo.get_user_session_by_name.return_value = existing_session
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.create_session(sample_user, sample_session_create)
        
        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail

    async def test_create_session_integrity_error(self, session_service, sample_user, sample_session_create, mock_session_repo, mock_session):
        """Test session creation with database integrity error."""
        mock_session_repo.get_user_session_by_name.return_value = None
        mock_session_repo.create.side_effect = IntegrityError("Duplicate key", None, None)
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.create_session(sample_user, sample_session_create)
        
        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail
        mock_session.rollback.assert_called_once()

    async def test_create_session_general_error(self, session_service, sample_user, sample_session_create, mock_session_repo, mock_session):
        """Test session creation with general error."""
        mock_session_repo.get_user_session_by_name.return_value = None
        mock_session_repo.create.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.create_session(sample_user, sample_session_create)
        
        assert exc_info.value.status_code == 500
        assert "Failed to create" in exc_info.value.detail
        mock_session.rollback.assert_called_once()

    # Get sessions tests
    async def test_get_user_sessions_success(self, session_service, sample_user, sample_session, mock_session_repo):
        """Test successful user sessions retrieval."""
        sessions = [sample_session]
        mock_session_repo.get_user_sessions.return_value = sessions
        mock_session_repo.count_user_sessions.return_value = 1
        
        result, total = await session_service.get_user_sessions(sample_user)
        
        assert len(result) == 1
        assert total == 1
        assert isinstance(result[0], SessionResponse)
        mock_session_repo.get_user_sessions.assert_called_once_with(
            sample_user.id, active_only=False, offset=0, limit=50
        )

    async def test_get_user_sessions_with_memory_updates(self, session_service, sample_user, sample_session, mock_session_repo):
        """Test user sessions retrieval with memory status updates."""
        sessions = [sample_session]
        mock_session_repo.get_user_sessions.return_value = sessions
        mock_session_repo.count_user_sessions.return_value = 1
        
        # Add session to memory with updated status
        session_service._active_sessions[str(sample_session.id)] = {
            "status": "connecting",
            "last_activity": datetime.now(UTC)
        }
        
        result, total = await session_service.get_user_sessions(sample_user)
        
        assert len(result) == 1
        assert total == 1

    async def test_get_user_sessions_error(self, session_service, sample_user, mock_session_repo):
        """Test user sessions retrieval with error."""
        mock_session_repo.get_user_sessions.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.get_user_sessions(sample_user)
        
        assert exc_info.value.status_code == 500
        assert "Failed to fetch" in exc_info.value.detail

    # Get single session tests
    async def test_get_session_success(self, session_service, sample_user, sample_session, mock_session_repo):
        """Test successful single session retrieval."""
        mock_session_repo.get_by_id.return_value = sample_session
        
        result = await session_service.get_session(sample_user, sample_session.id)
        
        assert isinstance(result, SessionResponse)
        assert result.name == sample_session.name
        mock_session_repo.get_by_id.assert_called_once_with(sample_session.id)

    async def test_get_session_not_found(self, session_service, sample_user, mock_session_repo):
        """Test single session retrieval when session not found."""
        mock_session_repo.get_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.get_session(sample_user, "non-existent-id")
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    async def test_get_session_wrong_user(self, session_service, sample_user, sample_session, mock_session_repo):
        """Test single session retrieval with wrong user."""
        sample_session.user_id = "different-user-id"
        mock_session_repo.get_by_id.return_value = sample_session
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.get_session(sample_user, sample_session.id)
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    # Update session tests
    async def test_update_session_success(self, session_service, sample_user, sample_session, mock_session_repo, mock_session):
        """Test successful session update."""
        mock_session_repo.get_by_id.return_value = sample_session
        mock_session_repo.update.return_value = sample_session
        
        update_data = SessionUpdate(
            description="Updated description",
            terminal_size={"cols": 120, "rows": 30}
        )
        
        result = await session_service.update_session(sample_user, sample_session.id, update_data)
        
        assert isinstance(result, SessionResponse)
        assert sample_session.description == "Updated description"
        assert sample_session.terminal_cols == 120
        assert sample_session.terminal_rows == 30
        mock_session_repo.update.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_update_session_not_found(self, session_service, sample_user, mock_session_repo):
        """Test session update when session not found."""
        mock_session_repo.get_by_id.return_value = None
        update_data = SessionUpdate(description="Updated")
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.update_session(sample_user, "non-existent-id", update_data)
        
        assert exc_info.value.status_code == 404

    async def test_update_session_failed_update(self, session_service, sample_user, sample_session, mock_session_repo, mock_session):
        """Test session update with failed repository update."""
        mock_session_repo.get_by_id.return_value = sample_session
        mock_session_repo.update.return_value = None
        
        update_data = SessionUpdate(description="Updated")
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.update_session(sample_user, sample_session.id, update_data)
        
        assert exc_info.value.status_code == 500
        assert "Failed to update" in exc_info.value.detail

    # Terminate session tests
    async def test_terminate_session_success(self, session_service, sample_user, sample_session, mock_session_repo, mock_session):
        """Test successful session termination."""
        mock_session_repo.get_by_id.return_value = sample_session
        mock_session_repo.update.return_value = sample_session
        
        with patch.object(session_service, '_terminate_session_process') as mock_terminate:
            result = await session_service.terminate_session(sample_user, sample_session.id)
            
            assert result is True
            assert sample_session.status == "terminated"
            assert sample_session.is_active is False
            mock_terminate.assert_called_once_with(sample_session.id)
            mock_session.commit.assert_called_once()

    async def test_terminate_session_already_terminated(self, session_service, sample_user, sample_session, mock_session_repo):
        """Test termination of already terminated session."""
        sample_session.status = "terminated"
        mock_session_repo.get_by_id.return_value = sample_session
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.terminate_session(sample_user, sample_session.id)
        
        assert exc_info.value.status_code == 400
        assert "already terminated" in exc_info.value.detail

    async def test_terminate_session_force(self, session_service, sample_user, sample_session, mock_session_repo, mock_session):
        """Test forced session termination."""
        sample_session.status = "terminated"
        mock_session_repo.get_by_id.return_value = sample_session
        mock_session_repo.update.return_value = sample_session
        
        with patch.object(session_service, '_terminate_session_process') as mock_terminate:
            result = await session_service.terminate_session(sample_user, sample_session.id, force=True)
            
            assert result is True
            mock_terminate.assert_called_once()

    # Delete session tests
    async def test_delete_session_success(self, session_service, sample_user, sample_session, mock_session_repo, mock_session):
        """Test successful session deletion."""
        sample_session.status = "terminated"
        mock_session_repo.get_by_id.return_value = sample_session
        
        with patch.object(session_service, '_cleanup_session_data') as mock_cleanup:
            result = await session_service.delete_session(sample_user, sample_session.id)
            
            assert result is True
            mock_cleanup.assert_called_once_with(sample_session.id)
            mock_session_repo.delete.assert_called_once_with(sample_session.id)
            mock_session.commit.assert_called_once()

    async def test_delete_active_session(self, session_service, sample_user, sample_session, mock_session_repo, mock_session):
        """Test deletion of active session."""
        sample_session.status = "active"
        mock_session_repo.get_by_id.return_value = sample_session
        
        with patch.object(session_service, '_terminate_session_process') as mock_terminate, \
             patch.object(session_service, '_cleanup_session_data') as mock_cleanup:
            
            result = await session_service.delete_session(sample_user, sample_session.id)
            
            assert result is True
            mock_terminate.assert_called_once_with(sample_session.id)
            mock_cleanup.assert_called_once()

    # Execute command tests
    async def test_execute_command_success(self, session_service, sample_user, sample_session, mock_session_repo):
        """Test successful command execution."""
        sample_session.status = "active"
        mock_session_repo.get_by_id.return_value = sample_session
        
        command = SessionCommand(
            command="ls -la",
            working_directory="/home/user"
        )
        
        with patch.object(session_service, '_execute_session_command') as mock_execute, \
             patch.object(session_service, '_update_session_activity') as mock_update:
            
            mock_result = SessionCommandResponse(
                command_id="cmd-id",
                command="ls -la",
                status="completed",
                stdout="file1 file2",
                stderr="",
                exit_code=0,
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                duration_ms=100,
                session_id=sample_session.id,
                working_directory="/home/user"
            )
            mock_execute.return_value = mock_result
            
            result = await session_service.execute_command(sample_user, sample_session.id, command)
            
            assert isinstance(result, SessionCommandResponse)
            assert result.command == "ls -la"
            mock_execute.assert_called_once_with(sample_session.id, command)
            mock_update.assert_called_once_with(sample_session.id)

    async def test_execute_command_inactive_session(self, session_service, sample_user, sample_session, mock_session_repo):
        """Test command execution on inactive session."""
        sample_session.status = "terminated"
        mock_session_repo.get_by_id.return_value = sample_session
        
        command = SessionCommand(command="ls -la")
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.execute_command(sample_user, sample_session.id, command)
        
        assert exc_info.value.status_code == 400
        assert "not active" in exc_info.value.detail

    # Session history tests
    async def test_get_session_history_success(self, session_service, sample_user, sample_session, mock_session_repo):
        """Test successful session history retrieval."""
        mock_session_repo.get_by_id.return_value = sample_session
        
        # Mock command data
        mock_commands = [
            MagicMock(
                id="cmd-1",
                command="ls -la",
                executed_at=datetime.now(UTC),
                exit_code=0,
                duration_ms=100,
                working_directory="/home/user"
            )
        ]
        mock_session_repo.get_session_commands.return_value = mock_commands
        mock_session_repo.count_session_commands.return_value = 1
        
        result = await session_service.get_session_history(sample_user, sample_session.id)
        
        assert isinstance(result, SessionHistoryResponse)
        assert result.session_id == sample_session.id
        assert len(result.entries) == 1
        assert result.total_entries == 1

    # Search sessions tests
    async def test_search_sessions_success(self, session_service, sample_user, sample_session, mock_session_repo):
        """Test successful session search."""
        sessions = [sample_session]
        mock_session_repo.search_sessions.return_value = sessions
        mock_session_repo.count_sessions_with_criteria.return_value = 1
        
        search_request = SessionSearchRequest(
            search_term="test",
            session_type=SessionType.LOCAL,
            status=SessionStatus.ACTIVE
        )
        
        result, total = await session_service.search_sessions(sample_user, search_request)
        
        assert len(result) == 1
        assert total == 1
        assert isinstance(result[0], SessionResponse)

    # Session statistics tests
    async def test_get_session_stats_success(self, session_service, sample_user, mock_session_repo):
        """Test successful session statistics retrieval."""
        # Mock stats data
        mock_stats_data = {
            "total_sessions": 5,
            "active_sessions": 2,
            "by_type": {"local": 3, "ssh": 2},
            "by_status": {"active": 2, "terminated": 3},
            "most_used_profiles": [],
            "sessions": [
                MagicMock(
                    duration_seconds=3600,
                    command_count=10,
                    created_at=datetime.now(UTC)
                )
            ]
        }
        mock_session_repo.get_user_session_stats.return_value = mock_stats_data
        
        result = await session_service.get_session_stats(sample_user)
        
        assert isinstance(result, SessionStats)
        assert result.total_sessions == 5
        assert result.active_sessions == 2

    # Health check tests
    async def test_check_session_health_success(self, session_service, sample_user, sample_session, mock_session_repo):
        """Test successful session health check."""
        sample_session.start_time = datetime.now(UTC) - timedelta(hours=1)
        mock_session_repo.get_by_id.return_value = sample_session
        
        with patch.object(session_service, '_check_session_health') as mock_health:
            mock_health.return_value = True
            
            result = await session_service.check_session_health(sample_user, sample_session.id)
            
            assert isinstance(result, SessionHealthCheck)
            assert result.session_id == sample_session.id
            assert result.is_healthy is True
            assert result.uptime_seconds > 0

    # Private method tests
    async def test_initialize_session_memory(self, session_service, sample_session):
        """Test session initialization in memory."""
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task
            
            await session_service._initialize_session(sample_session)
            
            assert str(sample_session.id) in session_service._active_sessions
            memory_session = session_service._active_sessions[str(sample_session.id)]
            assert memory_session["status"] == "connecting"
            assert memory_session["command_count"] == 0

    async def test_terminate_session_process_cleanup(self, session_service):
        """Test session process termination and cleanup."""
        session_id = "test-session-id"
        session_service._active_sessions[session_id] = {"status": "active"}
        
        await session_service._terminate_session_process(session_id)
        
        assert session_id not in session_service._active_sessions

    async def test_cleanup_session_data(self, session_service):
        """Test session data cleanup."""
        session_id = "test-session-id"
        session_service._active_sessions[session_id] = {"status": "active"}
        
        await session_service._cleanup_session_data(session_id)
        
        assert session_id not in session_service._active_sessions

    async def test_update_session_activity(self, session_service):
        """Test session activity update."""
        session_id = "test-session-id"
        session_service._active_sessions[session_id] = {
            "last_activity": datetime.now(UTC) - timedelta(minutes=5),
            "command_count": 5
        }
        
        await session_service._update_session_activity(session_id)
        
        memory_session = session_service._active_sessions[session_id]
        assert memory_session["command_count"] == 6
        # last_activity should be updated to a more recent time

    async def test_check_session_health_inactive(self, session_service):
        """Test health check for inactive session."""
        session_id = "test-session-id"
        
        result = await session_service._check_session_health(session_id)
        
        assert result is False

    async def test_check_session_health_stale(self, session_service):
        """Test health check for stale session."""
        session_id = "test-session-id"
        old_time = datetime.now(UTC) - timedelta(hours=2)
        session_service._active_sessions[session_id] = {
            "status": "active",
            "last_activity": old_time
        }
        
        result = await session_service._check_session_health(session_id)
        
        assert result is False

    async def test_execute_session_command_success(self, session_service):
        """Test session command execution."""
        session_id = "test-session-id"
        command = SessionCommand(
            command="echo hello",
            working_directory="/tmp"
        )
        
        result = await session_service._execute_session_command(session_id, command)
        
        assert isinstance(result, SessionCommandResponse)
        assert result.command == "echo hello"
        assert result.status == "completed"
        assert result.exit_code == 0
        assert "successfully" in result.stdout

    async def test_start_session_process_success(self, session_service, sample_session, mock_session_repo, mock_session):
        """Test successful session process start."""
        session_service._active_sessions[str(sample_session.id)] = {"status": "connecting"}
        mock_session_repo.update.return_value = sample_session
        
        await session_service._start_session_process(sample_session)
        
        assert sample_session.status == "active"
        mock_session_repo.update.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_start_session_process_failure(self, session_service, sample_session, mock_session_repo, mock_session):
        """Test session process start failure."""
        mock_session_repo.update.side_effect = [Exception("Connection failed"), sample_session]
        
        await session_service._start_session_process(sample_session)
        
        assert sample_session.status == "failed"
        assert sample_session.error_message == "Connection failed"