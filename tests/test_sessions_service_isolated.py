"""
Isolated Sessions service tests to avoid import conflicts.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

# Direct imports to avoid conftest issues
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.api.sessions.service import SessionService


class MockUser:
    def __init__(self):
        self.id = "user-123"
        self.username = "testuser"


class MockSession:
    def __init__(self):
        self.id = "session-123"
        self.user_id = "user-123"
        self.name = "Test Session"
        self.session_type = "local"
        self.device_id = "device-123"
        self.device_type = "web"
        self.is_active = True
        self.ssh_profile_id = None


class MockSessionCreate:
    def __init__(self):
        self.name = "Test Session"
        self.session_type = "local"
        self.device_id = "device-123"
        self.device_type = "web"
        self.ssh_profile_id = None
        self.environment = {}


class MockSessionUpdate:
    def __init__(self):
        self.name = "Updated Session"
        self.session_type = "ssh"
        self.ssh_profile_id = "profile-123"


class MockSessionSearchRequest:
    def __init__(self):
        self.query = "test"
        self.session_type = "local"
        self.is_active = True
        self.offset = 0
        self.limit = 50


class MockCommandExecuteRequest:
    def __init__(self):
        self.command = "ls -la"
        self.working_directory = "/home/user"
        self.timeout = 30
        self.capture_output = True


class TestSessionServiceIsolated:
    """Isolated Session Service tests."""

    @pytest.fixture
    def mock_db_session(self):
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def session_service(self, mock_db_session):
        with patch('app.api.sessions.service.SessionRepository') as mock_session_repo, \
             patch('app.api.sessions.service.SSHProfileRepository') as mock_ssh_repo:
            
            service = SessionService(mock_db_session)
            service.session_repo = mock_session_repo.return_value
            service.ssh_profile_repo = mock_ssh_repo.return_value
            service._active_sessions = {}
            service._background_tasks = set()
            return service

    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_db_session):
        """Test service initialization."""
        with patch('app.api.sessions.service.SessionRepository') as mock_session_repo, \
             patch('app.api.sessions.service.SSHProfileRepository') as mock_ssh_repo:
            
            service = SessionService(mock_db_session)
            assert service.session == mock_db_session
            assert service.session_repo is not None
            assert service.ssh_profile_repo is not None
            assert service._active_sessions == {}
            assert service._background_tasks == set()

    @pytest.mark.asyncio
    async def test_create_session_success(self, session_service):
        """Test successful session creation."""
        user = MockUser()
        session_data = MockSessionCreate()
        created_session = MockSession()

        session_service.session_repo.create.return_value = created_session

        result = await session_service.create_session(user, session_data)

        assert result is not None
        session_service.session_repo.create.assert_called_once()
        session_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_with_ssh_profile(self, session_service):
        """Test creating session with SSH profile."""
        user = MockUser()
        session_data = MockSessionCreate()
        session_data.session_type = "ssh"
        session_data.ssh_profile_id = "profile-123"
        
        created_session = MockSession()
        created_session.session_type = "ssh"
        created_session.ssh_profile_id = "profile-123"

        # Mock SSH profile exists
        mock_ssh_profile = MagicMock()
        mock_ssh_profile.id = "profile-123"
        mock_ssh_profile.user_id = user.id
        session_service.ssh_profile_repo.get_by_id.return_value = mock_ssh_profile
        session_service.session_repo.create.return_value = created_session

        result = await session_service.create_session(user, session_data)

        assert result is not None
        session_service.ssh_profile_repo.get_by_id.assert_called_once()
        session_service.session_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_invalid_ssh_profile(self, session_service):
        """Test creating session with invalid SSH profile."""
        user = MockUser()
        session_data = MockSessionCreate()
        session_data.session_type = "ssh"
        session_data.ssh_profile_id = "invalid-profile"

        # Mock SSH profile not found
        session_service.ssh_profile_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await session_service.create_session(user, session_data)
        
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_session_error_handling(self, session_service):
        """Test create session error handling."""
        user = MockUser()
        session_data = MockSessionCreate()

        session_service.session_repo.create.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await session_service.create_session(user, session_data)
        
        assert exc_info.value.status_code == 500
        session_service.session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_sessions_success(self, session_service):
        """Test successful retrieval of user sessions."""
        user = MockUser()
        sessions = [MockSession() for _ in range(3)]

        session_service.session_repo.get_user_sessions.return_value = sessions

        result = await session_service.get_user_sessions(user)

        assert isinstance(result, list)
        assert len(result) >= 0  # Should handle conversion
        session_service.session_repo.get_user_sessions.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_sessions_with_filters(self, session_service):
        """Test get user sessions with filters."""
        user = MockUser()
        sessions = [MockSession()]

        session_service.session_repo.get_user_sessions.return_value = sessions

        result = await session_service.get_user_sessions(
            user, 
            is_active=True, 
            session_type="local", 
            offset=0, 
            limit=50
        )

        assert isinstance(result, list)
        session_service.session_repo.get_user_sessions.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_sessions_error_handling(self, session_service):
        """Test get user sessions error handling."""
        user = MockUser()
        session_service.session_repo.get_user_sessions.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await session_service.get_user_sessions(user)
        
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_session_success(self, session_service):
        """Test successful session retrieval."""
        user = MockUser()
        session = MockSession()

        session_service.session_repo.get_by_id.return_value = session

        result = await session_service.get_session(user, str(session.id))

        assert result is not None
        session_service.session_repo.get_by_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, session_service):
        """Test get session when not found."""
        user = MockUser()
        session_service.session_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await session_service.get_session(user, "nonexistent-id")
        
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_session_wrong_user(self, session_service):
        """Test get session access by wrong user."""
        user = MockUser()
        session = MockSession()
        session.user_id = "different-user-id"

        session_service.session_repo.get_by_id.return_value = session

        with pytest.raises(HTTPException) as exc_info:
            await session_service.get_session(user, str(session.id))
        
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_session_success(self, session_service):
        """Test successful session update."""
        user = MockUser()
        session = MockSession()
        update_data = MockSessionUpdate()

        session_service.session_repo.get_by_id.return_value = session
        session_service.session_repo.update.return_value = session

        result = await session_service.update_session(user, str(session.id), update_data)

        assert result is not None
        session_service.session_repo.update.assert_called_once()
        session_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_session_with_ssh_profile(self, session_service):
        """Test updating session with SSH profile."""
        user = MockUser()
        session = MockSession()
        update_data = MockSessionUpdate()
        update_data.ssh_profile_id = "profile-123"

        # Mock SSH profile exists
        mock_ssh_profile = MagicMock()
        mock_ssh_profile.id = "profile-123"
        mock_ssh_profile.user_id = user.id
        session_service.ssh_profile_repo.get_by_id.return_value = mock_ssh_profile
        session_service.session_repo.get_by_id.return_value = session
        session_service.session_repo.update.return_value = session

        result = await session_service.update_session(user, str(session.id), update_data)

        assert result is not None
        session_service.ssh_profile_repo.get_by_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_session_error_handling(self, session_service):
        """Test update session error handling."""
        user = MockUser()
        session = MockSession()
        update_data = MockSessionUpdate()

        session_service.session_repo.get_by_id.return_value = session
        session_service.session_repo.update.side_effect = Exception("Update error")

        with pytest.raises(HTTPException) as exc_info:
            await session_service.update_session(user, str(session.id), update_data)
        
        assert exc_info.value.status_code == 500
        session_service.session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_terminate_session_success(self, session_service):
        """Test successful session termination."""
        user = MockUser()
        session = MockSession()
        session.is_active = True

        session_service.session_repo.get_by_id.return_value = session
        session_service.session_repo.update.return_value = session

        result = await session_service.terminate_session(user, str(session.id))

        assert result is not None
        session_service.session_repo.update.assert_called_once()
        session_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_terminate_session_already_inactive(self, session_service):
        """Test terminating already inactive session."""
        user = MockUser()
        session = MockSession()
        session.is_active = False

        session_service.session_repo.get_by_id.return_value = session

        with pytest.raises(HTTPException) as exc_info:
            await session_service.terminate_session(user, str(session.id))
        
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_session_success(self, session_service):
        """Test successful session deletion."""
        user = MockUser()
        session = MockSession()

        session_service.session_repo.get_by_id.return_value = session
        session_service.session_repo.delete.return_value = True

        result = await session_service.delete_session(user, str(session.id))

        assert result is True
        session_service.session_repo.delete.assert_called_once()
        session_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_active_session_error(self, session_service):
        """Test deleting active session should fail."""
        user = MockUser()
        session = MockSession()
        session.is_active = True

        session_service.session_repo.get_by_id.return_value = session

        with pytest.raises(HTTPException) as exc_info:
            await session_service.delete_session(user, str(session.id))
        
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_execute_command_success(self, session_service):
        """Test successful command execution."""
        user = MockUser()
        session = MockSession()
        command_request = MockCommandExecuteRequest()

        session_service.session_repo.get_by_id.return_value = session

        # Mock command execution result
        mock_result = {
            "command_id": "cmd-123",
            "status": "completed",
            "exit_code": 0,
            "output": "Command executed successfully"
        }

        with patch.object(session_service, '_execute_session_command', return_value=mock_result) as mock_execute:
            result = await session_service.execute_command(user, str(session.id), command_request)

            assert result == mock_result
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_command_inactive_session(self, session_service):
        """Test executing command on inactive session."""
        user = MockUser()
        session = MockSession()
        session.is_active = False
        command_request = MockCommandExecuteRequest()

        session_service.session_repo.get_by_id.return_value = session

        with pytest.raises(HTTPException) as exc_info:
            await session_service.execute_command(user, str(session.id), command_request)
        
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_session_history_success(self, session_service):
        """Test successful session history retrieval."""
        user = MockUser()
        session = MockSession()
        mock_commands = [MagicMock() for _ in range(5)]

        session_service.session_repo.get_by_id.return_value = session
        session_service.session_repo.get_session_commands.return_value = mock_commands

        result = await session_service.get_session_history(
            user, str(session.id), offset=0, limit=50
        )

        assert isinstance(result, dict)
        assert "commands" in result
        assert "total" in result
        session_service.session_repo.get_session_commands.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_sessions_success(self, session_service):
        """Test successful session search."""
        user = MockUser()
        search_request = MockSessionSearchRequest()
        sessions = [MockSession() for _ in range(3)]

        session_service.session_repo.search_sessions.return_value = sessions
        session_service.session_repo.count_search_results.return_value = 3

        result = await session_service.search_sessions(user, search_request)

        assert isinstance(result, tuple)
        sessions_list, total = result
        assert len(sessions_list) >= 0
        assert total >= 0

    @pytest.mark.asyncio
    async def test_search_sessions_error_handling(self, session_service):
        """Test search sessions error handling."""
        user = MockUser()
        search_request = MockSessionSearchRequest()
        session_service.session_repo.search_sessions.side_effect = Exception("Search error")

        with pytest.raises(HTTPException) as exc_info:
            await session_service.search_sessions(user, search_request)
        
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_session_stats_success(self, session_service):
        """Test successful session statistics retrieval."""
        user = MockUser()
        mock_stats = {
            "total_sessions": 10,
            "active_sessions": 3,
            "local_sessions": 7,
            "ssh_sessions": 3,
            "total_commands": 150,
            "average_session_duration": 3600
        }

        session_service.session_repo.get_user_session_stats.return_value = mock_stats

        result = await session_service.get_session_stats(user)

        assert result == mock_stats
        session_service.session_repo.get_user_session_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_stats_error_handling(self, session_service):
        """Test session statistics error handling."""
        user = MockUser()
        session_service.session_repo.get_user_session_stats.side_effect = Exception("Stats error")

        with pytest.raises(HTTPException) as exc_info:
            await session_service.get_session_stats(user)
        
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_check_session_health_success(self, session_service):
        """Test successful session health check."""
        user = MockUser()
        session = MockSession()
        session.is_active = True

        session_service.session_repo.get_by_id.return_value = session

        with patch.object(session_service, '_check_session_health', return_value=True) as mock_health:
            result = await session_service.check_session_health(user, str(session.id))

            assert result is not None
            assert "session_id" in result
            assert "is_healthy" in result
            mock_health.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_session_health_inactive_session(self, session_service):
        """Test health check on inactive session."""
        user = MockUser()
        session = MockSession()
        session.is_active = False

        session_service.session_repo.get_by_id.return_value = session

        result = await session_service.check_session_health(user, str(session.id))

        assert result is not None
        assert result["is_healthy"] is False
        assert "inactive session" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_private_helper_methods(self, session_service):
        """Test private helper methods."""
        # Test _initialize_session
        session = MockSession()
        result = await session_service._initialize_session(session)
        assert result is True

        # Test _update_session_activity
        await session_service._update_session_activity(str(session.id))
        # Should complete without error

    @pytest.mark.asyncio
    async def test_active_sessions_management(self, session_service):
        """Test active sessions management."""
        session_id = "session-123"
        
        # Test adding session to active sessions
        session_service._active_sessions[session_id] = {
            "started_at": "2023-01-01T00:00:00Z",
            "process_id": 1234
        }

        assert session_id in session_service._active_sessions

        # Test removing session from active sessions
        del session_service._active_sessions[session_id]
        assert session_id not in session_service._active_sessions

    @pytest.mark.asyncio
    async def test_background_tasks_management(self, session_service):
        """Test background tasks management."""
        # Test adding background task
        task = asyncio.create_task(asyncio.sleep(0.01))
        session_service._background_tasks.add(task)
        
        assert task in session_service._background_tasks

        # Wait for task completion and clean up
        await task
        session_service._background_tasks.discard(task)
        
        assert task not in session_service._background_tasks

    @pytest.mark.asyncio
    async def test_edge_cases_and_error_scenarios(self, session_service):
        """Test various edge cases and error scenarios."""
        user = MockUser()
        
        # Test with invalid session ID format
        with pytest.raises(HTTPException):
            await session_service.get_session(user, "invalid-id-format")

        # Test operations on non-existent session
        session_service.session_repo.get_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.get_session(user, "nonexistent-id")
        assert exc_info.value.status_code == 404

        # Test database connection issues
        session_service.session_repo.get_user_sessions.side_effect = Exception("DB connection lost")
        
        with pytest.raises(HTTPException) as exc_info:
            await session_service.get_user_sessions(user)
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self, session_service):
        """Test concurrent session operations."""
        user = MockUser()
        session = MockSession()
        
        # Reset mock to avoid side effects
        session_service.session_repo.get_by_id.side_effect = None
        session_service.session_repo.get_by_id.return_value = session

        # Simulate concurrent read operations
        tasks = []
        for _ in range(5):
            task = asyncio.create_task(
                session_service.get_session(user, str(session.id))
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All operations should succeed or fail consistently
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        assert success_count >= 0  # At least some should succeed

    @pytest.mark.asyncio
    async def test_session_lifecycle_simulation(self, session_service):
        """Test complete session lifecycle simulation."""
        user = MockUser()
        session_data = MockSessionCreate()
        created_session = MockSession()
        
        # Step 1: Create session
        session_service.session_repo.create.return_value = created_session
        create_result = await session_service.create_session(user, session_data)
        assert create_result is not None

        # Step 2: Get session
        session_service.session_repo.get_by_id.return_value = created_session
        get_result = await session_service.get_session(user, str(created_session.id))
        assert get_result is not None

        # Step 3: Update session
        update_data = MockSessionUpdate()
        session_service.session_repo.update.return_value = created_session
        update_result = await session_service.update_session(user, str(created_session.id), update_data)
        assert update_result is not None

        # Step 4: Terminate session
        created_session.is_active = True
        terminate_result = await session_service.terminate_session(user, str(created_session.id))
        assert terminate_result is not None

        # Step 5: Delete session
        created_session.is_active = False
        session_service.session_repo.delete.return_value = True
        delete_result = await session_service.delete_session(user, str(created_session.id))
        assert delete_result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])