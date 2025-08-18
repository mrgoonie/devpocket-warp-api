"""
Comprehensive Sessions Service tests for Phase 4 Week 1.

Target: Sessions Service coverage from 9% to 65% (+56 percentage points)
Focus: Complete implementation testing of all major service methods with edge cases.
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.sessions.schemas import (
    SessionCommand,
    SessionCommandResponse,
    SessionCreate,
    SessionHealthCheck,
    SessionHistoryResponse,
    SessionResponse,
    SessionSearchRequest,
    SessionStats,
    SessionStatus,
    SessionType,
    SessionUpdate,
    SessionMode,
)
from app.api.sessions.service import SessionService
from app.models.session import Session
from app.models.ssh_profile import SSHProfile
from app.models.user import User


@pytest.fixture
async def session_service(test_session):
    """Create SessionService instance for testing."""
    return SessionService(test_session)


@pytest.fixture
async def test_ssh_profile(test_session, verified_user):
    """Create a test SSH profile."""
    ssh_profile = SSHProfile(
        id=str(uuid.uuid4()),
        user_id=verified_user.id,
        name="Test SSH Profile",
        host="test.example.com",
        port=22,
        username="testuser",
    )
    test_session.add(ssh_profile)
    await test_session.commit()
    return ssh_profile


@pytest.fixture
async def test_user_with_sessions(test_session, verified_user, test_ssh_profile):
    """Create a test user with sample sessions."""
    user = verified_user
    
    # Create test sessions with various statuses and types
    sessions_data = [
        {
            "session_name": "Active Terminal Session",
            "session_type": "terminal", 
            "is_active": True,
            "device_id": str(uuid.uuid4()),
            "device_type": "web",
            "last_activity_at": datetime.now(UTC) - timedelta(minutes=5),
        },
        {
            "session_name": "SSH Session",
            "session_type": "ssh",
            "is_active": True,
            "device_id": str(uuid.uuid4()),
            "device_type": "terminal",
            "ssh_host": "test.example.com",
            "ssh_port": 22,
            "ssh_username": "testuser",
            "last_activity_at": datetime.now(UTC) - timedelta(minutes=2),
        },
        {
            "session_name": "Completed Session",
            "session_type": "terminal",
            "is_active": False,
            "device_id": str(uuid.uuid4()),
            "device_type": "mobile",
            "ended_at": datetime.now(UTC) - timedelta(hours=12),
        },
        {
            "session_name": "Failed Session",
            "session_type": "ssh",
            "is_active": False,
            "device_id": str(uuid.uuid4()),
            "device_type": "terminal",
            "error_message": "Connection refused",
        },
    ]
    
    sessions = []
    for session_data in sessions_data:
        session_obj = Session(
            user_id=user.id,
            **session_data
        )
        sessions.append(session_obj)
        test_session.add(session_obj)
    
    await test_session.commit()
    return user, sessions


class TestSessionServiceComprehensive:
    """Comprehensive tests for SessionService covering all major functionality."""
    
    async def test_create_session_terminal_success(self, session_service, verified_user):
        """Test successful terminal session creation."""
        session_data = SessionCreate(
            name="New Terminal Session",
            session_type=SessionType.LOCAL,
            mode=SessionMode.INTERACTIVE,
            description="Test terminal session",
            terminal_size={"cols": 80, "rows": 24},
            working_directory="/home/user",
            environment={"PATH": "/usr/bin:/bin"},
            enable_logging=True,
            enable_recording=False,
            auto_reconnect=True,
        )
        
        result = await session_service.create_session(verified_user, session_data)
        
        assert isinstance(result, SessionResponse)
        assert result.name == session_data.name
        assert result.session_type == session_data.session_type.value
        assert result.user_id == str(verified_user.id)
        assert result.status == "pending"
        assert result.is_active is True
    
    async def test_create_session_ssh_success(self, session_service, verified_user, test_ssh_profile):
        """Test successful SSH session creation with profile."""
        session_data = SessionCreate(
            name="New SSH Session",
            session_type=SessionType.SSH,
            mode=SessionMode.INTERACTIVE,
            ssh_profile_id=str(test_ssh_profile.id),
            terminal_size={"cols": 120, "rows": 30},
            enable_logging=True,
        )
        
        result = await session_service.create_session(verified_user, session_data)
        
        assert isinstance(result, SessionResponse)
        assert result.name == session_data.name
        assert result.session_type == session_data.session_type.value
        assert result.ssh_profile_id == str(test_ssh_profile.id)
        assert result.connection_info is not None
    
    async def test_create_session_with_connection_params(self, session_service, verified_user):
        """Test session creation with custom connection parameters."""
        session_data = SessionCreate(
            name="Custom Connection Session",
            session_type=SessionType.SSH,
            mode=SessionMode.INTERACTIVE,
            connection_params={
                "host": "custom.example.com",
                "port": 2222,
                "username": "customuser",
            }
        )
        
        result = await session_service.create_session(verified_user, session_data)
        
        assert isinstance(result, SessionResponse)
        assert result.connection_info is not None
        assert result.connection_info["host"] == "custom.example.com"
        assert result.connection_info["port"] == 2222
    
    async def test_create_session_duplicate_name_active(self, session_service, test_user_with_sessions):
        """Test session creation with duplicate name for active session."""
        user, sessions = test_user_with_sessions
        existing_active_session = next(s for s in sessions if s.is_active)
        
        session_data = SessionCreate(
            name=existing_active_session.name,  # Same name as active session
            session_type=SessionType.LOCAL,
            mode=SessionMode.INTERACTIVE,
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.create_session(user, session_data)
        
        assert exc_info.value.status_code == 400
        assert "already exists" in str(exc_info.value.detail)
    
    async def test_create_session_invalid_ssh_profile(self, session_service, verified_user):
        """Test session creation with invalid SSH profile ID."""
        fake_profile_id = str(uuid.uuid4())
        
        session_data = SessionCreate(
            name="Invalid SSH Session",
            session_type=SessionType.SSH,
            mode=SessionMode.INTERACTIVE,
            ssh_profile_id=fake_profile_id,
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.create_session(verified_user, session_data)
        
        assert exc_info.value.status_code == 404
        assert "SSH profile not found" in str(exc_info.value.detail)
    
    async def test_create_session_unauthorized_ssh_profile(self, session_service, verified_user, test_ssh_profile, premium_user):
        """Test session creation with SSH profile owned by different user."""
        session_data = SessionCreate(
            name="Unauthorized SSH Session",
            session_type=SessionType.SSH,
            mode=SessionMode.INTERACTIVE,
            ssh_profile_id=str(test_ssh_profile.id),
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.create_session(premium_user, session_data)
        
        assert exc_info.value.status_code == 404
        assert "SSH profile not found" in str(exc_info.value.detail)
    
    async def test_create_session_database_error(self, session_service, verified_user):
        """Test session creation with database error."""
        session_data = SessionCreate(
            name="Test Session",
            session_type=SessionType.LOCAL,
            mode=SessionMode.INTERACTIVE,
        )
        
        with patch.object(session_service.session_repo, 'create',
                         side_effect=Exception("Database error")):
            with pytest.raises(HTTPException) as exc_info:
                await session_service.create_session(verified_user, session_data)
            
            assert exc_info.value.status_code == 500
            assert "Failed to create terminal session" in str(exc_info.value.detail)
    
    async def test_create_session_integrity_error(self, session_service, verified_user):
        """Test session creation with integrity constraint violation."""
        session_data = SessionCreate(
            name="Test Session",
            session_type=SessionType.LOCAL,
            mode=SessionMode.INTERACTIVE,
        )
        
        with patch.object(session_service.session_repo, 'create',
                         side_effect=IntegrityError("", "", "")):
            with pytest.raises(HTTPException) as exc_info:
                await session_service.create_session(verified_user, session_data)
            
            assert exc_info.value.status_code == 400
            assert "Session with this name already exists" in str(exc_info.value.detail)
    
    async def test_get_user_sessions_success(self, session_service, test_user_with_sessions):
        """Test successful user sessions retrieval."""
        user, sessions = test_user_with_sessions
        
        results, total = await session_service.get_user_sessions(user)
        
        assert isinstance(results, list)
        assert isinstance(total, int)
        assert len(results) > 0
        assert total > 0
        assert all(isinstance(session, SessionResponse) for session in results)
        assert all(session.user_id == str(user.id) for session in results)
    
    async def test_get_user_sessions_active_only(self, session_service, test_user_with_sessions):
        """Test user sessions retrieval with active_only filter."""
        user, sessions = test_user_with_sessions
        
        results, total = await session_service.get_user_sessions(user, active_only=True)
        
        assert isinstance(results, list)
        # Should only return active sessions
        assert all(session.is_active for session in results)
    
    async def test_get_user_sessions_pagination(self, session_service, test_user_with_sessions):
        """Test user sessions retrieval with pagination."""
        user, sessions = test_user_with_sessions
        
        results, total = await session_service.get_user_sessions(user, offset=1, limit=2)
        
        assert isinstance(results, list)
        assert len(results) <= 2
        assert isinstance(total, int)
    
    async def test_get_user_sessions_database_error(self, session_service, verified_user):
        """Test user sessions retrieval with database error."""
        with patch.object(session_service.session_repo, 'get_user_sessions',
                         side_effect=Exception("Database error")):
            with pytest.raises(HTTPException) as exc_info:
                await session_service.get_user_sessions(verified_user)
            
            assert exc_info.value.status_code == 500
            assert "Failed to fetch terminal sessions" in str(exc_info.value.detail)
    
    async def test_get_session_success(self, session_service, test_user_with_sessions):
        """Test successful individual session retrieval."""
        user, sessions = test_user_with_sessions
        session_id = str(sessions[0].id)
        
        result = await session_service.get_session(user, session_id)
        
        assert isinstance(result, SessionResponse)
        assert result.id == session_id
        assert result.user_id == str(user.id)
    
    async def test_get_session_not_found(self, session_service, verified_user):
        """Test session retrieval for non-existent session."""
        fake_session_id = str(uuid.uuid4())
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.get_session(verified_user, fake_session_id)
        
        assert exc_info.value.status_code == 404
        assert "Terminal session not found" in str(exc_info.value.detail)
    
    async def test_get_session_unauthorized(self, session_service, test_user_with_sessions, premium_user):
        """Test session retrieval by unauthorized user."""
        user, sessions = test_user_with_sessions
        session_id = str(sessions[0].id)
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.get_session(premium_user, session_id)
        
        assert exc_info.value.status_code == 404
        assert "Terminal session not found" in str(exc_info.value.detail)
    
    async def test_update_session_success(self, session_service, test_user_with_sessions):
        """Test successful session update."""
        user, sessions = test_user_with_sessions
        session_id = str(sessions[0].id)
        
        update_data = SessionUpdate(
            description="Updated description",
            terminal_size={"cols": 100, "rows": 30},
            environment={"NEW_VAR": "value"},
        )
        
        result = await session_service.update_session(user, session_id, update_data)
        
        assert isinstance(result, SessionResponse)
        assert result.id == session_id
        assert result.description == update_data.description
    
    async def test_update_session_terminal_size(self, session_service, test_user_with_sessions):
        """Test session update with terminal size change."""
        user, sessions = test_user_with_sessions
        session_id = str(sessions[0].id)
        
        update_data = SessionUpdate(
            terminal_size={"cols": 120, "rows": 40}
        )
        
        result = await session_service.update_session(user, session_id, update_data)
        
        assert result.terminal_cols == 120
        assert result.terminal_rows == 40
    
    async def test_update_session_not_found(self, session_service, verified_user):
        """Test session update for non-existent session."""
        fake_session_id = str(uuid.uuid4())
        update_data = SessionUpdate(description="New description")
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.update_session(verified_user, fake_session_id, update_data)
        
        assert exc_info.value.status_code == 404
        assert "Terminal session not found" in str(exc_info.value.detail)
    
    async def test_update_session_unauthorized(self, session_service, test_user_with_sessions, premium_user):
        """Test session update by unauthorized user."""
        user, sessions = test_user_with_sessions
        session_id = str(sessions[0].id)
        update_data = SessionUpdate(description="Unauthorized update")
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.update_session(premium_user, session_id, update_data)
        
        assert exc_info.value.status_code == 404
        assert "Terminal session not found" in str(exc_info.value.detail)
    
    async def test_update_session_database_error(self, session_service, test_user_with_sessions):
        """Test session update with database error."""
        user, sessions = test_user_with_sessions
        session_id = str(sessions[0].id)
        update_data = SessionUpdate(description="New description")
        
        with patch.object(session_service.session_repo, 'update',
                         side_effect=Exception("Database error")):
            with pytest.raises(HTTPException) as exc_info:
                await session_service.update_session(user, session_id, update_data)
            
            assert exc_info.value.status_code == 500
            assert "Failed to update terminal session" in str(exc_info.value.detail)
    
    async def test_terminate_session_success(self, session_service, test_user_with_sessions):
        """Test successful session termination."""
        user, sessions = test_user_with_sessions
        active_session = next(s for s in sessions if s.status == "active")
        session_id = str(active_session.id)
        
        result = await session_service.terminate_session(user, session_id)
        
        assert result is True
    
    async def test_terminate_session_already_terminated(self, session_service, test_user_with_sessions):
        """Test termination of already terminated session."""
        user, sessions = test_user_with_sessions
        terminated_session = next(s for s in sessions if s.status == "terminated")
        session_id = str(terminated_session.id)
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.terminate_session(user, session_id)
        
        assert exc_info.value.status_code == 400
        assert "already terminated" in str(exc_info.value.detail)
    
    async def test_terminate_session_force(self, session_service, test_user_with_sessions):
        """Test forced termination of already terminated session."""
        user, sessions = test_user_with_sessions
        terminated_session = next(s for s in sessions if s.status == "terminated")
        session_id = str(terminated_session.id)
        
        result = await session_service.terminate_session(user, session_id, force=True)
        
        assert result is True
    
    async def test_terminate_session_not_found(self, session_service, verified_user):
        """Test termination of non-existent session."""
        fake_session_id = str(uuid.uuid4())
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.terminate_session(verified_user, fake_session_id)
        
        assert exc_info.value.status_code == 404
        assert "Terminal session not found" in str(exc_info.value.detail)
    
    async def test_terminate_session_database_error(self, session_service, test_user_with_sessions):
        """Test session termination with database error."""
        user, sessions = test_user_with_sessions
        session_id = str(sessions[0].id)
        
        with patch.object(session_service.session_repo, 'update',
                         side_effect=Exception("Database error")):
            with pytest.raises(HTTPException) as exc_info:
                await session_service.terminate_session(user, session_id)
            
            assert exc_info.value.status_code == 500
            assert "Failed to terminate terminal session" in str(exc_info.value.detail)
    
    async def test_delete_session_success(self, session_service, test_user_with_sessions):
        """Test successful session deletion."""
        user, sessions = test_user_with_sessions
        session_id = str(sessions[0].id)
        
        result = await session_service.delete_session(user, session_id)
        
        assert result is True
    
    async def test_delete_session_active_cleanup(self, session_service, test_user_with_sessions):
        """Test deletion of active session with proper cleanup."""
        user, sessions = test_user_with_sessions
        active_session = next(s for s in sessions if s.status == "active")
        session_id = str(active_session.id)
        
        result = await session_service.delete_session(user, session_id)
        
        assert result is True
    
    async def test_delete_session_not_found(self, session_service, verified_user):
        """Test deletion of non-existent session."""
        fake_session_id = str(uuid.uuid4())
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.delete_session(verified_user, fake_session_id)
        
        assert exc_info.value.status_code == 404
        assert "Terminal session not found" in str(exc_info.value.detail)
    
    async def test_delete_session_database_error(self, session_service, test_user_with_sessions):
        """Test session deletion with database error."""
        user, sessions = test_user_with_sessions
        session_id = str(sessions[0].id)
        
        with patch.object(session_service.session_repo, 'delete',
                         side_effect=Exception("Database error")):
            with pytest.raises(HTTPException) as exc_info:
                await session_service.delete_session(user, session_id)
            
            assert exc_info.value.status_code == 500
            assert "Failed to delete terminal session" in str(exc_info.value.detail)
    
    async def test_execute_command_success(self, session_service, test_user_with_sessions):
        """Test successful command execution in session."""
        user, sessions = test_user_with_sessions
        active_session = next(s for s in sessions if s.status == "active")
        session_id = str(active_session.id)
        
        command = SessionCommand(
            command="ls -la",
            working_directory="/home/user"
        )
        
        result = await session_service.execute_command(user, session_id, command)
        
        assert isinstance(result, SessionCommandResponse)
        assert result.command == command.command
        assert result.session_id == session_id
        assert result.status == "completed"
    
    async def test_execute_command_inactive_session(self, session_service, test_user_with_sessions):
        """Test command execution in inactive session."""
        user, sessions = test_user_with_sessions
        inactive_session = next(s for s in sessions if not s.is_active)
        session_id = str(inactive_session.id)
        
        command = SessionCommand(command="ls -la")
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.execute_command(user, session_id, command)
        
        assert exc_info.value.status_code == 400
        assert "Session is not active" in str(exc_info.value.detail)
    
    async def test_execute_command_not_found(self, session_service, verified_user):
        """Test command execution in non-existent session."""
        fake_session_id = str(uuid.uuid4())
        command = SessionCommand(command="ls -la")
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.execute_command(verified_user, fake_session_id, command)
        
        assert exc_info.value.status_code == 404
        assert "Terminal session not found" in str(exc_info.value.detail)
    
    async def test_execute_command_database_error(self, session_service, test_user_with_sessions):
        """Test command execution with database error."""
        user, sessions = test_user_with_sessions
        session_id = str(sessions[0].id)
        command = SessionCommand(command="ls -la")
        
        with patch.object(session_service.session_repo, 'get_by_id',
                         side_effect=Exception("Database error")):
            with pytest.raises(HTTPException) as exc_info:
                await session_service.execute_command(user, session_id, command)
            
            assert exc_info.value.status_code == 500
            assert "Failed to execute command" in str(exc_info.value.detail)
    
    async def test_get_session_history_success(self, session_service, test_user_with_sessions):
        """Test successful session history retrieval."""
        user, sessions = test_user_with_sessions
        session_id = str(sessions[0].id)
        
        # Mock session commands
        mock_commands = [
            MagicMock(
                id="cmd1",
                command="ls -la",
                executed_at=datetime.now(UTC),
                exit_code=0,
                duration_ms=100,
                working_directory="/home"
            ),
            MagicMock(
                id="cmd2", 
                command="cd /tmp",
                executed_at=datetime.now(UTC),
                exit_code=0,
                duration_ms=50,
                working_directory="/home"
            )
        ]
        
        with patch.object(session_service.session_repo, 'get_session_commands',
                         return_value=mock_commands), \
             patch.object(session_service.session_repo, 'count_session_commands',
                         return_value=2):
            
            result = await session_service.get_session_history(user, session_id)
        
        assert isinstance(result, SessionHistoryResponse)
        assert result.session_id == session_id
        assert len(result.entries) == 2
        assert result.total_entries == 2
    
    async def test_get_session_history_pagination(self, session_service, test_user_with_sessions):
        """Test session history with pagination."""
        user, sessions = test_user_with_sessions
        session_id = str(sessions[0].id)
        
        mock_commands = []
        with patch.object(session_service.session_repo, 'get_session_commands',
                         return_value=mock_commands), \
             patch.object(session_service.session_repo, 'count_session_commands',
                         return_value=0):
            
            result = await session_service.get_session_history(user, session_id, limit=5, offset=10)
        
        assert isinstance(result, SessionHistoryResponse)
        assert len(result.entries) == 0
    
    async def test_get_session_history_not_found(self, session_service, verified_user):
        """Test session history for non-existent session."""
        fake_session_id = str(uuid.uuid4())
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.get_session_history(verified_user, fake_session_id)
        
        assert exc_info.value.status_code == 404
        assert "Terminal session not found" in str(exc_info.value.detail)
    
    async def test_get_session_history_database_error(self, session_service, test_user_with_sessions):
        """Test session history with database error."""
        user, sessions = test_user_with_sessions
        session_id = str(sessions[0].id)
        
        with patch.object(session_service.session_repo, 'get_session_commands',
                         side_effect=Exception("Database error")):
            with pytest.raises(HTTPException) as exc_info:
                await session_service.get_session_history(user, session_id)
            
            assert exc_info.value.status_code == 500
            assert "Failed to fetch session history" in str(exc_info.value.detail)
    
    async def test_search_sessions_basic(self, session_service, test_user_with_sessions):
        """Test basic session search functionality."""
        user, sessions = test_user_with_sessions
        
        search_request = SessionSearchRequest(
            search_term="Terminal",
            limit=10
        )
        
        results, total = await session_service.search_sessions(user, search_request)
        
        assert isinstance(results, list)
        assert isinstance(total, int)
        assert all(isinstance(session, SessionResponse) for session in results)
    
    async def test_search_sessions_by_type(self, session_service, test_user_with_sessions):
        """Test session search by session type."""
        user, sessions = test_user_with_sessions
        
        search_request = SessionSearchRequest(
            session_type=SessionType.SSH,
            limit=10
        )
        
        results, total = await session_service.search_sessions(user, search_request)
        
        # All results should be SSH sessions
        for session in results:
            assert session.session_type == "ssh"
    
    async def test_search_sessions_by_status(self, session_service, test_user_with_sessions):
        """Test session search by status."""
        user, sessions = test_user_with_sessions
        
        search_request = SessionSearchRequest(
            status=SessionStatus.ACTIVE,
            limit=10
        )
        
        results, total = await session_service.search_sessions(user, search_request)
        
        # All results should be active sessions
        for session in results:
            assert session.is_active is True
    
    async def test_search_sessions_by_ssh_profile(self, session_service, test_user_with_sessions, test_ssh_profile):
        """Test session search by SSH profile."""
        user, sessions = test_user_with_sessions
        
        search_request = SessionSearchRequest(
            ssh_profile_id=str(test_ssh_profile.id),
            limit=10
        )
        
        results, total = await session_service.search_sessions(user, search_request)
        
        # All results should use the specified SSH profile
        for session in results:
            if session.ssh_profile_id:
                assert session.ssh_profile_id == str(test_ssh_profile.id)
    
    async def test_search_sessions_time_range(self, session_service, test_user_with_sessions):
        """Test session search with time range filters."""
        user, sessions = test_user_with_sessions
        
        now = datetime.now(UTC)
        day_ago = now - timedelta(days=1)
        
        search_request = SessionSearchRequest(
            created_after=day_ago,
            limit=10
        )
        
        results, total = await session_service.search_sessions(user, search_request)
        
        assert isinstance(results, list)
        assert isinstance(total, int)
    
    async def test_search_sessions_database_error(self, session_service, verified_user):
        """Test session search with database error."""
        search_request = SessionSearchRequest(search_term="test")
        
        with patch.object(session_service.session_repo, 'search_sessions',
                         side_effect=Exception("Database error")):
            with pytest.raises(HTTPException) as exc_info:
                await session_service.search_sessions(verified_user, search_request)
            
            assert exc_info.value.status_code == 500
            assert "Failed to search terminal sessions" in str(exc_info.value.detail)
    
    async def test_get_session_stats_success(self, session_service, test_user_with_sessions):
        """Test successful session statistics retrieval."""
        user, sessions = test_user_with_sessions
        
        # Mock the repository method
        mock_stats = {
            "total_sessions": 4,
            "active_sessions": 2,
            "by_type": {"terminal": 2, "ssh": 2},
            "by_status": {"active": 2, "terminated": 1, "failed": 1},
            "sessions": [MagicMock(
                duration_seconds=3600,
                command_count=10,
                created_at=datetime.now(UTC)
            ) for _ in range(4)],
            "most_used_profiles": []
        }
        
        with patch.object(session_service.session_repo, 'get_user_session_stats',
                         return_value=mock_stats):
            result = await session_service.get_session_stats(user)
        
        assert isinstance(result, SessionStats)
        assert result.total_sessions == 4
        assert result.active_sessions == 2
        assert isinstance(result.sessions_by_type, dict)
        assert isinstance(result.sessions_by_status, dict)
    
    async def test_get_session_stats_database_error(self, session_service, verified_user):
        """Test session stats with database error."""
        with patch.object(session_service.session_repo, 'get_user_session_stats',
                         side_effect=Exception("Database error")):
            with pytest.raises(HTTPException) as exc_info:
                await session_service.get_session_stats(verified_user)
            
            assert exc_info.value.status_code == 500
            assert "Failed to get session statistics" in str(exc_info.value.detail)
    
    async def test_check_session_health_success(self, session_service, test_user_with_sessions):
        """Test successful session health check."""
        user, sessions = test_user_with_sessions
        active_session = next(s for s in sessions if s.status == "active")
        session_id = str(active_session.id)
        
        result = await session_service.check_session_health(user, session_id)
        
        assert isinstance(result, SessionHealthCheck)
        assert result.session_id == session_id
        assert isinstance(result.is_healthy, bool)
        assert isinstance(result.status, SessionStatus)
        assert result.uptime_seconds >= 0
    
    async def test_check_session_health_not_found(self, session_service, verified_user):
        """Test session health check for non-existent session."""
        fake_session_id = str(uuid.uuid4())
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.check_session_health(verified_user, fake_session_id)
        
        assert exc_info.value.status_code == 404
        assert "Terminal session not found" in str(exc_info.value.detail)
    
    async def test_check_session_health_database_error(self, session_service, test_user_with_sessions):
        """Test session health check with database error."""
        user, sessions = test_user_with_sessions
        session_id = str(sessions[0].id)
        
        with patch.object(session_service.session_repo, 'get_by_id',
                         side_effect=Exception("Database error")):
            with pytest.raises(HTTPException) as exc_info:
                await session_service.check_session_health(user, session_id)
            
            assert exc_info.value.status_code == 500
            assert "Failed to check session health" in str(exc_info.value.detail)
    
    # Private method tests
    async def test_initialize_session(self, session_service, verified_user):
        """Test session initialization in memory."""
        session_obj = Session(
            id=str(uuid.uuid4()),
            user_id=verified_user.id,
            name="Test Session",
            session_type="terminal",
            status="pending",
            is_active=True,
            terminal_cols=80,
            terminal_rows=24,
            environment={"PATH": "/usr/bin"}
        )
        
        await session_service._initialize_session(session_obj)
        
        # Check that session is in memory
        assert str(session_obj.id) in session_service._active_sessions
        
        memory_session = session_service._active_sessions[str(session_obj.id)]
        assert memory_session["status"] == "connecting"
        assert memory_session["terminal_cols"] == 80
        assert memory_session["terminal_rows"] == 24
    
    async def test_start_session_process(self, session_service, test_session, verified_user):
        """Test session process startup."""
        session_obj = Session(
            id=str(uuid.uuid4()),
            user_id=verified_user.id,
            name="Test Session",
            session_type="terminal",
            status="pending",
            is_active=True,
        )
        test_session.add(session_obj)
        await test_session.flush()
        
        # Initialize session in memory first
        session_service._active_sessions[str(session_obj.id)] = {
            "status": "connecting",
            "created_at": datetime.now(UTC),
        }
        
        await session_service._start_session_process(session_obj)
        
        # Session should be active after startup
        assert session_obj.status == "active"
        assert str(session_obj.id) in session_service._active_sessions
    
    async def test_terminate_session_process(self, session_service):
        """Test session process termination."""
        session_id = str(uuid.uuid4())
        
        # Add session to active sessions
        session_service._active_sessions[session_id] = {
            "status": "active",
            "created_at": datetime.now(UTC),
        }
        
        await session_service._terminate_session_process(session_id)
        
        # Session should be removed from active sessions
        assert session_id not in session_service._active_sessions
    
    async def test_cleanup_session_data(self, session_service):
        """Test session data cleanup."""
        session_id = str(uuid.uuid4())
        
        # Add session to active sessions
        session_service._active_sessions[session_id] = {
            "status": "active",
            "created_at": datetime.now(UTC),
        }
        
        await session_service._cleanup_session_data(session_id)
        
        # Session should be removed from active sessions
        assert session_id not in session_service._active_sessions
    
    async def test_execute_session_command_mock(self, session_service):
        """Test session command execution (mocked)."""
        session_id = str(uuid.uuid4())
        command = SessionCommand(
            command="echo 'hello world'",
            working_directory="/tmp"
        )
        
        result = await session_service._execute_session_command(session_id, command)
        
        assert isinstance(result, SessionCommandResponse)
        assert result.command == command.command
        assert result.session_id == session_id
        assert result.status == "completed"
        assert result.exit_code == 0
        assert result.working_directory == "/tmp"
    
    async def test_update_session_activity(self, session_service):
        """Test session activity update."""
        session_id = str(uuid.uuid4())
        
        # Initialize session in memory
        session_service._active_sessions[session_id] = {
            "status": "active",
            "last_activity": datetime.now(UTC) - timedelta(minutes=10),
            "command_count": 5
        }
        
        await session_service._update_session_activity(session_id)
        
        # Activity should be updated
        memory_session = session_service._active_sessions[session_id]
        assert memory_session["command_count"] == 6
        # last_activity should be very recent
        time_diff = datetime.now(UTC) - memory_session["last_activity"]
        assert time_diff.total_seconds() < 10  # Within 10 seconds
    
    async def test_check_session_health_memory(self, session_service):
        """Test session health check against memory state."""
        session_id = str(uuid.uuid4())
        
        # Test healthy session
        session_service._active_sessions[session_id] = {
            "status": "active",
            "last_activity": datetime.now(UTC) - timedelta(minutes=5)
        }
        
        is_healthy = await session_service._check_session_health(session_id)
        assert is_healthy is True
        
        # Test unhealthy session (old activity)
        session_service._active_sessions[session_id]["last_activity"] = \
            datetime.now(UTC) - timedelta(hours=2)
        
        is_healthy = await session_service._check_session_health(session_id)
        assert is_healthy is False
        
        # Test non-existent session
        is_healthy = await session_service._check_session_health("nonexistent")
        assert is_healthy is False
    
    async def test_concurrent_session_operations(self, session_service, test_user_with_sessions):
        """Test concurrent session operations don't interfere."""
        user, sessions = test_user_with_sessions
        session_id = str(sessions[0].id)
        
        # Run multiple operations concurrently
        tasks = [
            session_service.get_session(user, session_id),
            session_service.get_session_stats(user),
            session_service.check_session_health(user, session_id),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All operations should succeed
        for result in results:
            assert not isinstance(result, Exception)
        
        # Verify result types
        assert isinstance(results[0], SessionResponse)
        assert isinstance(results[1], SessionStats)
        assert isinstance(results[2], SessionHealthCheck)