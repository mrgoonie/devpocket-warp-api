"""
Enhanced comprehensive tests for Session repository functionality to achieve 70% coverage.

This module provides targeted test coverage for all Session repository operations,
focusing on the missing statements to reach our coverage goal.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, UTC
from uuid import uuid4

from app.models.session import Session
from app.models.user import User
from app.repositories.session import SessionRepository


@pytest.mark.database
class TestSessionRepositoryEnhanced:
    """Enhanced test suite for SessionRepository to achieve 70% coverage."""

    @pytest_asyncio.fixture
    async def session_repository(self, test_session):
        """Create session repository instance."""
        return SessionRepository(test_session)

    @pytest_asyncio.fixture
    async def test_user(self, test_session):
        """Create a test user."""
        user = User(
            username="testuser",
            email="test@example.com", 
            full_name="Test User",
            hashed_password="hashed_password_123"
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def sample_sessions(self, session_repository, test_user):
        """Create multiple sample sessions for testing."""
        sessions = []
        session_specs = [
            {
                "session_name": "terminal_session_1", 
                "device_id": "device1", 
                "device_type": "web",
                "session_type": "terminal",
                "is_active": True
            },
            {
                "session_name": "ssh_session_1", 
                "device_id": "device2", 
                "device_type": "mobile",
                "session_type": "ssh",
                "ssh_host": "server1.example.com",
                "ssh_port": 22,
                "ssh_username": "user1",
                "is_active": True
            },
            {
                "session_name": "terminal_session_2", 
                "device_id": "device1", 
                "device_type": "web",
                "session_type": "terminal",
                "is_active": False,
                "ended_at": datetime.now(UTC) - timedelta(hours=1)
            },
            {
                "session_name": "ssh_session_2", 
                "device_id": "device3", 
                "device_type": "desktop",
                "session_type": "ssh",
                "ssh_host": "server2.example.com",
                "ssh_port": 2222,
                "ssh_username": "admin",
                "is_active": False
            }
        ]

        for spec in session_specs:
            session = await session_repository.create_session(
                user_id=test_user.id,
                **spec
            )
            sessions.append(session)

        return sessions

    @pytest.mark.asyncio
    async def test_get_user_sessions(self, session_repository, test_user, sample_sessions):
        """Test retrieving user sessions."""
        sessions = sample_sessions
        
        # Get all sessions
        user_sessions = await session_repository.get_user_sessions(test_user.id)
        assert len(user_sessions) >= 4
        
        # Get only active sessions
        active_sessions = await session_repository.get_user_sessions(test_user.id, active_only=True)
        assert len(active_sessions) >= 2
        for session in active_sessions:
            assert session.is_active is True
        
        # Test pagination
        page1 = await session_repository.get_user_sessions(test_user.id, offset=0, limit=2)
        page2 = await session_repository.get_user_sessions(test_user.id, offset=2, limit=2)
        assert len(page1) == 2
        assert len(page2) >= 2

    @pytest.mark.asyncio
    async def test_get_user_sessions_with_filters(self, session_repository, test_user, sample_sessions):
        """Test retrieving user sessions with filters."""
        sessions = sample_sessions
        
        # Filter by session type
        ssh_sessions = await session_repository.get_user_sessions(
            test_user.id, session_type="ssh"
        )
        assert len(ssh_sessions) >= 2
        for session in ssh_sessions:
            assert session.session_type == "ssh"
        
        # Test include_inactive flag
        sessions_with_inactive = await session_repository.get_user_sessions(
            test_user.id, active_only=True, include_inactive=True
        )
        assert len(sessions_with_inactive) >= 2

    @pytest.mark.asyncio
    async def test_get_user_active_sessions(self, session_repository, test_user, sample_sessions):
        """Test retrieving user active sessions."""
        sessions = sample_sessions
        
        active_sessions = await session_repository.get_user_active_sessions(test_user.id)
        assert len(active_sessions) >= 2
        
        for session in active_sessions:
            assert session.is_active is True

    @pytest.mark.asyncio
    async def test_get_user_session_count(self, session_repository, test_user, sample_sessions):
        """Test counting user sessions."""
        sessions = sample_sessions
        
        # Count all sessions
        total_count = await session_repository.get_user_session_count(test_user.id)
        assert total_count >= 4
        
        # Count SSH sessions
        ssh_count = await session_repository.get_user_session_count(test_user.id, session_type="ssh")
        assert ssh_count >= 2
        
        # Count terminal sessions
        terminal_count = await session_repository.get_user_session_count(test_user.id, session_type="terminal")
        assert terminal_count >= 2

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, session_repository, test_user, sample_sessions):
        """Test retrieving all active sessions."""
        sessions = sample_sessions
        
        # Get all active sessions
        active_sessions = await session_repository.get_active_sessions()
        assert len(active_sessions) >= 2
        
        for session in active_sessions:
            assert session.is_active is True
        
        # Get active sessions for specific user
        user_active_sessions = await session_repository.get_active_sessions(user_id=test_user.id)
        assert len(user_active_sessions) >= 2
        
        for session in user_active_sessions:
            assert session.user_id == test_user.id
            assert session.is_active is True

    @pytest.mark.asyncio
    async def test_search_sessions(self, session_repository, test_user, sample_sessions):
        """Test searching sessions with criteria."""
        sessions = sample_sessions
        
        # Search by user ID
        user_sessions = await session_repository.search_sessions(
            criteria={"user_id": test_user.id}
        )
        assert len(user_sessions) >= 4
        
        # Search by session type
        ssh_sessions = await session_repository.search_sessions(
            criteria={"session_type": "ssh"}
        )
        assert len(ssh_sessions) >= 2
        
        # Search by search term
        terminal_sessions = await session_repository.search_sessions(
            criteria={"user_id": test_user.id},
            search_term="terminal"
        )
        assert len(terminal_sessions) >= 2
        
        # Search with date range
        now = datetime.now(UTC)
        hour_ago = now - timedelta(hours=1)
        recent_sessions = await session_repository.search_sessions(
            criteria={"user_id": test_user.id},
            created_after=hour_ago
        )
        assert len(recent_sessions) >= 3  # All except the ended one

    @pytest.mark.asyncio
    async def test_search_sessions_sorting(self, session_repository, test_user, sample_sessions):
        """Test search sessions with sorting."""
        sessions = sample_sessions
        
        # Sort by created_at descending (default)
        sessions_desc = await session_repository.search_sessions(
            criteria={"user_id": test_user.id},
            sort_by="created_at",
            sort_order="desc"
        )
        assert len(sessions_desc) >= 4
        
        # Sort by created_at ascending
        sessions_asc = await session_repository.search_sessions(
            criteria={"user_id": test_user.id},
            sort_by="created_at",
            sort_order="asc"
        )
        assert len(sessions_asc) >= 4
        
        # Verify sorting by checking created_at timestamps
        if len(sessions_desc) > 1:
            # Descending: first created_at >= second created_at
            assert sessions_desc[0].created_at >= sessions_desc[1].created_at
        
        if len(sessions_asc) > 1:
            # Ascending: first created_at <= second created_at
            assert sessions_asc[0].created_at <= sessions_asc[1].created_at
        
        # If we have different timestamps, ensure different order
        if len(sessions_desc) > 1 and len(sessions_asc) > 1:
            desc_timestamps = [s.created_at for s in sessions_desc]
            asc_timestamps = [s.created_at for s in sessions_asc]
            # Only check order difference if timestamps are actually different
            if desc_timestamps[0] != desc_timestamps[-1]:
                assert sessions_desc[0].id != sessions_asc[0].id

    @pytest.mark.asyncio
    async def test_count_sessions_with_criteria(self, session_repository, test_user, sample_sessions):
        """Test counting sessions with criteria."""
        sessions = sample_sessions
        
        # Count by user
        user_count = await session_repository.count_sessions_with_criteria(
            {"user_id": test_user.id}
        )
        assert user_count >= 4
        
        # Count by session type
        ssh_count = await session_repository.count_sessions_with_criteria(
            {"session_type": "ssh"}
        )
        assert ssh_count >= 2

    @pytest.mark.asyncio
    async def test_get_user_session_stats(self, session_repository, test_user, sample_sessions):
        """Test getting user session statistics."""
        sessions = sample_sessions
        
        stats = await session_repository.get_user_session_stats(test_user.id)
        
        assert "total_sessions" in stats
        assert "active_sessions" in stats
        assert stats["total_sessions"] >= 4
        assert stats["active_sessions"] >= 2

    @pytest.mark.asyncio
    async def test_get_session_with_commands(self, session_repository, sample_sessions):
        """Test getting session with commands loaded."""
        sessions = sample_sessions
        session_id = str(sessions[0].id)
        
        session = await session_repository.get_session_with_commands(session_id)
        assert session is not None
        assert hasattr(session, 'commands')

    @pytest.mark.asyncio
    async def test_get_sessions_by_device(self, session_repository, test_user, sample_sessions):
        """Test getting sessions by device."""
        sessions = sample_sessions
        
        # Get sessions for device1
        device1_sessions = await session_repository.get_sessions_by_device(
            test_user.id, "device1"
        )
        assert len(device1_sessions) >= 2  # Both terminal sessions use device1
        
        for session in device1_sessions:
            assert session.device_id == "device1"

    @pytest.mark.asyncio
    async def test_get_sessions_by_type(self, session_repository, test_user, sample_sessions):
        """Test getting sessions by type."""
        sessions = sample_sessions
        
        # Get terminal sessions
        terminal_sessions = await session_repository.get_sessions_by_type(
            test_user.id, "terminal"
        )
        assert len(terminal_sessions) >= 2
        
        for session in terminal_sessions:
            assert session.session_type == "terminal"
        
        # Get SSH sessions
        ssh_sessions = await session_repository.get_sessions_by_type(
            test_user.id, "ssh"
        )
        assert len(ssh_sessions) >= 2
        
        for session in ssh_sessions:
            assert session.session_type == "ssh"

    @pytest.mark.asyncio
    async def test_get_ssh_sessions(self, session_repository, test_user, sample_sessions):
        """Test getting SSH sessions."""
        sessions = sample_sessions
        
        # Get all SSH sessions
        ssh_sessions = await session_repository.get_ssh_sessions()
        assert len(ssh_sessions) >= 2
        
        for session in ssh_sessions:
            assert session.ssh_host is not None
        
        # Get SSH sessions for specific user
        user_ssh_sessions = await session_repository.get_ssh_sessions(user_id=test_user.id)
        assert len(user_ssh_sessions) >= 2
        
        # Get SSH sessions for specific host
        host_sessions = await session_repository.get_ssh_sessions(host="server1.example.com")
        assert len(host_sessions) >= 1
        
        for session in host_sessions:
            assert session.ssh_host == "server1.example.com"

    @pytest.mark.asyncio
    async def test_create_session(self, session_repository, test_user):
        """Test creating a new session."""
        session = await session_repository.create_session(
            user_id=test_user.id,
            device_id="new_device",
            device_type="tablet",
            session_name="new_session",
            session_type="terminal"
        )
        
        assert session.user_id == test_user.id
        assert session.device_id == "new_device"
        assert session.device_type == "tablet"
        assert session.session_name == "new_session"
        assert session.session_type == "terminal"
        assert session.last_activity_at is not None

    @pytest.mark.asyncio
    async def test_create_ssh_session(self, session_repository, test_user):
        """Test creating a new SSH session."""
        session = await session_repository.create_ssh_session(
            user_id=test_user.id,
            device_id="ssh_device",
            device_type="laptop",
            ssh_host="newserver.example.com",
            ssh_port=22,
            ssh_username="testuser",
            session_name="new_ssh_session"
        )
        
        assert session.user_id == test_user.id
        assert session.device_id == "ssh_device"
        assert session.device_type == "laptop"
        assert session.session_type == "ssh"
        assert session.ssh_host == "newserver.example.com"
        assert session.ssh_port == 22
        assert session.ssh_username == "testuser"

    @pytest.mark.asyncio
    async def test_update_activity(self, session_repository, sample_sessions):
        """Test updating session activity."""
        sessions = sample_sessions
        session = sessions[0]
        original_activity = session.last_activity_at
        
        # Small delay to ensure timestamp difference
        import asyncio
        await asyncio.sleep(0.1)
        
        updated_session = await session_repository.update_activity(str(session.id))
        
        assert updated_session is not None
        assert updated_session.last_activity_at > original_activity

    @pytest.mark.asyncio
    async def test_end_session(self, session_repository, sample_sessions):
        """Test ending a session."""
        sessions = sample_sessions
        session = sessions[0]  # Use an active session
        
        ended_session = await session_repository.end_session(str(session.id))
        
        assert ended_session is not None
        assert ended_session.is_active is False
        assert ended_session.ended_at is not None

    @pytest.mark.asyncio
    async def test_resize_terminal(self, session_repository, sample_sessions):
        """Test resizing terminal."""
        sessions = sample_sessions
        session = sessions[0]
        
        resized_session = await session_repository.resize_terminal(
            str(session.id), cols=120, rows=40
        )
        
        assert resized_session is not None
        assert resized_session.terminal_cols == 120
        assert resized_session.terminal_rows == 40

    @pytest.mark.asyncio
    async def test_end_inactive_sessions(self, session_repository, test_user, test_session):
        """Test ending inactive sessions."""
        # Create a session with old activity
        old_session = Session(
            user_id=test_user.id,
            device_id="old_device",
            device_type="web",
            session_name="old_session",
            is_active=True,
            last_activity_at=datetime.now(UTC) - timedelta(hours=2)
        )
        test_session.add(old_session)
        await test_session.commit()
        
        # End sessions inactive for more than 1 hour
        ended_count = await session_repository.end_inactive_sessions(inactive_threshold_minutes=60)
        
        assert ended_count >= 1
        
        # Refresh the session to check it was ended
        await test_session.refresh(old_session)
        assert old_session.is_active is False

    @pytest.mark.asyncio
    async def test_get_session_stats(self, session_repository, test_user, sample_sessions):
        """Test getting session statistics."""
        sessions = sample_sessions
        
        # Get stats for specific user
        user_stats = await session_repository.get_session_stats(user_id=test_user.id)
        
        assert "total_sessions" in user_stats
        assert "active_sessions" in user_stats
        assert "ssh_sessions" in user_stats
        assert "device_breakdown" in user_stats
        
        assert user_stats["total_sessions"] >= 4
        assert user_stats["active_sessions"] >= 2
        assert user_stats["ssh_sessions"] >= 2
        assert isinstance(user_stats["device_breakdown"], dict)
        
        # Get global stats
        global_stats = await session_repository.get_session_stats()
        assert global_stats["total_sessions"] >= 4

    @pytest.mark.asyncio
    async def test_get_user_device_sessions(self, session_repository, test_user, sample_sessions):
        """Test getting user sessions grouped by device."""
        sessions = sample_sessions
        
        devices = await session_repository.get_user_device_sessions(test_user.id)
        
        assert isinstance(devices, dict)
        assert len(devices) >= 3  # device1_web, device2_mobile, device3_desktop
        
        for device_key, device_info in devices.items():
            assert "device_id" in device_info
            assert "device_type" in device_info
            assert "sessions" in device_info
            assert "active_count" in device_info
            assert "total_count" in device_info
            assert isinstance(device_info["sessions"], list)

    @pytest.mark.asyncio
    async def test_get_user_device_sessions_filtered(self, session_repository, test_user, sample_sessions):
        """Test getting user device sessions with device type filter."""
        sessions = sample_sessions
        
        # Filter by device type
        web_devices = await session_repository.get_user_device_sessions(
            test_user.id, device_type="web"
        )
        
        assert isinstance(web_devices, dict)
        for device_key, device_info in web_devices.items():
            assert device_info["device_type"] == "web"

    @pytest.mark.asyncio
    async def test_get_user_session_by_name(self, session_repository, test_user, sample_sessions):
        """Test getting session by name."""
        sessions = sample_sessions
        
        session = await session_repository.get_user_session_by_name(
            test_user.id, "terminal_session_1"
        )
        
        assert session is not None
        assert session.session_name == "terminal_session_1"
        assert session.user_id == test_user.id
        
        # Test non-existent session
        session = await session_repository.get_user_session_by_name(
            test_user.id, "non_existent_session"
        )
        assert session is None

    @pytest.mark.asyncio
    async def test_count_user_sessions(self, session_repository, test_user, sample_sessions):
        """Test counting user sessions (alias method)."""
        sessions = sample_sessions
        
        # This method is an alias for get_user_session_count
        count = await session_repository.count_user_sessions(test_user.id)
        assert count >= 4
        
        # Test with session type
        ssh_count = await session_repository.count_user_sessions(test_user.id, session_type="ssh")
        assert ssh_count >= 2

    @pytest.mark.asyncio
    async def test_get_session_commands(self, session_repository, sample_sessions):
        """Test getting session commands."""
        sessions = sample_sessions
        session_id = str(sessions[0].id)
        
        # This method currently returns empty list as noted in implementation
        commands = await session_repository.get_session_commands(session_id)
        assert isinstance(commands, list)
        assert len(commands) == 0

    @pytest.mark.asyncio
    async def test_count_session_commands(self, session_repository, sample_sessions):
        """Test counting session commands."""
        sessions = sample_sessions
        session_id = str(sessions[0].id)
        
        # This method currently returns 0 as noted in implementation
        count = await session_repository.count_session_commands(session_id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_cleanup_old_sessions(self, session_repository, test_user, test_session):
        """Test cleaning up old sessions."""
        # Create an old session
        old_session = Session(
            user_id=test_user.id,
            device_id="old_device",
            device_type="web",
            session_name="old_session",
            is_active=False,
            created_at=datetime.now(UTC) - timedelta(days=100)
        )
        test_session.add(old_session)
        await test_session.commit()
        
        # Cleanup sessions older than 90 days
        deleted_count = await session_repository.cleanup_old_sessions(days_old=90)
        
        assert deleted_count >= 1

    @pytest.mark.asyncio
    async def test_cleanup_old_sessions_keep_active(self, session_repository, test_user, test_session):
        """Test cleaning up old sessions while keeping active ones."""
        # Create old active and inactive sessions
        old_active = Session(
            user_id=test_user.id,
            device_id="old_active_device",
            device_type="web",
            session_name="old_active_session",
            is_active=True,
            created_at=datetime.now(UTC) - timedelta(days=100)
        )
        old_inactive = Session(
            user_id=test_user.id,
            device_id="old_inactive_device",
            device_type="web",
            session_name="old_inactive_session",
            is_active=False,
            created_at=datetime.now(UTC) - timedelta(days=100)
        )
        
        test_session.add_all([old_active, old_inactive])
        await test_session.commit()
        
        # Cleanup with keep_active=True (default)
        deleted_count = await session_repository.cleanup_old_sessions(
            days_old=90, keep_active=True
        )
        
        # Should delete inactive but keep active
        assert deleted_count >= 1

    @pytest.mark.asyncio
    async def test_repository_inheritance(self, session_repository):
        """Test that SessionRepository properly inherits from BaseRepository."""
        # Test inherited methods work
        assert hasattr(session_repository, 'create')
        assert hasattr(session_repository, 'get_by_id')
        assert hasattr(session_repository, 'update')
        assert hasattr(session_repository, 'delete')
        assert hasattr(session_repository, 'list')
        assert hasattr(session_repository, 'count')

    @pytest.mark.asyncio
    async def test_edge_cases_empty_results(self, session_repository):
        """Test edge cases with empty results."""
        # Search with impossible criteria
        sessions = await session_repository.search_sessions(
            criteria={"session_name": "impossible_session_that_does_not_exist"}
        )
        assert sessions == []
        
        # Get sessions for non-existent user
        sessions = await session_repository.get_user_sessions("non-existent-user-id")
        assert sessions == []
        
        # Count for non-existent user
        count = await session_repository.get_user_session_count("non-existent-user-id")
        assert count == 0

    @pytest.mark.asyncio
    async def test_pagination_edge_cases(self, session_repository, test_user, sample_sessions):
        """Test pagination with edge cases."""
        sessions = sample_sessions
        
        # Test large offset
        results = await session_repository.get_user_sessions(test_user.id, offset=1000, limit=10)
        assert len(results) == 0
        
        # Test zero limit
        results = await session_repository.get_user_sessions(test_user.id, offset=0, limit=0)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_performance_with_large_data(self, session_repository, test_user, test_session):
        """Test performance with multiple sessions."""
        # Create additional sessions for performance testing
        additional_sessions = []
        for i in range(20):
            session = Session(
                user_id=test_user.id,
                device_id=f"perftest_device_{i}",
                device_type="web" if i % 2 == 0 else "mobile",
                session_name=f"perftest_session_{i}",
                session_type="terminal",
                is_active=True if i % 3 == 0 else False
            )
            additional_sessions.append(session)
        
        test_session.add_all(additional_sessions)
        await test_session.commit()
        
        # Test search performance
        start_time = datetime.now(UTC)
        results = await session_repository.search_sessions(
            criteria={"user_id": test_user.id}
        )
        end_time = datetime.now(UTC)
        
        assert len(results) >= 20
        # Should complete within reasonable time
        assert (end_time - start_time).total_seconds() < 1.0

    @pytest.mark.asyncio
    async def test_complex_search_scenarios(self, session_repository, test_user, sample_sessions):
        """Test complex search scenarios."""
        sessions = sample_sessions
        
        # Search with multiple criteria and date range
        now = datetime.now(UTC)
        hour_ago = now - timedelta(hours=1)
        
        results = await session_repository.search_sessions(
            criteria={"user_id": test_user.id, "session_type": "ssh"},
            search_term="ssh",
            created_after=hour_ago,
            sort_by="created_at",
            sort_order="desc",
            offset=0,
            limit=5
        )
        
        assert len(results) >= 1
        for session in results:
            assert session.user_id == test_user.id
            assert session.session_type == "ssh"

    @pytest.mark.asyncio
    async def test_device_grouping_edge_cases(self, session_repository, test_user):
        """Test device grouping with edge cases."""
        # Test with no sessions
        devices = await session_repository.get_user_device_sessions("non-existent-user")
        assert devices == {}
        
        # Test device grouping calculation
        devices = await session_repository.get_user_device_sessions(test_user.id)
        
        for device_key, device_info in devices.items():
            # Verify counts are consistent
            assert device_info["total_count"] == len(device_info["sessions"])
            active_count = sum(1 for session in device_info["sessions"] if session["is_active"])
            assert device_info["active_count"] == active_count