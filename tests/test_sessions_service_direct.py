"""
Direct Sessions Service Tests - Avoiding import conflicts.

Simple, direct tests for Sessions service coverage without complex fixtures.
"""

import pytest
import asyncio
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.api.sessions.service import SessionService


class TestSessionServiceDirect:
    """Direct test suite for SessionService."""

    @pytest.mark.asyncio
    async def test_service_init_basic(self):
        """Test basic service initialization."""
        mock_session = AsyncMock()
        
        with patch('app.api.sessions.service.SessionRepository') as mock_repo_class, \
             patch('app.api.sessions.service.SSHProfileRepository') as mock_ssh_repo_class:
            
            service = SessionService(mock_session)
            
            assert service.session == mock_session
            assert service._active_sessions == {}
            assert isinstance(service._background_tasks, set)
            mock_repo_class.assert_called_once_with(mock_session)
            mock_ssh_repo_class.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_initialize_session_memory_setup(self):
        """Test session initialization in memory."""
        mock_session = AsyncMock()
        
        with patch('app.api.sessions.service.SessionRepository'), \
             patch('app.api.sessions.service.SSHProfileRepository'), \
             patch('asyncio.create_task') as mock_create_task:
            
            service = SessionService(mock_session)
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task
            
            # Mock session object
            session_obj = MagicMock()
            session_obj.id = "test-session-id"
            session_obj.created_at = datetime.now(UTC)
            session_obj.terminal_cols = 80
            session_obj.terminal_rows = 24
            session_obj.environment = {}
            
            await service._initialize_session(session_obj)
            
            assert str(session_obj.id) in service._active_sessions
            memory_session = service._active_sessions[str(session_obj.id)]
            assert memory_session["status"] == "connecting"
            assert memory_session["command_count"] == 0
            assert memory_session["terminal_cols"] == 80
            assert memory_session["terminal_rows"] == 24
            
            # Verify task creation
            mock_create_task.assert_called_once()
            mock_task.add_done_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_terminate_session_process_cleanup(self):
        """Test session process termination."""
        mock_session = AsyncMock()
        
        with patch('app.api.sessions.service.SessionRepository'), \
             patch('app.api.sessions.service.SSHProfileRepository'):
            
            service = SessionService(mock_session)
            session_id = "test-session-id"
            
            # Add session to active sessions
            service._active_sessions[session_id] = {
                "status": "active",
                "command_count": 5
            }
            
            await service._terminate_session_process(session_id)
            
            # Verify session was removed from active sessions
            assert session_id not in service._active_sessions

    @pytest.mark.asyncio
    async def test_cleanup_session_data(self):
        """Test session data cleanup."""
        mock_session = AsyncMock()
        
        with patch('app.api.sessions.service.SessionRepository'), \
             patch('app.api.sessions.service.SSHProfileRepository'):
            
            service = SessionService(mock_session)
            session_id = "test-session-id"
            
            # Add session to active sessions
            service._active_sessions[session_id] = {
                "status": "active",
                "data": "test-data"
            }
            
            await service._cleanup_session_data(session_id)
            
            # Verify session was cleaned up
            assert session_id not in service._active_sessions

    @pytest.mark.asyncio
    async def test_update_session_activity(self):
        """Test session activity update."""
        mock_session = AsyncMock()
        
        with patch('app.api.sessions.service.SessionRepository'), \
             patch('app.api.sessions.service.SSHProfileRepository'):
            
            service = SessionService(mock_session)
            session_id = "test-session-id"
            
            # Add session to active sessions
            service._active_sessions[session_id] = {
                "last_activity": datetime.now(UTC),
                "command_count": 5
            }
            
            await service._update_session_activity(session_id)
            
            # Verify activity was updated
            memory_session = service._active_sessions[session_id]
            assert memory_session["command_count"] == 6

    @pytest.mark.asyncio
    async def test_check_session_health_no_session(self):
        """Test health check for non-existent session."""
        mock_session = AsyncMock()
        
        with patch('app.api.sessions.service.SessionRepository'), \
             patch('app.api.sessions.service.SSHProfileRepository'):
            
            service = SessionService(mock_session)
            session_id = "non-existent-session"
            
            result = await service._check_session_health(session_id)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_check_session_health_active_session(self):
        """Test health check for active session."""
        mock_session = AsyncMock()
        
        with patch('app.api.sessions.service.SessionRepository'), \
             patch('app.api.sessions.service.SSHProfileRepository'):
            
            service = SessionService(mock_session)
            session_id = "test-session-id"
            
            # Add active session with recent activity
            service._active_sessions[session_id] = {
                "status": "active",
                "last_activity": datetime.now(UTC)
            }
            
            result = await service._check_session_health(session_id)
            
            assert result is True

    @pytest.mark.asyncio
    async def test_execute_session_command_basic(self):
        """Test basic session command execution."""
        mock_session = AsyncMock()
        
        with patch('app.api.sessions.service.SessionRepository'), \
             patch('app.api.sessions.service.SSHProfileRepository'):
            
            service = SessionService(mock_session)
            session_id = "test-session-id"
            
            # Mock command object
            command_obj = MagicMock()
            command_obj.command = "echo hello"
            command_obj.working_directory = "/tmp"
            
            result = await service._execute_session_command(session_id, command_obj)
            
            # Verify command response structure
            assert hasattr(result, 'command_id')
            assert result.command == "echo hello"
            assert result.status == "completed"
            assert result.exit_code == 0
            assert "successfully" in result.stdout
            assert result.stderr == ""
            assert result.session_id == session_id

    @pytest.mark.asyncio
    async def test_start_session_process_success(self):
        """Test successful session process start."""
        mock_session = AsyncMock()
        
        with patch('app.api.sessions.service.SessionRepository') as mock_repo_class, \
             patch('app.api.sessions.service.SSHProfileRepository'):
            
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.update.return_value = MagicMock()
            
            service = SessionService(mock_session)
            
            # Mock session object
            session_obj = MagicMock()
            session_obj.id = "test-session-id"
            session_obj.status = "pending"
            
            # Add session to memory first
            service._active_sessions[str(session_obj.id)] = {
                "status": "connecting"
            }
            
            await service._start_session_process(session_obj)
            
            # Verify status was updated
            assert session_obj.status == "active"
            mock_repo.update.assert_called_once_with(session_obj)
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_session_process_failure(self):
        """Test session process start failure."""
        mock_session = AsyncMock()
        
        with patch('app.api.sessions.service.SessionRepository') as mock_repo_class, \
             patch('app.api.sessions.service.SSHProfileRepository'):
            
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            # First call fails, second succeeds for error handling
            mock_repo.update.side_effect = [Exception("Connection failed"), MagicMock()]
            
            service = SessionService(mock_session)
            
            # Mock session object
            session_obj = MagicMock()
            session_obj.id = "test-session-id"
            session_obj.status = "connecting"
            
            await service._start_session_process(session_obj)
            
            # Verify error was handled
            assert session_obj.status == "failed"
            assert session_obj.error_message == "Connection failed"
            # Should be called twice - once that fails, once for error handling
            assert mock_repo.update.call_count == 2

    @pytest.mark.asyncio
    async def test_memory_session_operations(self):
        """Test various memory session operations."""
        mock_session = AsyncMock()
        
        with patch('app.api.sessions.service.SessionRepository'), \
             patch('app.api.sessions.service.SSHProfileRepository'):
            
            service = SessionService(mock_session)
            session_id = "test-session-id"
            
            # Test session doesn't exist initially
            assert session_id not in service._active_sessions
            
            # Add session
            service._active_sessions[session_id] = {
                "status": "connecting",
                "command_count": 0,
                "last_activity": datetime.now(UTC)
            }
            
            # Test session exists
            assert session_id in service._active_sessions
            
            # Update activity
            await service._update_session_activity(session_id)
            assert service._active_sessions[session_id]["command_count"] == 1
            
            # Terminate process
            await service._terminate_session_process(session_id)
            assert session_id not in service._active_sessions

    @pytest.mark.asyncio
    async def test_background_task_management(self):
        """Test background task management."""
        mock_session = AsyncMock()
        
        with patch('app.api.sessions.service.SessionRepository'), \
             patch('app.api.sessions.service.SSHProfileRepository'), \
             patch('asyncio.create_task') as mock_create_task:
            
            service = SessionService(mock_session)
            
            # Mock task
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task
            
            # Mock session
            session_obj = MagicMock()
            session_obj.id = "test-session-id"
            session_obj.created_at = datetime.now(UTC)
            session_obj.terminal_cols = 80
            session_obj.terminal_rows = 24
            session_obj.environment = {}
            
            # Initialize session (creates background task)
            await service._initialize_session(session_obj)
            
            # Verify task was added to background tasks set
            assert mock_task in service._background_tasks
            
            # Test task cleanup callback
            mock_task.add_done_callback.assert_called_once()
            callback = mock_task.add_done_callback.call_args[0][0]
            
            # Call the callback (simulates task completion)
            callback(mock_task)
            
            # Verify task was removed from set
            assert mock_task not in service._background_tasks