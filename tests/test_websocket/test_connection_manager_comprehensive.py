"""
Comprehensive tests for WebSocket ConnectionManager to improve coverage.

This test suite focuses on improving test coverage for the Connection and 
ConnectionManager classes by testing all methods and code paths with proper mocking.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import WebSocket

from app.websocket.manager import Connection, ConnectionManager
from app.websocket.protocols import (
    HeartbeatMessage,
    MessageType,
    TerminalMessage,
    create_error_message,
    create_status_message,
)
from app.websocket.terminal import TerminalSession


class TestConnection:
    """Test the Connection class."""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.fixture
    def connection(self, mock_websocket):
        """Create Connection instance."""
        return Connection(
            websocket=mock_websocket,
            connection_id="conn-123",
            user_id="user-456",
            device_id="device-789",
        )

    def test_connection_init(self, connection, mock_websocket):
        """Test Connection initialization."""
        assert connection.websocket == mock_websocket
        assert connection.connection_id == "conn-123"
        assert connection.user_id == "user-456"
        assert connection.device_id == "device-789"
        assert isinstance(connection.connected_at, datetime)
        assert isinstance(connection.last_ping, datetime)
        assert connection.terminal_sessions == {}

    @pytest.mark.asyncio
    async def test_send_message_success(self, connection, mock_websocket):
        """Test successful message sending."""
        message = TerminalMessage(
            type=MessageType.TERMINAL_OUTPUT,
            session_id="session-123",
            data={"output": "Hello World"}
        )

        result = await connection.send_message(message)

        assert result is True
        mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_failure(self, connection, mock_websocket):
        """Test message sending failure."""
        mock_websocket.send_text.side_effect = Exception("WebSocket error")
        
        message = TerminalMessage(
            type=MessageType.TERMINAL_OUTPUT,
            session_id="session-123",
            data={"output": "Hello World"}
        )

        result = await connection.send_message(message)

        assert result is False

    @pytest.mark.asyncio
    async def test_ping_success(self, connection, mock_websocket):
        """Test successful ping."""
        initial_ping_time = connection.last_ping
        
        result = await connection.ping()

        assert result is True
        assert connection.last_ping > initial_ping_time
        mock_websocket.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_ping_failure(self, connection, mock_websocket):
        """Test ping failure."""
        mock_websocket.send_json.side_effect = Exception("Ping failed")
        
        result = await connection.ping()

        assert result is False

    @pytest.mark.asyncio
    async def test_close_success(self, connection, mock_websocket):
        """Test successful connection close."""
        result = await connection.close()

        assert result is True
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_failure(self, connection, mock_websocket):
        """Test connection close failure."""
        mock_websocket.close.side_effect = Exception("Close failed")
        
        result = await connection.close()

        assert result is False

    def test_is_alive_recently_pinged(self, connection):
        """Test is_alive with recent ping."""
        connection.last_ping = datetime.now()
        
        result = connection.is_alive()

        assert result is True

    def test_is_alive_old_ping(self, connection):
        """Test is_alive with old ping."""
        connection.last_ping = datetime.now() - timedelta(minutes=5)
        
        result = connection.is_alive(timeout_seconds=60)

        assert result is False

    def test_add_terminal_session(self, connection):
        """Test adding terminal session."""
        mock_session = Mock(spec=TerminalSession)
        session_id = "session-123"
        
        connection.add_terminal_session(session_id, mock_session)

        assert connection.terminal_sessions[session_id] == mock_session

    def test_remove_terminal_session_exists(self, connection):
        """Test removing existing terminal session."""
        mock_session = Mock(spec=TerminalSession)
        session_id = "session-123"
        connection.terminal_sessions[session_id] = mock_session
        
        result = connection.remove_terminal_session(session_id)

        assert result == mock_session
        assert session_id not in connection.terminal_sessions

    def test_remove_terminal_session_not_exists(self, connection):
        """Test removing non-existent terminal session."""
        result = connection.remove_terminal_session("non-existent")

        assert result is None

    def test_get_terminal_session_exists(self, connection):
        """Test getting existing terminal session."""
        mock_session = Mock(spec=TerminalSession)
        session_id = "session-123"
        connection.terminal_sessions[session_id] = mock_session
        
        result = connection.get_terminal_session(session_id)

        assert result == mock_session

    def test_get_terminal_session_not_exists(self, connection):
        """Test getting non-existent terminal session."""
        result = connection.get_terminal_session("non-existent")

        assert result is None


class TestConnectionManager:
    """Test the ConnectionManager class."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        return AsyncMock()

    @pytest.fixture
    def connection_manager(self, mock_redis):
        """Create ConnectionManager instance."""
        return ConnectionManager(redis_client=mock_redis)

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.fixture
    def mock_connection(self, mock_websocket):
        """Create mock Connection."""
        return Connection(
            websocket=mock_websocket,
            connection_id="conn-123",
            user_id="user-456",
            device_id="device-789",
        )

    def test_connection_manager_init(self, connection_manager, mock_redis):
        """Test ConnectionManager initialization."""
        assert connection_manager.redis_client == mock_redis
        assert connection_manager.connections == {}
        assert connection_manager.user_connections == {}
        assert connection_manager._heartbeat_task is None

    @pytest.mark.asyncio
    async def test_connect_new_connection(self, connection_manager, mock_websocket):
        """Test connecting a new WebSocket."""
        user_id = "user-123"
        device_id = "device-456"
        
        connection_id = await connection_manager.connect(mock_websocket, user_id, device_id)

        assert connection_id is not None
        assert connection_id in connection_manager.connections
        assert user_id in connection_manager.user_connections
        assert connection_id in connection_manager.user_connections[user_id]
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_existing_user(self, connection_manager, mock_websocket):
        """Test connecting for existing user."""
        user_id = "user-123"
        device_id1 = "device-456"
        device_id2 = "device-789"
        
        # First connection
        connection_id1 = await connection_manager.connect(mock_websocket, user_id, device_id1)
        
        # Second connection for same user
        mock_websocket2 = AsyncMock(spec=WebSocket)
        connection_id2 = await connection_manager.connect(mock_websocket2, user_id, device_id2)

        assert len(connection_manager.user_connections[user_id]) == 2
        assert connection_id1 in connection_manager.user_connections[user_id]
        assert connection_id2 in connection_manager.user_connections[user_id]

    @pytest.mark.asyncio
    async def test_disconnect_existing_connection(self, connection_manager, mock_connection):
        """Test disconnecting existing connection."""
        connection_id = mock_connection.connection_id
        user_id = mock_connection.user_id
        
        # Add connection manually
        connection_manager.connections[connection_id] = mock_connection
        connection_manager.user_connections[user_id] = {connection_id}
        
        await connection_manager.disconnect(connection_id)

        assert connection_id not in connection_manager.connections
        assert user_id not in connection_manager.user_connections

    @pytest.mark.asyncio
    async def test_disconnect_non_existent_connection(self, connection_manager):
        """Test disconnecting non-existent connection."""
        # Should not raise exception
        await connection_manager.disconnect("non-existent")

    @pytest.mark.asyncio
    async def test_send_to_connection_exists(self, connection_manager, mock_connection):
        """Test sending message to existing connection."""
        connection_id = mock_connection.connection_id
        connection_manager.connections[connection_id] = mock_connection
        
        # Mock the send_message method
        mock_connection.send_message = AsyncMock(return_value=True)
        
        message = TerminalMessage(
            type=MessageType.TERMINAL_OUTPUT,
            session_id="session-123",
            data={"output": "test"}
        )
        
        result = await connection_manager.send_to_connection(connection_id, message)

        assert result is True
        mock_connection.send_message.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_connection_not_exists(self, connection_manager):
        """Test sending message to non-existent connection."""
        message = TerminalMessage(
            type=MessageType.TERMINAL_OUTPUT,
            session_id="session-123",
            data={"output": "test"}
        )
        
        result = await connection_manager.send_to_connection("non-existent", message)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_user_single_connection(self, connection_manager, mock_connection):
        """Test sending message to user with single connection."""
        user_id = mock_connection.user_id
        connection_id = mock_connection.connection_id
        
        connection_manager.connections[connection_id] = mock_connection
        connection_manager.user_connections[user_id] = {connection_id}
        
        mock_connection.send_message = AsyncMock(return_value=True)
        
        message = TerminalMessage(
            type=MessageType.TERMINAL_OUTPUT,
            session_id="session-123",
            data={"output": "test"}
        )
        
        result = await connection_manager.send_to_user(user_id, message)

        assert result == 1
        mock_connection.send_message.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_user_multiple_connections(self, connection_manager):
        """Test sending message to user with multiple connections."""
        user_id = "user-123"
        
        # Create two mock connections
        mock_conn1 = Mock()
        mock_conn1.send_message = AsyncMock(return_value=True)
        mock_conn2 = Mock()
        mock_conn2.send_message = AsyncMock(return_value=True)
        
        connection_manager.connections["conn1"] = mock_conn1
        connection_manager.connections["conn2"] = mock_conn2
        connection_manager.user_connections[user_id] = {"conn1", "conn2"}
        
        message = TerminalMessage(
            type=MessageType.TERMINAL_OUTPUT,
            session_id="session-123",
            data={"output": "test"}
        )
        
        result = await connection_manager.send_to_user(user_id, message)

        assert result == 2
        mock_conn1.send_message.assert_called_once_with(message)
        mock_conn2.send_message.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_user_no_connections(self, connection_manager):
        """Test sending message to user with no connections."""
        message = TerminalMessage(
            type=MessageType.TERMINAL_OUTPUT,
            session_id="session-123",
            data={"output": "test"}
        )
        
        result = await connection_manager.send_to_user("non-existent-user", message)

        assert result == 0

    @pytest.mark.asyncio
    async def test_broadcast_message(self, connection_manager):
        """Test broadcasting message to all connections."""
        # Create two mock connections
        mock_conn1 = Mock()
        mock_conn1.send_message = AsyncMock(return_value=True)
        mock_conn2 = Mock()
        mock_conn2.send_message = AsyncMock(return_value=True)
        
        connection_manager.connections["conn1"] = mock_conn1
        connection_manager.connections["conn2"] = mock_conn2
        
        message = TerminalMessage(
            type=MessageType.TERMINAL_OUTPUT,
            session_id="session-123",
            data={"output": "broadcast"}
        )
        
        result = await connection_manager.broadcast(message)

        assert result == 2
        mock_conn1.send_message.assert_called_once_with(message)
        mock_conn2.send_message.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_with_exclusions(self, connection_manager):
        """Test broadcasting message with exclusions."""
        # Create three mock connections
        mock_conn1 = Mock()
        mock_conn1.send_message = AsyncMock(return_value=True)
        mock_conn2 = Mock()
        mock_conn2.send_message = AsyncMock(return_value=True)
        mock_conn3 = Mock()
        mock_conn3.send_message = AsyncMock(return_value=True)
        
        connection_manager.connections["conn1"] = mock_conn1
        connection_manager.connections["conn2"] = mock_conn2
        connection_manager.connections["conn3"] = mock_conn3
        
        message = TerminalMessage(
            type=MessageType.TERMINAL_OUTPUT,
            session_id="session-123",
            data={"output": "broadcast"}
        )
        
        result = await connection_manager.broadcast(message, exclude_connections={"conn2"})

        assert result == 2
        mock_conn1.send_message.assert_called_once_with(message)
        mock_conn3.send_message.assert_called_once_with(message)
        mock_conn2.send_message.assert_not_called()

    def test_get_connection_exists(self, connection_manager, mock_connection):
        """Test getting existing connection."""
        connection_id = mock_connection.connection_id
        connection_manager.connections[connection_id] = mock_connection
        
        result = connection_manager.get_connection(connection_id)

        assert result == mock_connection

    def test_get_connection_not_exists(self, connection_manager):
        """Test getting non-existent connection."""
        result = connection_manager.get_connection("non-existent")

        assert result is None

    def test_get_user_connections_exists(self, connection_manager, mock_connection):
        """Test getting connections for existing user."""
        user_id = mock_connection.user_id
        connection_id = mock_connection.connection_id
        
        connection_manager.connections[connection_id] = mock_connection
        connection_manager.user_connections[user_id] = {connection_id}
        
        result = connection_manager.get_user_connections(user_id)

        assert result == [mock_connection]

    def test_get_user_connections_not_exists(self, connection_manager):
        """Test getting connections for non-existent user."""
        result = connection_manager.get_user_connections("non-existent")

        assert result == []

    def test_get_connection_count(self, connection_manager, mock_connection):
        """Test getting total connection count."""
        connection_manager.connections["conn1"] = mock_connection
        connection_manager.connections["conn2"] = Mock()
        
        result = connection_manager.get_connection_count()

        assert result == 2

    def test_get_user_connection_count_exists(self, connection_manager):
        """Test getting connection count for existing user."""
        user_id = "user-123"
        connection_manager.user_connections[user_id] = {"conn1", "conn2", "conn3"}
        
        result = connection_manager.get_user_connection_count(user_id)

        assert result == 3

    def test_get_user_connection_count_not_exists(self, connection_manager):
        """Test getting connection count for non-existent user."""
        result = connection_manager.get_user_connection_count("non-existent")

        assert result == 0

    def test_get_all_users(self, connection_manager):
        """Test getting all connected users."""
        connection_manager.user_connections["user1"] = {"conn1"}
        connection_manager.user_connections["user2"] = {"conn2", "conn3"}
        
        result = connection_manager.get_all_users()

        assert result == {"user1", "user2"}

    @pytest.mark.asyncio
    async def test_cleanup_stale_connections_with_stale(self, connection_manager):
        """Test cleanup of stale connections."""
        # Create stale connection
        mock_stale_conn = Mock()
        mock_stale_conn.is_alive.return_value = False
        mock_stale_conn.connection_id = "stale-conn"
        mock_stale_conn.user_id = "user-123"
        mock_stale_conn.close = AsyncMock()
        
        # Create active connection
        mock_active_conn = Mock()
        mock_active_conn.is_alive.return_value = True
        mock_active_conn.connection_id = "active-conn"
        mock_active_conn.user_id = "user-456"
        
        connection_manager.connections["stale-conn"] = mock_stale_conn
        connection_manager.connections["active-conn"] = mock_active_conn
        connection_manager.user_connections["user-123"] = {"stale-conn"}
        connection_manager.user_connections["user-456"] = {"active-conn"}
        
        removed_count = await connection_manager.cleanup_stale_connections()

        assert removed_count == 1
        assert "stale-conn" not in connection_manager.connections
        assert "active-conn" in connection_manager.connections
        assert "user-123" not in connection_manager.user_connections
        assert "user-456" in connection_manager.user_connections

    @pytest.mark.asyncio
    async def test_cleanup_stale_connections_no_stale(self, connection_manager):
        """Test cleanup when no stale connections exist."""
        mock_active_conn = Mock()
        mock_active_conn.is_alive.return_value = True
        
        connection_manager.connections["active-conn"] = mock_active_conn
        
        removed_count = await connection_manager.cleanup_stale_connections()

        assert removed_count == 0
        assert "active-conn" in connection_manager.connections

    @pytest.mark.asyncio
    async def test_start_heartbeat(self, connection_manager):
        """Test starting heartbeat task."""
        connection_manager.start_heartbeat(interval=1)
        
        assert connection_manager._heartbeat_task is not None
        assert not connection_manager._heartbeat_task.done()
        
        # Clean up
        connection_manager._heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await connection_manager._heartbeat_task

    @pytest.mark.asyncio
    async def test_stop_heartbeat(self, connection_manager):
        """Test stopping heartbeat task."""
        # Start heartbeat first
        connection_manager.start_heartbeat(interval=1)
        assert connection_manager._heartbeat_task is not None
        
        # Stop heartbeat
        await connection_manager.stop_heartbeat()
        
        assert connection_manager._heartbeat_task.cancelled()

    @pytest.mark.asyncio
    async def test_stop_heartbeat_no_task(self, connection_manager):
        """Test stopping heartbeat when no task exists."""
        # Should not raise exception
        await connection_manager.stop_heartbeat()

    def test_get_connection_stats(self, connection_manager):
        """Test getting connection statistics."""
        # Add some connections
        connection_manager.user_connections["user1"] = {"conn1"}
        connection_manager.user_connections["user2"] = {"conn2", "conn3"}
        connection_manager.connections["conn1"] = Mock()
        connection_manager.connections["conn2"] = Mock()
        connection_manager.connections["conn3"] = Mock()
        
        stats = connection_manager.get_connection_stats()

        assert stats["total_connections"] == 3
        assert stats["total_users"] == 2
        assert stats["average_connections_per_user"] == 1.5

    def test_get_connection_stats_no_connections(self, connection_manager):
        """Test getting connection statistics with no connections."""
        stats = connection_manager.get_connection_stats()

        assert stats["total_connections"] == 0
        assert stats["total_users"] == 0
        assert stats["average_connections_per_user"] == 0