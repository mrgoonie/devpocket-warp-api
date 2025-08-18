#!/usr/bin/env python3
"""
Standalone Sessions Service Test for Coverage Analysis.

This script runs focused tests directly without pytest's conftest interference.
"""

import sys
import os
import asyncio
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from app.api.sessions.service import SessionService


class StandaloneSessionTests:
    """Standalone test runner for Sessions Service."""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []

    def assert_equals(self, actual, expected, message=""):
        if actual != expected:
            error_msg = f"AssertionError: {message}. Expected {expected}, got {actual}"
            self.errors.append(error_msg)
            raise AssertionError(error_msg)

    def assert_true(self, condition, message=""):
        if not condition:
            error_msg = f"AssertionError: {message}. Expected True, got {condition}"
            self.errors.append(error_msg)
            raise AssertionError(error_msg)

    def assert_in(self, item, container, message=""):
        if item not in container:
            error_msg = f"AssertionError: {message}. Expected {item} in {container}"
            self.errors.append(error_msg)
            raise AssertionError(error_msg)

    def assert_not_in(self, item, container, message=""):
        if item in container:
            error_msg = f"AssertionError: {message}. Expected {item} not in {container}"
            self.errors.append(error_msg)
            raise AssertionError(error_msg)

    async def run_test(self, test_method):
        """Run a single test method."""
        test_name = test_method.__name__
        try:
            await test_method()
            print(f"✓ {test_name}")
            self.tests_passed += 1
        except Exception as e:
            print(f"✗ {test_name}: {e}")
            self.tests_failed += 1

    # Test Methods

    async def test_service_initialization(self):
        """Test service initializes correctly."""
        mock_session = AsyncMock()
        
        with patch('app.api.sessions.service.SessionRepository') as mock_repo_class, \
             patch('app.api.sessions.service.SSHProfileRepository') as mock_ssh_repo_class:
            
            service = SessionService(mock_session)
            
            self.assert_equals(service.session, mock_session)
            self.assert_equals(service._active_sessions, {})
            self.assert_true(isinstance(service._background_tasks, set))
            mock_repo_class.assert_called_once_with(mock_session)
            mock_ssh_repo_class.assert_called_once_with(mock_session)

    async def test_initialize_session_memory(self):
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
            
            self.assert_in(str(session_obj.id), service._active_sessions)
            memory_session = service._active_sessions[str(session_obj.id)]
            self.assert_equals(memory_session["status"], "connecting")
            self.assert_equals(memory_session["command_count"], 0)
            self.assert_equals(memory_session["terminal_cols"], 80)
            self.assert_equals(memory_session["terminal_rows"], 24)

    async def test_terminate_session_process(self):
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
            
            self.assert_not_in(session_id, service._active_sessions)

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
            
            self.assert_not_in(session_id, service._active_sessions)

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
            
            memory_session = service._active_sessions[session_id]
            self.assert_equals(memory_session["command_count"], 6)

    async def test_check_session_health_missing(self):
        """Test health check for non-existent session."""
        mock_session = AsyncMock()
        
        with patch('app.api.sessions.service.SessionRepository'), \
             patch('app.api.sessions.service.SSHProfileRepository'):
            
            service = SessionService(mock_session)
            session_id = "non-existent-session"
            
            result = await service._check_session_health(session_id)
            
            self.assert_equals(result, False)

    async def test_check_session_health_active(self):
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
            
            self.assert_equals(result, True)

    async def test_execute_session_command(self):
        """Test session command execution."""
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
            self.assert_true(hasattr(result, 'command_id'))
            self.assert_equals(result.command, "echo hello")
            self.assert_equals(result.status, "completed")
            self.assert_equals(result.exit_code, 0)
            self.assert_true("successfully" in result.stdout)
            self.assert_equals(result.stderr, "")
            self.assert_equals(result.session_id, session_id)

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
            self.assert_equals(session_obj.status, "active")
            mock_repo.update.assert_called_once_with(session_obj)
            mock_session.commit.assert_called_once()

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
            self.assert_equals(session_obj.status, "failed")
            self.assert_equals(session_obj.error_message, "Connection failed")
            # Should be called twice - once that fails, once for error handling
            self.assert_equals(mock_repo.update.call_count, 2)

    async def test_memory_operations_workflow(self):
        """Test complete memory operations workflow."""
        mock_session = AsyncMock()
        
        with patch('app.api.sessions.service.SessionRepository'), \
             patch('app.api.sessions.service.SSHProfileRepository'):
            
            service = SessionService(mock_session)
            session_id = "test-session-id"
            
            # Test session doesn't exist initially
            self.assert_not_in(session_id, service._active_sessions)
            
            # Add session
            service._active_sessions[session_id] = {
                "status": "connecting",
                "command_count": 0,
                "last_activity": datetime.now(UTC)
            }
            
            # Test session exists
            self.assert_in(session_id, service._active_sessions)
            
            # Update activity
            await service._update_session_activity(session_id)
            self.assert_equals(service._active_sessions[session_id]["command_count"], 1)
            
            # Terminate process
            await service._terminate_session_process(session_id)
            self.assert_not_in(session_id, service._active_sessions)

    async def run_all_tests(self):
        """Run all test methods."""
        print("Running standalone Sessions Service tests...")
        print("=" * 50)
        
        test_methods = [
            self.test_service_initialization,
            self.test_initialize_session_memory,
            self.test_terminate_session_process,
            self.test_cleanup_session_data,
            self.test_update_session_activity,
            self.test_check_session_health_missing,
            self.test_check_session_health_active,
            self.test_execute_session_command,
            self.test_start_session_process_success,
            self.test_start_session_process_failure,
            self.test_memory_operations_workflow,
        ]
        
        for test_method in test_methods:
            await self.run_test(test_method)
        
        print("=" * 50)
        print(f"Tests completed: {self.tests_passed} passed, {self.tests_failed} failed")
        
        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(f"  - {error}")
        
        return self.tests_passed, self.tests_failed


async def main():
    """Main test runner."""
    test_runner = StandaloneSessionTests()
    passed, failed = await test_runner.run_all_tests()
    
    print(f"\nTest Results: {passed}/{passed + failed} tests passed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"❌ {failed} tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)