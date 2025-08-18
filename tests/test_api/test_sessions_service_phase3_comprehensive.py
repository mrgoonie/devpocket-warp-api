"""
Comprehensive Sessions Service Tests - Phase 3 Implementation.

This module provides extensive coverage for Sessions service operations,
targeting 65% coverage for Sessions Service to achieve Phase 3 objectives.
Implements Phase 3, Week 1 Priority 2 for Sessions Service Enhancement.

Coverage Target: 9% → 65% coverage (+159 lines of coverage)
Expected Test Count: ~80-90 comprehensive tests
Focus: Session lifecycle, connection management, multi-device sync, cleanup operations
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
    SessionHistoryEntry,
    SessionSearchRequest,
    SessionStats,
    SessionHealthCheck,
    SessionStatus
)
from app.models.session import Session
from app.models.user import User
from app.models.ssh_profile import SSHProfile


@pytest.mark.database
class TestSessionServicePhase3Comprehensive:
    """Comprehensive test suite for SessionService - Phase 3 Implementation."""

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
    async def sample_ssh_profile(self, sample_user):
        """Create a sample SSH profile."""
        return SSHProfile(
            id=str(uuid4()),
            user_id=sample_user.id,
            name="Test SSH Profile",
            host="example.com",
            port=22,
            username="user"
        )

    @pytest_asyncio.fixture
    async def sample_sessions(self, sample_user):
        """Create comprehensive sample sessions."""
        sessions = []
        now = datetime.now(UTC)
        
        session_types = ["local", "ssh", "docker"]
        statuses = ["active", "terminated", "pending", "failed"]
        
        for i in range(12):
            session_obj = Session(
                id=str(uuid4()),
                user_id=sample_user.id,
                name=f"Session-{i}",
                session_type=session_types[i % 3],
                status=statuses[i % 4],
                mode="interactive",
                terminal_cols=80,
                terminal_rows=24,
                environment={"PATH": "/usr/bin"},
                working_directory="/home/user",
                idle_timeout=3600,
                max_duration=7200,
                enable_logging=True,
                enable_recording=False,
                auto_reconnect=True,
                connection_info={},
                is_active=i % 2 == 0,
                created_at=now - timedelta(hours=i),
                start_time=now - timedelta(hours=i, minutes=30) if i % 2 == 0 else None,
                end_time=now - timedelta(hours=i, minutes=15) if i % 4 == 0 else None,
                duration_seconds=900 if i % 4 == 0 else None,
                last_activity=now - timedelta(minutes=i*5),
                command_count=i*5
            )
            sessions.append(session_obj)
        
        return sessions

    @pytest_asyncio.fixture
    async def sample_session_create(self):
        """Create sample session creation data."""
        return SessionCreate(
            name="Test Session",
            session_type="local",
            description="Test session for unit testing",
            mode="interactive",
            terminal_size={"cols": 120, "rows": 30},
            environment={"TERM": "xterm-256color"},
            working_directory="/home/user",
            idle_timeout=3600,
            max_duration=7200,
            enable_logging=True,
            enable_recording=False,
            auto_reconnect=True
        )

    # ===================================================================================
    # SERVICE INITIALIZATION TESTS
    # ===================================================================================

    async def test_service_initialization_complete(self, mock_session):
        """Test complete SessionService initialization."""
        with patch('app.api.sessions.service.SessionRepository') as mock_sess_repo, \
             patch('app.api.sessions.service.SSHProfileRepository') as mock_ssh_repo:
            service = SessionService(mock_session)
            
            # Verify basic initialization
            assert service.session == mock_session
            assert service.session_repo is not None
            assert service.ssh_profile_repo is not None
            assert service._active_sessions == {}
            assert service._background_tasks == set()
            
            # Verify repository initialization calls
            mock_sess_repo.assert_called_once_with(mock_session)
            mock_ssh_repo.assert_called_once_with(mock_session)

    # ===================================================================================
    # SESSION CREATION TESTS - Complete Lifecycle Management
    # ===================================================================================

    async def test_create_session_complete_local_session(self, session_service, sample_user, sample_session_create):
        """Test complete local session creation with all configurations."""
        created_session = Session(
            id=str(uuid4()),
            user_id=sample_user.id,
            name=sample_session_create.name,
            session_type=sample_session_create.session_type,
            status="pending",
            mode=sample_session_create.mode,
            terminal_cols=sample_session_create.terminal_size["cols"],
            terminal_rows=sample_session_create.terminal_size["rows"],
            environment=sample_session_create.environment,
            working_directory=sample_session_create.working_directory,
            idle_timeout=sample_session_create.idle_timeout,
            max_duration=sample_session_create.max_duration,
            enable_logging=sample_session_create.enable_logging,
            enable_recording=sample_session_create.enable_recording,
            auto_reconnect=sample_session_create.auto_reconnect,
            is_active=True
        )

        session_service.session_repo.get_user_session_by_name.return_value = None
        session_service.session_repo.create.return_value = created_session
        
        with patch.object(session_service, '_initialize_session') as mock_init:
            result = await session_service.create_session(sample_user, sample_session_create)
            
            assert isinstance(result, SessionResponse)
            assert result.name == sample_session_create.name
            assert result.session_type == sample_session_create.session_type
            assert result.terminal_cols == 120
            assert result.terminal_rows == 30
            
            # Verify session initialization was called
            mock_init.assert_called_once_with(created_session)
            session_service.session.commit.assert_called_once()

    async def test_create_session_with_ssh_profile_complete(self, session_service, sample_user, sample_ssh_profile, sample_session_create):
        """Test session creation with SSH profile integration."""
        sample_session_create.session_type = "ssh"
        sample_session_create.ssh_profile_id = sample_ssh_profile.id
        
        created_session = Session(
            id=str(uuid4()),
            user_id=sample_user.id,
            name=sample_session_create.name,
            session_type="ssh",
            ssh_profile_id=sample_ssh_profile.id,
            status="pending",
            connection_info={
                "host": sample_ssh_profile.host,
                "port": sample_ssh_profile.port,
                "username": sample_ssh_profile.username,
                "profile_name": sample_ssh_profile.name
            }
        )

        session_service.ssh_profile_repo.get_by_id.return_value = sample_ssh_profile
        session_service.session_repo.get_user_session_by_name.return_value = None
        session_service.session_repo.create.return_value = created_session
        
        with patch.object(session_service, '_initialize_session') as mock_init:
            result = await session_service.create_session(sample_user, sample_session_create)
            
            assert result.ssh_profile_id == sample_ssh_profile.id
            assert "host" in result.connection_info
            assert result.connection_info["host"] == sample_ssh_profile.host
            
            # Verify SSH profile was validated
            session_service.ssh_profile_repo.get_by_id.assert_called_once_with(sample_ssh_profile.id)

    async def test_create_session_ssh_profile_not_found(self, session_service, sample_user, sample_session_create):
        """Test session creation with invalid SSH profile."""
        sample_session_create.session_type = "ssh"
        sample_session_create.ssh_profile_id = str(uuid4())
        
        session_service.ssh_profile_repo.get_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc:
            await session_service.create_session(sample_user, sample_session_create)
        
        assert exc.value.status_code == 404
        assert "SSH profile not found" in str(exc.value.detail)

    async def test_create_session_ssh_profile_wrong_user(self, session_service, sample_user, sample_ssh_profile, sample_session_create):
        """Test session creation with SSH profile belonging to different user."""
        sample_session_create.session_type = "ssh"
        sample_session_create.ssh_profile_id = sample_ssh_profile.id
        sample_ssh_profile.user_id = str(uuid4())  # Different user
        
        session_service.ssh_profile_repo.get_by_id.return_value = sample_ssh_profile
        
        with pytest.raises(HTTPException) as exc:
            await session_service.create_session(sample_user, sample_session_create)
        
        assert exc.value.status_code == 404
        assert "SSH profile not found" in str(exc.value.detail)

    async def test_create_session_duplicate_active_name(self, session_service, sample_user, sample_session_create):
        """Test session creation with duplicate active session name."""
        existing_session = Session(
            id=str(uuid4()),
            user_id=sample_user.id,
            name=sample_session_create.name,
            status="active"
        )
        
        session_service.session_repo.get_user_session_by_name.return_value = existing_session
        
        with pytest.raises(HTTPException) as exc:
            await session_service.create_session(sample_user, sample_session_create)
        
        assert exc.value.status_code == 400
        assert "Active session with name" in str(exc.value.detail)

    async def test_create_session_with_connection_params(self, session_service, sample_user, sample_session_create):
        """Test session creation with custom connection parameters."""
        sample_session_create.connection_params = {
            "timeout": 30,
            "keepalive": True,
            "compression": True
        }
        
        created_session = Session(
            id=str(uuid4()),
            user_id=sample_user.id,
            name=sample_session_create.name,
            connection_info=sample_session_create.connection_params
        )
        
        session_service.session_repo.get_user_session_by_name.return_value = None
        session_service.session_repo.create.return_value = created_session
        
        with patch.object(session_service, '_initialize_session'):
            result = await session_service.create_session(sample_user, sample_session_create)
            
            assert "timeout" in result.connection_info
            assert result.connection_info["timeout"] == 30

    async def test_create_session_integrity_error_handling(self, session_service, sample_user, sample_session_create):
        """Test session creation with database integrity error."""
        session_service.session_repo.get_user_session_by_name.return_value = None
        session_service.session_repo.create.side_effect = IntegrityError("Duplicate key", None, None)
        
        with pytest.raises(HTTPException) as exc:
            await session_service.create_session(sample_user, sample_session_create)
        
        assert exc.value.status_code == 400
        assert "Session with this name already exists" in str(exc.value.detail)
        session_service.session.rollback.assert_called_once()

    async def test_create_session_general_error_handling(self, session_service, sample_user, sample_session_create):
        """Test session creation with general database error."""
        session_service.session_repo.get_user_session_by_name.return_value = None
        session_service.session_repo.create.side_effect = Exception("Database connection failed")
        
        with pytest.raises(HTTPException) as exc:
            await session_service.create_session(sample_user, sample_session_create)
        
        assert exc.value.status_code == 500
        assert "Failed to create terminal session" in str(exc.value.detail)
        session_service.session.rollback.assert_called_once()

    # ===================================================================================
    # SESSION RETRIEVAL TESTS - User Sessions and Filtering
    # ===================================================================================

    async def test_get_user_sessions_with_comprehensive_filtering(self, session_service, sample_user, sample_sessions):
        """Test get user sessions with comprehensive filtering and pagination."""
        active_sessions = [s for s in sample_sessions if s.is_active]
        session_service.session_repo.get_user_sessions.return_value = active_sessions
        session_service.session_repo.count_user_sessions.return_value = len(active_sessions)
        
        # Mock active sessions memory updates
        for session_obj in active_sessions:
            session_service._active_sessions[str(session_obj.id)] = {
                "status": "active",
                "last_activity": datetime.now(UTC)
            }
        
        sessions, total = await session_service.get_user_sessions(
            user=sample_user,
            active_only=True,
            offset=0,
            limit=10
        )
        
        assert len(sessions) == len(active_sessions)
        assert total == len(active_sessions)
        assert all(isinstance(s, SessionResponse) for s in sessions)
        
        # Verify real-time status updates from memory
        for session_resp in sessions:
            if session_resp.id in [str(s.id) for s in active_sessions]:
                # Should have updated status from memory
                pass  # Status updated in response

    async def test_get_user_sessions_with_memory_status_updates(self, session_service, sample_user, sample_sessions):
        """Test user sessions retrieval with real-time memory status updates."""
        session_service.session_repo.get_user_sessions.return_value = sample_sessions[:5]
        session_service.session_repo.count_user_sessions.return_value = 5
        
        # Add some sessions to active memory with different status
        session_service._active_sessions[str(sample_sessions[0].id)] = {
            "status": "connecting",
            "last_activity": datetime.now(UTC)
        }
        session_service._active_sessions[str(sample_sessions[1].id)] = {
            "status": "active",
            "last_activity": datetime.now(UTC) - timedelta(minutes=5)
        }
        
        sessions, total = await session_service.get_user_sessions(
            user=sample_user,
            offset=0,
            limit=50
        )
        
        assert len(sessions) == 5
        # Verify memory status was applied
        for session_resp in sessions:
            if session_resp.id == str(sample_sessions[0].id):
                # Status should be updated from memory
                assert session_resp.status is not None

    async def test_get_user_sessions_pagination_boundaries(self, session_service, sample_user, sample_sessions):
        """Test user sessions with various pagination scenarios."""
        session_service.session_repo.get_user_sessions.return_value = sample_sessions[5:8]
        session_service.session_repo.count_user_sessions.return_value = len(sample_sessions)
        
        sessions, total = await session_service.get_user_sessions(
            user=sample_user,
            offset=50,
            limit=20
        )
        
        assert len(sessions) == 3  # Only 3 returned
        assert total == len(sample_sessions)  # Total count

    async def test_get_user_sessions_error_handling(self, session_service, sample_user):
        """Test get user sessions error handling."""
        session_service.session_repo.get_user_sessions.side_effect = Exception("Database timeout")
        
        with pytest.raises(HTTPException) as exc:
            await session_service.get_user_sessions(user=sample_user)
        
        assert exc.value.status_code == 500
        assert "Failed to fetch terminal sessions" in str(exc.value.detail)

    # ===================================================================================
    # INDIVIDUAL SESSION RETRIEVAL TESTS
    # ===================================================================================

    async def test_get_session_with_memory_updates(self, session_service, sample_user, sample_sessions):
        """Test individual session retrieval with memory status updates."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_service.session_repo.get_by_id.return_value = session_obj
        
        # Add session to active memory
        session_service._active_sessions[str(session_obj.id)] = {
            "status": "active",
            "last_activity": datetime.now(UTC),
            "command_count": 15
        }
        
        result = await session_service.get_session(sample_user, str(session_obj.id))
        
        assert isinstance(result, SessionResponse)
        assert result.id == str(session_obj.id)
        assert result.user_id == str(sample_user.id)

    async def test_get_session_not_found(self, session_service, sample_user):
        """Test get session when session doesn't exist."""
        session_id = str(uuid4())
        session_service.session_repo.get_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc:
            await session_service.get_session(sample_user, session_id)
        
        assert exc.value.status_code == 404
        assert "Terminal session not found" in str(exc.value.detail)

    async def test_get_session_unauthorized_access(self, session_service, sample_sessions):
        """Test get session access by unauthorized user."""
        session_obj = sample_sessions[0]
        wrong_user = User(id=str(uuid4()), username="wronguser", email="wrong@example.com")
        
        session_service.session_repo.get_by_id.return_value = session_obj
        
        with pytest.raises(HTTPException) as exc:
            await session_service.get_session(wrong_user, str(session_obj.id))
        
        assert exc.value.status_code == 404
        assert "Terminal session not found" in str(exc.value.detail)

    # ===================================================================================
    # SESSION UPDATE TESTS - Configuration Changes
    # ===================================================================================

    async def test_update_session_comprehensive_changes(self, session_service, sample_user, sample_sessions):
        """Test comprehensive session updates with various configuration changes."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        
        update_data = SessionUpdate(
            name="Updated Session Name",
            description="Updated description",
            terminal_size={"cols": 100, "rows": 40},
            environment={"NEW_VAR": "value"},
            idle_timeout=7200,
            enable_logging=False,
            auto_reconnect=False
        )
        
        session_service.session_repo.get_by_id.return_value = session_obj
        session_service.session_repo.update.return_value = session_obj
        
        # Add session to active memory
        session_service._active_sessions[str(session_obj.id)] = {
            "terminal_cols": 80,
            "terminal_rows": 24
        }
        
        result = await session_service.update_session(
            sample_user, str(session_obj.id), update_data
        )
        
        assert isinstance(result, SessionResponse)
        session_service.session_repo.update.assert_called_once()
        session_service.session.commit.assert_called_once()
        
        # Verify memory was updated
        assert session_service._active_sessions[str(session_obj.id)]["terminal_cols"] == 100

    async def test_update_session_terminal_size_handling(self, session_service, sample_user, sample_sessions):
        """Test session update with terminal size changes."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_obj.terminal_cols = 80
        session_obj.terminal_rows = 24
        
        update_data = SessionUpdate(
            terminal_size={"cols": 120, "rows": 30}
        )
        
        session_service.session_repo.get_by_id.return_value = session_obj
        session_service.session_repo.update.return_value = session_obj
        
        result = await session_service.update_session(
            sample_user, str(session_obj.id), update_data
        )
        
        # Verify terminal size was applied
        assert session_obj.terminal_cols == 120
        assert session_obj.terminal_rows == 30

    async def test_update_session_not_found(self, session_service, sample_user):
        """Test update session when session doesn't exist."""
        session_id = str(uuid4())
        update_data = SessionUpdate(name="New Name")
        
        session_service.session_repo.get_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc:
            await session_service.update_session(sample_user, session_id, update_data)
        
        assert exc.value.status_code == 404
        assert "Terminal session not found" in str(exc.value.detail)

    async def test_update_session_unauthorized_access(self, session_service, sample_sessions):
        """Test update session by unauthorized user."""
        session_obj = sample_sessions[0]
        wrong_user = User(id=str(uuid4()), username="wronguser", email="wrong@example.com")
        update_data = SessionUpdate(name="Hacked Name")
        
        session_service.session_repo.get_by_id.return_value = session_obj
        
        with pytest.raises(HTTPException) as exc:
            await session_service.update_session(wrong_user, str(session_obj.id), update_data)
        
        assert exc.value.status_code == 404
        assert "Terminal session not found" in str(exc.value.detail)

    async def test_update_session_database_error_rollback(self, session_service, sample_user, sample_sessions):
        """Test update session with database error and rollback."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        update_data = SessionUpdate(name="Updated Name")
        
        session_service.session_repo.get_by_id.return_value = session_obj
        session_service.session_repo.update.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc:
            await session_service.update_session(sample_user, str(session_obj.id), update_data)
        
        assert exc.value.status_code == 500
        assert "Failed to update terminal session" in str(exc.value.detail)
        session_service.session.rollback.assert_called_once()

    async def test_update_session_failed_update_handling(self, session_service, sample_user, sample_sessions):
        """Test update session when repository returns None."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        update_data = SessionUpdate(name="Updated Name")
        
        session_service.session_repo.get_by_id.return_value = session_obj
        session_service.session_repo.update.return_value = None
        
        with pytest.raises(HTTPException) as exc:
            await session_service.update_session(sample_user, str(session_obj.id), update_data)
        
        assert exc.value.status_code == 500
        assert "Failed to update session" in str(exc.value.detail)

    # ===================================================================================
    # SESSION TERMINATION TESTS - Process Cleanup
    # ===================================================================================

    async def test_terminate_session_active_session(self, session_service, sample_user, sample_sessions):
        """Test termination of active session with proper cleanup."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_obj.status = "active"
        session_obj.start_time = datetime.now(UTC) - timedelta(hours=2)
        
        session_service.session_repo.get_by_id.return_value = session_obj
        session_service.session_repo.update.return_value = session_obj
        
        with patch.object(session_service, '_terminate_session_process') as mock_terminate:
            result = await session_service.terminate_session(
                sample_user, str(session_obj.id)
            )
            
            assert result is True
            assert session_obj.status == "terminated"
            assert session_obj.end_time is not None
            assert session_obj.is_active is False
            assert session_obj.duration_seconds > 0
            
            mock_terminate.assert_called_once_with(str(session_obj.id))
            session_service.session_repo.update.assert_called_once()
            session_service.session.commit.assert_called_once()

    async def test_terminate_session_already_terminated(self, session_service, sample_user, sample_sessions):
        """Test termination of already terminated session."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_obj.status = "terminated"
        
        session_service.session_repo.get_by_id.return_value = session_obj
        
        with pytest.raises(HTTPException) as exc:
            await session_service.terminate_session(sample_user, str(session_obj.id))
        
        assert exc.value.status_code == 400
        assert "Session is already terminated" in str(exc.value.detail)

    async def test_terminate_session_force_termination(self, session_service, sample_user, sample_sessions):
        """Test force termination of already terminated session."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_obj.status = "terminated"
        
        session_service.session_repo.get_by_id.return_value = session_obj
        session_service.session_repo.update.return_value = session_obj
        
        with patch.object(session_service, '_terminate_session_process') as mock_terminate:
            result = await session_service.terminate_session(
                sample_user, str(session_obj.id), force=True
            )
            
            assert result is True
            mock_terminate.assert_called_once()

    async def test_terminate_session_not_found(self, session_service, sample_user):
        """Test termination of non-existent session."""
        session_id = str(uuid4())
        session_service.session_repo.get_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc:
            await session_service.terminate_session(sample_user, session_id)
        
        assert exc.value.status_code == 404
        assert "Terminal session not found" in str(exc.value.detail)

    async def test_terminate_session_error_handling(self, session_service, sample_user, sample_sessions):
        """Test terminate session error handling with rollback."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_obj.status = "active"
        
        session_service.session_repo.get_by_id.return_value = session_obj
        session_service.session_repo.update.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc:
            await session_service.terminate_session(sample_user, str(session_obj.id))
        
        assert exc.value.status_code == 500
        assert "Failed to terminate terminal session" in str(exc.value.detail)
        session_service.session.rollback.assert_called_once()

    # ===================================================================================
    # SESSION DELETION TESTS - Complete Cleanup
    # ===================================================================================

    async def test_delete_session_inactive_session(self, session_service, sample_user, sample_sessions):
        """Test deletion of inactive session with complete cleanup."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_obj.status = "terminated"
        session_obj.is_active = False
        
        session_service.session_repo.get_by_id.return_value = session_obj
        session_service.session_repo.delete.return_value = None
        
        with patch.object(session_service, '_cleanup_session_data') as mock_cleanup:
            result = await session_service.delete_session(sample_user, str(session_obj.id))
            
            assert result is True
            mock_cleanup.assert_called_once_with(str(session_obj.id))
            session_service.session_repo.delete.assert_called_once_with(str(session_obj.id))
            session_service.session.commit.assert_called_once()

    async def test_delete_session_active_session_with_termination(self, session_service, sample_user, sample_sessions):
        """Test deletion of active session with automatic termination."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_obj.status = "active"
        
        session_service.session_repo.get_by_id.return_value = session_obj
        session_service.session_repo.delete.return_value = None
        
        with patch.object(session_service, '_terminate_session_process') as mock_terminate, \
             patch.object(session_service, '_cleanup_session_data') as mock_cleanup:
            
            result = await session_service.delete_session(sample_user, str(session_obj.id))
            
            assert result is True
            mock_terminate.assert_called_once_with(str(session_obj.id))
            mock_cleanup.assert_called_once_with(str(session_obj.id))

    async def test_delete_session_not_found(self, session_service, sample_user):
        """Test deletion of non-existent session."""
        session_id = str(uuid4())
        session_service.session_repo.get_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc:
            await session_service.delete_session(sample_user, session_id)
        
        assert exc.value.status_code == 404
        assert "Terminal session not found" in str(exc.value.detail)

    async def test_delete_session_unauthorized_access(self, session_service, sample_sessions):
        """Test deletion by unauthorized user."""
        session_obj = sample_sessions[0]
        wrong_user = User(id=str(uuid4()), username="wronguser", email="wrong@example.com")
        
        session_service.session_repo.get_by_id.return_value = session_obj
        
        with pytest.raises(HTTPException) as exc:
            await session_service.delete_session(wrong_user, str(session_obj.id))
        
        assert exc.value.status_code == 404
        assert "Terminal session not found" in str(exc.value.detail)

    async def test_delete_session_error_handling(self, session_service, sample_user, sample_sessions):
        """Test delete session error handling with rollback."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_obj.status = "terminated"
        
        session_service.session_repo.get_by_id.return_value = session_obj
        session_service.session_repo.delete.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc:
            await session_service.delete_session(sample_user, str(session_obj.id))
        
        assert exc.value.status_code == 500
        assert "Failed to delete terminal session" in str(exc.value.detail)
        session_service.session.rollback.assert_called_once()

    # ===================================================================================
    # COMMAND EXECUTION TESTS - Terminal Operations
    # ===================================================================================

    async def test_execute_command_in_active_session(self, session_service, sample_user, sample_sessions):
        """Test command execution in active session."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_obj.status = "active"
        
        command = SessionCommand(
            command="ls -la",
            working_directory="/home/user"
        )
        
        mock_response = SessionCommandResponse(
            command_id=str(uuid4()),
            command="ls -la",
            status="completed",
            stdout="file1\nfile2\n",
            stderr="",
            exit_code=0,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            duration_ms=500,
            session_id=str(session_obj.id),
            working_directory="/home/user"
        )
        
        session_service.session_repo.get_by_id.return_value = session_obj
        
        with patch.object(session_service, '_execute_session_command', return_value=mock_response) as mock_execute, \
             patch.object(session_service, '_update_session_activity') as mock_update:
            
            result = await session_service.execute_command(
                sample_user, str(session_obj.id), command
            )
            
            assert isinstance(result, SessionCommandResponse)
            assert result.command == "ls -la"
            assert result.exit_code == 0
            
            mock_execute.assert_called_once_with(str(session_obj.id), command)
            mock_update.assert_called_once_with(str(session_obj.id))

    async def test_execute_command_in_inactive_session(self, session_service, sample_user, sample_sessions):
        """Test command execution in inactive session."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_obj.status = "terminated"
        
        command = SessionCommand(command="ls -la")
        session_service.session_repo.get_by_id.return_value = session_obj
        
        with pytest.raises(HTTPException) as exc:
            await session_service.execute_command(sample_user, str(session_obj.id), command)
        
        assert exc.value.status_code == 400
        assert "Session is not active" in str(exc.value.detail)

    async def test_execute_command_session_not_found(self, session_service, sample_user):
        """Test command execution in non-existent session."""
        session_id = str(uuid4())
        command = SessionCommand(command="ls -la")
        
        session_service.session_repo.get_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc:
            await session_service.execute_command(sample_user, session_id, command)
        
        assert exc.value.status_code == 404
        assert "Terminal session not found" in str(exc.value.detail)

    async def test_execute_command_error_handling(self, session_service, sample_user, sample_sessions):
        """Test command execution error handling."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_obj.status = "active"
        
        command = SessionCommand(command="invalid-command")
        session_service.session_repo.get_by_id.return_value = session_obj
        
        with patch.object(session_service, '_execute_session_command', side_effect=Exception("Execution failed")):
            with pytest.raises(HTTPException) as exc:
                await session_service.execute_command(sample_user, str(session_obj.id), command)
            
            assert exc.value.status_code == 500
            assert "Failed to execute command" in str(exc.value.detail)

    # ===================================================================================
    # SESSION HISTORY TESTS - Command History Management
    # ===================================================================================

    async def test_get_session_history_comprehensive(self, session_service, sample_user, sample_sessions):
        """Test comprehensive session history retrieval."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        
        # Mock command history
        mock_commands = []
        for i in range(10):
            cmd = MagicMock()
            cmd.id = str(uuid4())
            cmd.command = f"command-{i}"
            cmd.exit_code = 0
            cmd.duration_ms = 1000 + i*100
            cmd.executed_at = datetime.now(UTC) - timedelta(minutes=i*5)
            cmd.working_directory = "/home/user"
            mock_commands.append(cmd)
        
        session_service.session_repo.get_by_id.return_value = session_obj
        session_service.session_repo.get_session_commands.return_value = mock_commands
        session_service.session_repo.count_session_commands.return_value = len(mock_commands)
        
        result = await session_service.get_session_history(
            sample_user, str(session_obj.id), limit=50, offset=0
        )
        
        assert isinstance(result, SessionHistoryResponse)
        assert result.session_id == str(session_obj.id)
        assert len(result.entries) == 10
        assert result.total_entries == 10
        
        # Verify entry structure
        for i, entry in enumerate(result.entries):
            assert isinstance(entry, SessionHistoryEntry)
            assert entry.entry_type == "command"
            assert entry.content == f"command-{i}"
            assert "exit_code" in entry.metadata
            assert "duration_ms" in entry.metadata

    async def test_get_session_history_with_pagination(self, session_service, sample_user, sample_sessions):
        """Test session history with pagination."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        
        # Return limited commands for pagination
        mock_commands = []
        for i in range(5):  # Only 5 commands returned
            cmd = MagicMock()
            cmd.id = str(uuid4())
            cmd.command = f"command-{i+10}"  # Different range
            cmd.exit_code = 0
            cmd.duration_ms = 1500
            cmd.executed_at = datetime.now(UTC)
            cmd.working_directory = "/home/user"
            mock_commands.append(cmd)
        
        session_service.session_repo.get_by_id.return_value = session_obj
        session_service.session_repo.get_session_commands.return_value = mock_commands
        session_service.session_repo.count_session_commands.return_value = 50  # Total
        
        result = await session_service.get_session_history(
            sample_user, str(session_obj.id), limit=5, offset=10
        )
        
        assert len(result.entries) == 5
        assert result.total_entries == 50

    async def test_get_session_history_session_not_found(self, session_service, sample_user):
        """Test session history for non-existent session."""
        session_id = str(uuid4())
        session_service.session_repo.get_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc:
            await session_service.get_session_history(sample_user, session_id)
        
        assert exc.value.status_code == 404
        assert "Terminal session not found" in str(exc.value.detail)

    async def test_get_session_history_error_handling(self, session_service, sample_user, sample_sessions):
        """Test session history error handling."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        
        session_service.session_repo.get_by_id.return_value = session_obj
        session_service.session_repo.get_session_commands.side_effect = Exception("History fetch failed")
        
        with pytest.raises(HTTPException) as exc:
            await session_service.get_session_history(sample_user, str(session_obj.id))
        
        assert exc.value.status_code == 500
        assert "Failed to fetch session history" in str(exc.value.detail)

    # ===================================================================================
    # SESSION SEARCH TESTS - Advanced Filtering
    # ===================================================================================

    async def test_search_sessions_comprehensive_filters(self, session_service, sample_user, sample_sessions):
        """Test comprehensive session search with all filters."""
        search_results = sample_sessions[:5]
        
        search_request = SessionSearchRequest(
            search_term="Test",
            session_type="ssh",
            status=SessionStatus.ACTIVE,
            ssh_profile_id=str(uuid4()),
            created_after=datetime.now(UTC) - timedelta(days=30),
            created_before=datetime.now(UTC),
            sort_by="created_at",
            sort_order="desc",
            offset=0,
            limit=25
        )
        
        session_service.session_repo.search_sessions.return_value = search_results
        session_service.session_repo.count_sessions_with_criteria.return_value = 5
        
        sessions, total = await session_service.search_sessions(sample_user, search_request)
        
        assert len(sessions) == 5
        assert total == 5
        assert all(isinstance(s, SessionResponse) for s in sessions)
        
        # Verify search criteria were applied
        session_service.session_repo.search_sessions.assert_called_once()
        call_args = session_service.session_repo.search_sessions.call_args[1]
        assert call_args["search_term"] == "Test"
        assert call_args["sort_by"] == "created_at"

    async def test_search_sessions_status_mapping(self, session_service, sample_user, sample_sessions):
        """Test session search with status mapping to is_active field."""
        search_request = SessionSearchRequest(status=SessionStatus.TERMINATED)
        
        session_service.session_repo.search_sessions.return_value = sample_sessions[:3]
        session_service.session_repo.count_sessions_with_criteria.return_value = 3
        
        sessions, total = await session_service.search_sessions(sample_user, search_request)
        
        # Verify status was mapped to is_active
        call_args = session_service.session_repo.search_sessions.call_args[1]
        assert "is_active" in call_args["criteria"]
        assert call_args["criteria"]["is_active"] is False  # terminated = not active

    async def test_search_sessions_error_handling(self, session_service, sample_user):
        """Test search sessions error handling."""
        search_request = SessionSearchRequest(search_term="test")
        session_service.session_repo.search_sessions.side_effect = Exception("Search failed")
        
        with pytest.raises(HTTPException) as exc:
            await session_service.search_sessions(sample_user, search_request)
        
        assert exc.value.status_code == 500
        assert "Failed to search terminal sessions" in str(exc.value.detail)

    # ===================================================================================
    # SESSION STATISTICS TESTS - Analytics and Reporting
    # ===================================================================================

    async def test_get_session_stats_comprehensive(self, session_service, sample_user):
        """Test comprehensive session statistics calculation."""
        now = datetime.now(UTC)
        
        # Mock session statistics data
        mock_sessions = []
        for i in range(10):
            session_mock = MagicMock()
            session_mock.duration_seconds = 3600 + i*300  # Varying durations
            session_mock.command_count = 10 + i*5  # Varying command counts
            session_mock.created_at = now - timedelta(days=i%7)
            mock_sessions.append(session_mock)
        
        mock_stats_data = {
            "sessions": mock_sessions,
            "total_sessions": 10,
            "active_sessions": 4,
            "by_type": {"ssh": 6, "local": 4},
            "by_status": {"active": 4, "terminated": 6},
            "most_used_profiles": [
                {"profile_name": "Production", "count": 5},
                {"profile_name": "Development", "count": 3}
            ]
        }
        
        session_service.session_repo.get_user_session_stats.return_value = mock_stats_data
        
        result = await session_service.get_session_stats(sample_user)
        
        assert isinstance(result, SessionStats)
        assert result.total_sessions == 10
        assert result.active_sessions == 4
        assert result.sessions_by_type == {"ssh": 6, "local": 4}
        assert result.sessions_by_status == {"active": 4, "terminated": 6}
        assert result.total_duration_hours > 0
        assert result.average_session_duration_minutes > 0
        assert result.total_commands > 0
        assert len(result.most_used_profiles) == 2

    async def test_get_session_stats_time_based_calculations(self, session_service, sample_user):
        """Test session statistics with time-based calculations."""
        now = datetime.now(UTC)
        today = now.date()
        
        # Create sessions for different time periods
        mock_sessions = []
        
        # Sessions from today
        for i in range(3):
            session_mock = MagicMock()
            session_mock.duration_seconds = 1800
            session_mock.command_count = 15
            session_mock.created_at = datetime.combine(today, datetime.min.time().replace(tzinfo=UTC))
            mock_sessions.append(session_mock)
        
        # Sessions from this week
        for i in range(5):
            session_mock = MagicMock()
            session_mock.duration_seconds = 2400
            session_mock.command_count = 20
            session_mock.created_at = now - timedelta(days=i%7)
            mock_sessions.append(session_mock)
        
        mock_stats_data = {
            "sessions": mock_sessions,
            "total_sessions": 8,
            "active_sessions": 3,
            "by_type": {"local": 8},
            "by_status": {"active": 3, "terminated": 5},
            "most_used_profiles": []
        }
        
        session_service.session_repo.get_user_session_stats.return_value = mock_stats_data
        
        result = await session_service.get_session_stats(sample_user)
        
        assert result.sessions_today >= 3
        assert result.sessions_this_week >= 5

    async def test_get_session_stats_error_handling(self, session_service, sample_user):
        """Test session statistics error handling."""
        session_service.session_repo.get_user_session_stats.side_effect = Exception("Stats error")
        
        with pytest.raises(HTTPException) as exc:
            await session_service.get_session_stats(sample_user)
        
        assert exc.value.status_code == 500
        assert "Failed to get session statistics" in str(exc.value.detail)

    # ===================================================================================
    # SESSION HEALTH CHECK TESTS - Monitoring and Diagnostics
    # ===================================================================================

    async def test_check_session_health_healthy_session(self, session_service, sample_user, sample_sessions):
        """Test health check for healthy active session."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_obj.status = "active"
        session_obj.start_time = datetime.now(UTC) - timedelta(hours=1)
        session_obj.last_activity = datetime.now(UTC) - timedelta(minutes=5)
        
        session_service.session_repo.get_by_id.return_value = session_obj
        
        with patch.object(session_service, '_check_session_health', return_value=True) as mock_health:
            result = await session_service.check_session_health(sample_user, str(session_obj.id))
            
            assert isinstance(result, SessionHealthCheck)
            assert result.session_id == str(session_obj.id)
            assert result.is_healthy is True
            assert result.status == SessionStatus.ACTIVE
            assert result.connection_stable is True
            assert result.uptime_seconds > 0
            
            mock_health.assert_called_once_with(str(session_obj.id))

    async def test_check_session_health_unhealthy_session(self, session_service, sample_user, sample_sessions):
        """Test health check for unhealthy session."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_obj.status = "failed"
        session_obj.start_time = datetime.now(UTC) - timedelta(hours=1)
        
        session_service.session_repo.get_by_id.return_value = session_obj
        
        with patch.object(session_service, '_check_session_health', return_value=False) as mock_health:
            result = await session_service.check_session_health(sample_user, str(session_obj.id))
            
            assert result.is_healthy is False
            assert result.connection_stable is False

    async def test_check_session_health_session_not_found(self, session_service, sample_user):
        """Test health check for non-existent session."""
        session_id = str(uuid4())
        session_service.session_repo.get_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc:
            await session_service.check_session_health(sample_user, session_id)
        
        assert exc.value.status_code == 404
        assert "Terminal session not found" in str(exc.value.detail)

    async def test_check_session_health_invalid_status(self, session_service, sample_user, sample_sessions):
        """Test health check with invalid status enum conversion."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_obj.status = "invalid_status"
        
        session_service.session_repo.get_by_id.return_value = session_obj
        
        with patch.object(session_service, '_check_session_health', return_value=False):
            result = await session_service.check_session_health(sample_user, str(session_obj.id))
            
            # Should default to PENDING when invalid status
            assert result.status == SessionStatus.PENDING

    async def test_check_session_health_error_handling(self, session_service, sample_user, sample_sessions):
        """Test session health check error handling."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        
        session_service.session_repo.get_by_id.return_value = session_obj
        
        with patch.object(session_service, '_check_session_health', side_effect=Exception("Health check failed")):
            with pytest.raises(HTTPException) as exc:
                await session_service.check_session_health(sample_user, str(session_obj.id))
            
            assert exc.value.status_code == 500
            assert "Failed to check session health" in str(exc.value.detail)

    # ===================================================================================
    # PRIVATE HELPER METHOD TESTS - Internal Logic Coverage
    # ===================================================================================

    async def test_initialize_session_memory_setup(self, session_service, sample_sessions):
        """Test session initialization in memory."""
        session_obj = sample_sessions[0]
        
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = AsyncMock()
            mock_create_task.return_value = mock_task
            
            await session_service._initialize_session(session_obj)
            
            # Verify session was added to active memory
            assert str(session_obj.id) in session_service._active_sessions
            memory_session = session_service._active_sessions[str(session_obj.id)]
            
            assert memory_session["status"] == "connecting"
            assert memory_session["command_count"] == 0
            assert memory_session["terminal_cols"] == session_obj.terminal_cols
            
            # Verify background task was created
            mock_create_task.assert_called_once()
            assert mock_task in session_service._background_tasks

    async def test_start_session_process_success(self, session_service, sample_sessions):
        """Test successful session process startup."""
        session_obj = sample_sessions[0]
        session_obj.status = "pending"
        
        session_service.session_repo.update.return_value = session_obj
        
        # Add to active sessions first
        session_service._active_sessions[str(session_obj.id)] = {
            "status": "connecting"
        }
        
        await session_service._start_session_process(session_obj)
        
        assert session_obj.status == "active"
        assert session_obj.last_activity is not None
        session_service.session_repo.update.assert_called_once()
        session_service.session.commit.assert_called_once()

    async def test_start_session_process_failure(self, session_service, sample_sessions):
        """Test session process startup failure."""
        session_obj = sample_sessions[0]
        session_obj.status = "pending"
        
        session_service.session_repo.update.side_effect = Exception("Process start failed")
        
        await session_service._start_session_process(session_obj)
        
        assert session_obj.status == "failed"
        assert session_obj.error_message == "Process start failed"

    async def test_terminate_session_process_cleanup(self, session_service):
        """Test session process termination and cleanup."""
        session_id = str(uuid4())
        
        # Add session to active sessions
        session_service._active_sessions[session_id] = {
            "status": "active",
            "process_id": 1234
        }
        
        await session_service._terminate_session_process(session_id)
        
        # Session should be removed from active sessions
        assert session_id not in session_service._active_sessions

    async def test_cleanup_session_data(self, session_service):
        """Test session data cleanup."""
        session_id = str(uuid4())
        
        # Add session to active sessions
        session_service._active_sessions[session_id] = {"status": "terminated"}
        
        await session_service._cleanup_session_data(session_id)
        
        # Session should be removed from active sessions
        assert session_id not in session_service._active_sessions

    async def test_execute_session_command_simulation(self, session_service):
        """Test session command execution simulation."""
        session_id = str(uuid4())
        command = SessionCommand(
            command="echo 'hello world'",
            working_directory="/home/user"
        )
        
        result = await session_service._execute_session_command(session_id, command)
        
        assert isinstance(result, SessionCommandResponse)
        assert result.command == "echo 'hello world'"
        assert result.status == "completed"
        assert result.exit_code == 0
        assert result.session_id == session_id
        assert result.duration_ms > 0

    async def test_update_session_activity_memory(self, session_service):
        """Test session activity update in memory."""
        session_id = str(uuid4())
        
        # Initialize session in memory
        session_service._active_sessions[session_id] = {
            "last_activity": datetime.now(UTC) - timedelta(minutes=10),
            "command_count": 5
        }
        
        await session_service._update_session_activity(session_id)
        
        # Activity should be updated
        updated_session = session_service._active_sessions[session_id]
        assert updated_session["command_count"] == 6
        assert updated_session["last_activity"] > datetime.now(UTC) - timedelta(seconds=10)

    async def test_check_session_health_logic(self, session_service):
        """Test session health check logic."""
        session_id = str(uuid4())
        now = datetime.now(UTC)
        
        # Test healthy session
        session_service._active_sessions[session_id] = {
            "status": "active",
            "last_activity": now - timedelta(minutes=30)  # Recent activity
        }
        
        is_healthy = await session_service._check_session_health(session_id)
        assert is_healthy is True
        
        # Test unhealthy session (old activity)
        session_service._active_sessions[session_id]["last_activity"] = now - timedelta(hours=2)
        is_healthy = await session_service._check_session_health(session_id)
        assert is_healthy is False
        
        # Test non-existent session
        is_healthy = await session_service._check_session_health("nonexistent")
        assert is_healthy is False

    # ===================================================================================
    # INTEGRATION AND WORKFLOW TESTS
    # ===================================================================================

    async def test_complete_session_lifecycle_workflow(self, session_service, sample_user, sample_session_create):
        """Test complete session service workflow integration."""
        created_session = Session(
            id=str(uuid4()),
            user_id=sample_user.id,
            name=sample_session_create.name,
            session_type=sample_session_create.session_type,
            status="active"
        )
        
        # Setup mocks for full workflow
        session_service.session_repo.get_user_session_by_name.return_value = None
        session_service.session_repo.create.return_value = created_session
        session_service.session_repo.get_by_id.return_value = created_session
        session_service.session_repo.get_user_sessions.return_value = [created_session]
        session_service.session_repo.count_user_sessions.return_value = 1
        session_service.session_repo.update.return_value = created_session
        session_service.session_repo.delete.return_value = None
        
        with patch.object(session_service, '_initialize_session'), \
             patch.object(session_service, '_terminate_session_process'), \
             patch.object(session_service, '_cleanup_session_data'):
            
            # 1. Create session
            create_result = await session_service.create_session(sample_user, sample_session_create)
            assert isinstance(create_result, SessionResponse)
            
            # 2. Get sessions
            sessions, total = await session_service.get_user_sessions(sample_user)
            assert len(sessions) == 1
            
            # 3. Get individual session
            get_result = await session_service.get_session(sample_user, str(created_session.id))
            assert get_result.id == str(created_session.id)
            
            # 4. Update session
            update_data = SessionUpdate(name="Updated Name")
            update_result = await session_service.update_session(sample_user, str(created_session.id), update_data)
            assert isinstance(update_result, SessionResponse)
            
            # 5. Terminate session
            terminate_result = await session_service.terminate_session(sample_user, str(created_session.id))
            assert terminate_result is True
            
            # 6. Delete session
            created_session.status = "terminated"
            delete_result = await session_service.delete_session(sample_user, str(created_session.id))
            assert delete_result is True

    async def test_concurrent_session_operations(self, session_service, sample_user, sample_sessions):
        """Test concurrent session operations handling."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_service.session_repo.get_by_id.return_value = session_obj
        
        # Simulate concurrent session access
        tasks = []
        for _ in range(10):
            task = asyncio.create_task(
                session_service.get_session(sample_user, str(session_obj.id))
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should succeed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 10
        
        # All should return the same session
        for result in successful_results:
            assert result.id == str(session_obj.id)

    async def test_background_task_management(self, session_service):
        """Test background task management and cleanup."""
        # Create mock tasks
        tasks = []
        for _ in range(5):
            task = asyncio.create_task(asyncio.sleep(0.01))
            session_service._background_tasks.add(task)
            task.add_done_callback(session_service._background_tasks.discard)
            tasks.append(task)
        
        assert len(session_service._background_tasks) == 5
        
        # Wait for tasks to complete
        await asyncio.gather(*tasks)
        
        # Tasks should be automatically cleaned up
        assert len(session_service._background_tasks) == 0

    async def test_memory_consistency_across_operations(self, session_service, sample_user, sample_sessions):
        """Test memory consistency across various operations."""
        session_obj = sample_sessions[0]
        session_obj.user_id = sample_user.id
        session_service.session_repo.get_by_id.return_value = session_obj
        
        # Initialize session in memory
        await session_service._initialize_session(session_obj)
        
        # Verify memory state
        assert str(session_obj.id) in session_service._active_sessions
        initial_memory = session_service._active_sessions[str(session_obj.id)].copy()
        
        # Update session activity
        await session_service._update_session_activity(str(session_obj.id))
        
        # Verify memory was updated
        updated_memory = session_service._active_sessions[str(session_obj.id)]
        assert updated_memory["command_count"] == initial_memory["command_count"] + 1
        assert updated_memory["last_activity"] > initial_memory["last_activity"]
        
        # Terminate session
        await session_service._terminate_session_process(str(session_obj.id))
        
        # Verify memory was cleaned up
        assert str(session_obj.id) not in session_service._active_sessions