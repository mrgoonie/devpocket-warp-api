"""
Comprehensive tests for WebSocket ConnectionManager to achieve 60% coverage.

Tests all ConnectionManager functionality including:
- Connection lifecycle management (connect, disconnect, cleanup)
- Message routing and handling (ping/pong, connect, disconnect, terminal messages)
- User and session tracking
- Background task management
- Error handling and edge cases
- Terminal session management
- Resource cleanup and connection pooling
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock, call

from fastapi import WebSocket
import redis.asyncio as aioredis

from app.websocket.manager import Connection, ConnectionManager
from app.websocket.protocols import (
    TerminalMessage, 
    MessageType, 
    HeartbeatMessage,
    create_error_message,
    create_status_message,
    parse_message
)
from app.websocket.terminal import TerminalSession


@pytest.mark.asyncio
class TestConnection:
    """Test Connection class functionality."""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket for testing."""
        websocket = MagicMock(spec=WebSocket)
        websocket.send_json = AsyncMock()
        websocket.send_text = AsyncMock()
        return websocket

    @pytest.fixture
    def connection(self, mock_websocket):
        """Create Connection instance for testing."""
        return Connection(
            websocket=mock_websocket,
            connection_id="test-conn-123",
            user_id="user-456",
            device_id="device-789"
        )

    def test_connection_initialization(self, connection, mock_websocket):
        """Test Connection initialization."""
        assert connection.websocket == mock_websocket
        assert connection.connection_id == "test-conn-123"
        assert connection.user_id == "user-456"
        assert connection.device_id == "device-789"
        assert isinstance(connection.connected_at, datetime)
        assert isinstance(connection.last_ping, datetime)
        assert connection.terminal_sessions == {}

    async def test_send_message_success(self, connection):
        """Test successful message sending."""
        message = TerminalMessage(
            type=MessageType.OUTPUT,
            session_id="session-123",
            data="test output"
        )
        
        result = await connection.send_message(message)
        
        assert result is True
        connection.websocket.send_json.assert_called_once()

    async def test_send_message_failure(self, connection):
        """Test message sending failure."""
        connection.websocket.send_json.side_effect = Exception("WebSocket error")
        
        message = TerminalMessage(
            type=MessageType.OUTPUT,
            session_id="session-123",
            data="test output"
        )
        
        with patch('app.core.logging.logger.error') as mock_logger:
            result = await connection.send_message(message)
            
            assert result is False
            mock_logger.assert_called_once()

    async def test_send_text_success(self, connection):
        """Test successful text sending."""
        result = await connection.send_text("test text")
        
        assert result is True
        connection.websocket.send_text.assert_called_once_with("test text")

    async def test_send_text_failure(self, connection):
        """Test text sending failure."""
        connection.websocket.send_text.side_effect = Exception("WebSocket error")
        
        with patch('app.core.logging.logger.error') as mock_logger:
            result = await connection.send_text("test text")
            
            assert result is False
            mock_logger.assert_called_once()

    def test_add_terminal_session(self, connection):
        """Test adding terminal session."""
        mock_session = MagicMock(spec=TerminalSession)
        mock_session.session_id = "session-123"
        
        connection.add_terminal_session(mock_session)
        
        assert connection.terminal_sessions["session-123"] == mock_session

    def test_remove_terminal_session(self, connection):
        """Test removing terminal session."""
        mock_session = MagicMock(spec=TerminalSession)
        mock_session.session_id = "session-123"
        connection.terminal_sessions["session-123"] = mock_session
        
        removed_session = connection.remove_terminal_session("session-123")
        
        assert removed_session == mock_session
        assert "session-123" not in connection.terminal_sessions

    def test_remove_terminal_session_not_found(self, connection):
        """Test removing non-existent terminal session."""
        result = connection.remove_terminal_session("nonexistent")
        
        assert result is None

    def test_get_terminal_session(self, connection):
        """Test getting terminal session."""
        mock_session = MagicMock(spec=TerminalSession)
        connection.terminal_sessions["session-123"] = mock_session
        
        retrieved_session = connection.get_terminal_session("session-123")
        
        assert retrieved_session == mock_session

    def test_get_terminal_session_not_found(self, connection):
        """Test getting non-existent terminal session."""
        result = connection.get_terminal_session("nonexistent")
        
        assert result is None

    def test_update_ping(self, connection):
        """Test updating ping timestamp."""
        original_ping = connection.last_ping
        
        # Wait a small amount to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        connection.update_ping()
        
        assert connection.last_ping > original_ping


@pytest.mark.asyncio
class TestConnectionManager:
    """Test ConnectionManager class functionality."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis_client = MagicMock(spec=aioredis.Redis)
        return redis_client

    @pytest.fixture
    def connection_manager(self, mock_redis):
        """Create ConnectionManager instance for testing."""
        return ConnectionManager(redis_client=mock_redis)

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket for testing."""
        websocket = MagicMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.send_text = AsyncMock()
        return websocket

    def test_connection_manager_initialization(self, connection_manager, mock_redis):
        """Test ConnectionManager initialization."""
        assert connection_manager.connections == {}
        assert connection_manager.user_connections == {}
        assert connection_manager.session_connections == {}
        assert connection_manager.redis == mock_redis
        assert connection_manager._cleanup_task is None

    async def test_connect_new_connection(self, connection_manager, mock_websocket):
        """Test connecting new WebSocket connection."""
        with patch('uuid.uuid4', return_value=MagicMock(return_value="test-uuid")):
            with patch('app.core.logging.logger.info') as mock_logger:
                connection_id = await connection_manager.connect(
                    mock_websocket, "user-123", "device-456"
                )
                
                assert connection_id is not None
                assert connection_id in connection_manager.connections
                assert "user-123" in connection_manager.user_connections
                assert connection_id in connection_manager.user_connections["user-123"]
                
                mock_websocket.accept.assert_called_once()
                mock_logger.assert_called_once()

    async def test_connect_existing_user(self, connection_manager, mock_websocket):
        """Test connecting second connection for existing user."""
        # First connection
        conn_id_1 = await connection_manager.connect(mock_websocket, "user-123", "device-1")
        
        # Second connection for same user
        mock_websocket_2 = MagicMock(spec=WebSocket)
        mock_websocket_2.accept = AsyncMock()
        conn_id_2 = await connection_manager.connect(mock_websocket_2, "user-123", "device-2")
        
        assert len(connection_manager.user_connections["user-123"]) == 2
        assert conn_id_1 in connection_manager.user_connections["user-123"]
        assert conn_id_2 in connection_manager.user_connections["user-123"]

    async def test_connect_starts_background_tasks(self, connection_manager, mock_websocket):
        """Test that connect starts background tasks."""
        with patch.object(connection_manager, 'start_background_tasks') as mock_start:
            await connection_manager.connect(mock_websocket, "user-123", "device-456")
            
            mock_start.assert_called_once()

    async def test_disconnect_existing_connection(self, connection_manager, mock_websocket):
        """Test disconnecting existing connection."""
        # Connect first
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        
        # Add a terminal session
        mock_session = MagicMock(spec=TerminalSession)
        mock_session.session_id = "session-123"
        connection = connection_manager.connections[connection_id]
        connection.terminal_sessions["session-123"] = mock_session
        connection_manager.session_connections["session-123"] = connection_id
        
        with patch.object(connection_manager, '_cleanup_terminal_session') as mock_cleanup:
            with patch('app.core.logging.logger.info') as mock_logger:
                await connection_manager.disconnect(connection_id)
                
                assert connection_id not in connection_manager.connections
                assert "user-123" not in connection_manager.user_connections
                assert "session-123" not in connection_manager.session_connections
                
                mock_cleanup.assert_called_once_with(mock_session)
                mock_logger.assert_called_once()

    async def test_disconnect_nonexistent_connection(self, connection_manager):
        """Test disconnecting non-existent connection."""
        # Should not raise an exception
        await connection_manager.disconnect("nonexistent-connection")

    async def test_disconnect_user_with_multiple_connections(self, connection_manager, mock_websocket):
        """Test disconnecting one of multiple connections for a user."""
        # Connect two connections for same user
        conn_id_1 = await connection_manager.connect(mock_websocket, "user-123", "device-1")
        
        mock_websocket_2 = MagicMock(spec=WebSocket)
        mock_websocket_2.accept = AsyncMock()
        conn_id_2 = await connection_manager.connect(mock_websocket_2, "user-123", "device-2")
        
        # Disconnect first connection
        await connection_manager.disconnect(conn_id_1)
        
        # Second connection should still exist
        assert conn_id_2 in connection_manager.connections
        assert "user-123" in connection_manager.user_connections
        assert conn_id_2 in connection_manager.user_connections["user-123"]
        assert conn_id_1 not in connection_manager.user_connections["user-123"]

    async def test_disconnect_with_cleanup_error(self, connection_manager, mock_websocket):
        """Test disconnect handling cleanup errors."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        
        with patch.object(connection_manager, '_cleanup_terminal_session', side_effect=Exception("Cleanup error")):
            with patch('app.core.logging.logger.error') as mock_logger:
                await connection_manager.disconnect(connection_id)
                
                # Connection should still be cleaned up despite error
                assert connection_id not in connection_manager.connections
                mock_logger.assert_called_once()

    async def test_handle_message_unknown_connection(self, connection_manager):
        """Test handling message for unknown connection."""
        with patch('app.core.logging.logger.warning') as mock_logger:
            await connection_manager.handle_message("unknown-conn", {"type": "ping"})
            
            mock_logger.assert_called_once()

    async def test_handle_message_ping(self, connection_manager, mock_websocket):
        """Test handling ping message."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        
        ping_message = {"type": "ping"}
        
        with patch('app.websocket.protocols.parse_message') as mock_parse:
            mock_message = MagicMock()
            mock_message.type = MessageType.PING
            mock_parse.return_value = mock_message
            
            await connection_manager.handle_message(connection_id, ping_message)
            
            # Should send pong response
            mock_websocket.send_json.assert_called()

    async def test_handle_message_connect(self, connection_manager, mock_websocket):
        """Test handling connect message."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        
        connect_message = {
            "type": "connect",
            "data": {
                "session_type": "terminal",
                "terminal_size": {"cols": 80, "rows": 24}
            }
        }
        
        with patch('app.websocket.protocols.parse_message') as mock_parse:
            with patch.object(connection_manager, '_handle_connect_message') as mock_handle:
                mock_message = MagicMock()
                mock_message.type = MessageType.CONNECT
                mock_parse.return_value = mock_message
                
                await connection_manager.handle_message(connection_id, connect_message)
                
                mock_handle.assert_called_once()

    async def test_handle_message_disconnect(self, connection_manager, mock_websocket):
        """Test handling disconnect message."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        
        disconnect_message = {
            "type": "disconnect",
            "session_id": "session-123"
        }
        
        with patch('app.websocket.protocols.parse_message') as mock_parse:
            with patch.object(connection_manager, '_handle_disconnect_message') as mock_handle:
                mock_message = MagicMock()
                mock_message.type = MessageType.DISCONNECT
                mock_parse.return_value = mock_message
                
                await connection_manager.handle_message(connection_id, disconnect_message)
                
                mock_handle.assert_called_once()

    async def test_handle_message_terminal_messages(self, connection_manager, mock_websocket):
        """Test handling terminal input/resize/signal messages."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        
        terminal_types = [MessageType.INPUT, MessageType.RESIZE, MessageType.SIGNAL]
        
        for msg_type in terminal_types:
            with patch('app.websocket.protocols.parse_message') as mock_parse:
                with patch.object(connection_manager, '_handle_terminal_message') as mock_handle:
                    mock_message = MagicMock()
                    mock_message.type = msg_type
                    mock_parse.return_value = mock_message
                    
                    await connection_manager.handle_message(connection_id, {"type": msg_type.value})
                    
                    mock_handle.assert_called_once()

    async def test_handle_message_unknown_type(self, connection_manager, mock_websocket):
        """Test handling unknown message type."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        
        with patch('app.websocket.protocols.parse_message') as mock_parse:
            with patch('app.core.logging.logger.warning') as mock_logger:
                mock_message = MagicMock()
                mock_message.type = "unknown_type"
                mock_parse.return_value = mock_message
                
                await connection_manager.handle_message(connection_id, {"type": "unknown"})
                
                mock_logger.assert_called_once()

    async def test_handle_message_parse_error(self, connection_manager, mock_websocket):
        """Test handling message parse error."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        
        with patch('app.websocket.protocols.parse_message', side_effect=ValueError("Parse error")):
            with patch('app.core.logging.logger.warning') as mock_logger:
                await connection_manager.handle_message(connection_id, {"invalid": "message"})
                
                mock_logger.assert_called_once()
                mock_websocket.send_json.assert_called()  # Error message sent

    async def test_handle_message_unexpected_error(self, connection_manager, mock_websocket):
        """Test handling unexpected error in message processing."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        
        with patch('app.websocket.protocols.parse_message', side_effect=Exception("Unexpected error")):
            with patch('app.core.logging.logger.error') as mock_logger:
                await connection_manager.handle_message(connection_id, {"type": "ping"})
                
                mock_logger.assert_called_once()
                mock_websocket.send_json.assert_called()  # Error message sent

    async def test_handle_connect_message_success(self, connection_manager, mock_websocket):
        """Test successful connect message handling."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        connection = connection_manager.connections[connection_id]
        
        mock_message = MagicMock()
        mock_message.data = {
            "session_type": "terminal",
            "terminal_size": {"cols": 80, "rows": 24}
        }
        
        with patch('app.db.database.AsyncSessionLocal') as mock_session_local:
            with patch('app.repositories.session.SessionRepository') as mock_session_repo:
                with patch('app.websocket.terminal.TerminalSession') as mock_terminal_session:
                    mock_db = AsyncMock()
                    mock_session_local.return_value.__aenter__.return_value = mock_db
                    
                    mock_repo = AsyncMock()
                    mock_session_repo.return_value = mock_repo
                    
                    mock_db_session = MagicMock()
                    mock_db_session.id = "db-session-123"
                    mock_repo.create.return_value = mock_db_session
                    
                    mock_terminal = MagicMock()
                    mock_terminal.session_id = "db-session-123"
                    mock_terminal.start = AsyncMock()
                    mock_terminal_session.return_value = mock_terminal
                    
                    await connection_manager._handle_connect_message(connection, mock_message)
                    
                    # Verify session was created and started
                    mock_repo.create.assert_called_once()
                    mock_terminal.start.assert_called_once()
                    mock_websocket.send_json.assert_called()  # Status message sent

    async def test_handle_connect_message_invalid_data_type(self, connection_manager, mock_websocket):
        """Test connect message with invalid data type."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        connection = connection_manager.connections[connection_id]
        
        mock_message = MagicMock()
        mock_message.data = "invalid_data_type"  # Should be dict
        
        with patch('app.core.logging.logger.error') as mock_logger:
            await connection_manager._handle_connect_message(connection, mock_message)
            
            mock_logger.assert_called_once()
            mock_websocket.send_json.assert_called()  # Error message sent

    async def test_handle_connect_message_with_ssh_profile(self, connection_manager, mock_websocket):
        """Test connect message with SSH profile."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        connection = connection_manager.connections[connection_id]
        
        mock_message = MagicMock()
        mock_message.data = {
            "session_type": "terminal",
            "ssh_profile_id": "ssh-profile-123"
        }
        
        with patch('app.db.database.AsyncSessionLocal') as mock_session_local:
            with patch('app.repositories.session.SessionRepository') as mock_session_repo:
                with patch('app.websocket.terminal.TerminalSession') as mock_terminal_session:
                    mock_db = AsyncMock()
                    mock_session_local.return_value.__aenter__.return_value = mock_db
                    
                    mock_repo = AsyncMock()
                    mock_session_repo.return_value = mock_repo
                    
                    mock_db_session = MagicMock()
                    mock_db_session.id = "db-session-123"
                    mock_repo.create.return_value = mock_db_session
                    
                    mock_terminal = MagicMock()
                    mock_terminal.start = AsyncMock()
                    mock_terminal_session.return_value = mock_terminal
                    
                    await connection_manager._handle_connect_message(connection, mock_message)
                    
                    # Verify SSH session type was set
                    create_call = mock_repo.create.call_args[0][0]
                    assert create_call["session_type"] == "ssh"

    async def test_handle_connect_message_exception(self, connection_manager, mock_websocket):
        """Test connect message handling with exception."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        connection = connection_manager.connections[connection_id]
        
        mock_message = MagicMock()
        mock_message.data = {"session_type": "terminal"}
        
        with patch('app.db.database.AsyncSessionLocal', side_effect=Exception("Database error")):
            with patch('app.core.logging.logger.error') as mock_logger:
                await connection_manager._handle_connect_message(connection, mock_message)
                
                mock_logger.assert_called_once()
                mock_websocket.send_json.assert_called()  # Error message sent

    async def test_handle_disconnect_message(self, connection_manager, mock_websocket):
        """Test disconnect message handling."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        connection = connection_manager.connections[connection_id]
        
        # Add terminal session
        mock_session = MagicMock(spec=TerminalSession)
        mock_session.session_id = "session-123"
        connection.terminal_sessions["session-123"] = mock_session
        connection_manager.session_connections["session-123"] = connection_id
        
        mock_message = MagicMock()
        mock_message.session_id = "session-123"
        
        with patch.object(connection_manager, '_cleanup_terminal_session') as mock_cleanup:
            await connection_manager._handle_disconnect_message(connection, mock_message)
            
            mock_cleanup.assert_called_once_with(mock_session)
            assert "session-123" not in connection.terminal_sessions
            assert "session-123" not in connection_manager.session_connections

    async def test_handle_disconnect_message_no_session_id(self, connection_manager, mock_websocket):
        """Test disconnect message with no session ID."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        connection = connection_manager.connections[connection_id]
        
        mock_message = MagicMock()
        mock_message.session_id = None
        
        # Should not do anything
        await connection_manager._handle_disconnect_message(connection, mock_message)

    async def test_handle_terminal_message_input(self, connection_manager, mock_websocket):
        """Test handling terminal input message."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        connection = connection_manager.connections[connection_id]
        
        # Add terminal session
        mock_session = MagicMock(spec=TerminalSession)
        mock_session.handle_input = AsyncMock()
        connection.terminal_sessions["session-123"] = mock_session
        
        mock_message = MagicMock()
        mock_message.session_id = "session-123"
        mock_message.type = MessageType.INPUT
        mock_message.data = "ls -la"
        
        await connection_manager._handle_terminal_message(connection, mock_message)
        
        mock_session.handle_input.assert_called_once_with("ls -la")

    async def test_handle_terminal_message_resize(self, connection_manager, mock_websocket):
        """Test handling terminal resize message."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        connection = connection_manager.connections[connection_id]
        
        # Add terminal session
        mock_session = MagicMock(spec=TerminalSession)
        mock_session.handle_resize = AsyncMock()
        connection.terminal_sessions["session-123"] = mock_session
        
        mock_message = MagicMock()
        mock_message.session_id = "session-123"
        mock_message.type = MessageType.RESIZE
        mock_message.data = {"cols": 120, "rows": 30}
        
        await connection_manager._handle_terminal_message(connection, mock_message)
        
        mock_session.handle_resize.assert_called_once_with(120, 30)

    async def test_handle_terminal_message_signal(self, connection_manager, mock_websocket):
        """Test handling terminal signal message."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        connection = connection_manager.connections[connection_id]
        
        # Add terminal session
        mock_session = MagicMock(spec=TerminalSession)
        mock_session.handle_signal = AsyncMock()
        connection.terminal_sessions["session-123"] = mock_session
        
        mock_message = MagicMock()
        mock_message.session_id = "session-123"
        mock_message.type = MessageType.SIGNAL
        mock_message.data = {"signal": "SIGINT"}
        
        await connection_manager._handle_terminal_message(connection, mock_message)
        
        mock_session.handle_signal.assert_called_once_with("SIGINT")

    async def test_handle_terminal_message_no_session_id(self, connection_manager, mock_websocket):
        """Test terminal message with no session ID."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        connection = connection_manager.connections[connection_id]
        
        mock_message = MagicMock()
        mock_message.session_id = None
        
        await connection_manager._handle_terminal_message(connection, mock_message)
        
        mock_websocket.send_json.assert_called()  # Error message sent

    async def test_handle_terminal_message_session_not_found(self, connection_manager, mock_websocket):
        """Test terminal message for non-existent session."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        connection = connection_manager.connections[connection_id]
        
        mock_message = MagicMock()
        mock_message.session_id = "nonexistent-session"
        
        await connection_manager._handle_terminal_message(connection, mock_message)
        
        mock_websocket.send_json.assert_called()  # Error message sent

    async def test_handle_terminal_message_invalid_input_data(self, connection_manager, mock_websocket):
        """Test terminal message with invalid input data type."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        connection = connection_manager.connections[connection_id]
        
        # Add terminal session
        mock_session = MagicMock(spec=TerminalSession)
        connection.terminal_sessions["session-123"] = mock_session
        
        mock_message = MagicMock()
        mock_message.session_id = "session-123"
        mock_message.type = MessageType.INPUT
        mock_message.data = 123  # Should be string
        
        with patch('app.core.logging.logger.warning') as mock_logger:
            await connection_manager._handle_terminal_message(connection, mock_message)
            
            mock_logger.assert_called_once()

    async def test_handle_terminal_message_invalid_resize_data(self, connection_manager, mock_websocket):
        """Test terminal message with invalid resize data type."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        connection = connection_manager.connections[connection_id]
        
        # Add terminal session
        mock_session = MagicMock(spec=TerminalSession)
        connection.terminal_sessions["session-123"] = mock_session
        
        mock_message = MagicMock()
        mock_message.session_id = "session-123"
        mock_message.type = MessageType.RESIZE
        mock_message.data = "invalid"  # Should be dict
        
        with patch('app.core.logging.logger.warning') as mock_logger:
            await connection_manager._handle_terminal_message(connection, mock_message)
            
            mock_logger.assert_called_once()

    async def test_handle_terminal_message_invalid_signal_data(self, connection_manager, mock_websocket):
        """Test terminal message with invalid signal data type."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        connection = connection_manager.connections[connection_id]
        
        # Add terminal session
        mock_session = MagicMock(spec=TerminalSession)
        connection.terminal_sessions["session-123"] = mock_session
        
        mock_message = MagicMock()
        mock_message.session_id = "session-123"
        mock_message.type = MessageType.SIGNAL
        mock_message.data = 123  # Should be dict
        
        with patch('app.core.logging.logger.warning') as mock_logger:
            await connection_manager._handle_terminal_message(connection, mock_message)
            
            mock_logger.assert_called_once()

    async def test_cleanup_terminal_session(self, connection_manager):
        """Test terminal session cleanup."""
        mock_session = MagicMock(spec=TerminalSession)
        mock_session.stop = AsyncMock()
        
        await connection_manager._cleanup_terminal_session(mock_session)
        
        mock_session.stop.assert_called_once()

    async def test_cleanup_terminal_session_error(self, connection_manager):
        """Test terminal session cleanup with error."""
        mock_session = MagicMock(spec=TerminalSession)
        mock_session.session_id = "session-123"
        mock_session.stop = AsyncMock(side_effect=Exception("Cleanup error"))
        
        with patch('app.core.logging.logger.error') as mock_logger:
            await connection_manager._cleanup_terminal_session(mock_session)
            
            mock_logger.assert_called_once()

    async def test_start_background_tasks(self, connection_manager):
        """Test starting background tasks."""
        assert connection_manager._cleanup_task is None
        
        await connection_manager.start_background_tasks()
        
        assert connection_manager._cleanup_task is not None
        assert not connection_manager._cleanup_task.done()
        
        # Clean up
        connection_manager._cleanup_task.cancel()

    async def test_start_background_tasks_already_running(self, connection_manager):
        """Test starting background tasks when already running."""
        # Start first time
        await connection_manager.start_background_tasks()
        first_task = connection_manager._cleanup_task
        
        # Start again
        await connection_manager.start_background_tasks()
        
        # Should be same task
        assert connection_manager._cleanup_task == first_task
        
        # Clean up
        connection_manager._cleanup_task.cancel()

    async def test_start_background_tasks_done_task(self, connection_manager):
        """Test starting background tasks when previous task is done."""
        # Create a completed task
        done_task = asyncio.create_task(asyncio.sleep(0))
        await done_task
        connection_manager._cleanup_task = done_task
        
        await connection_manager.start_background_tasks()
        
        # Should create new task
        assert connection_manager._cleanup_task != done_task
        assert not connection_manager._cleanup_task.done()
        
        # Clean up
        connection_manager._cleanup_task.cancel()

    async def test_stop_background_tasks(self, connection_manager):
        """Test stopping background tasks."""
        await connection_manager.start_background_tasks()
        assert connection_manager._cleanup_task is not None
        
        await connection_manager.stop_background_tasks()
        
        assert connection_manager._cleanup_task.cancelled()

    async def test_stop_background_tasks_no_task(self, connection_manager):
        """Test stopping background tasks when no task exists."""
        # Should not raise an exception
        await connection_manager.stop_background_tasks()

    async def test_cleanup_inactive_connections(self, connection_manager, mock_websocket):
        """Test cleanup of inactive connections."""
        # Connect a connection
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        connection = connection_manager.connections[connection_id]
        
        # Make connection appear inactive (last ping > 60 seconds ago)
        connection.last_ping = datetime.now() - timedelta(seconds=70)
        
        with patch.object(connection_manager, 'disconnect') as mock_disconnect:
            with patch('app.core.logging.logger.info') as mock_logger:
                # Run one iteration of cleanup
                cleanup_task = asyncio.create_task(connection_manager._cleanup_inactive_connections())
                
                # Wait a bit for the task to run
                await asyncio.sleep(0.1)
                cleanup_task.cancel()
                
                try:
                    await cleanup_task
                except asyncio.CancelledError:
                    pass
                
                mock_disconnect.assert_called_once_with(connection_id)
                mock_logger.assert_called_once()

    async def test_cleanup_inactive_connections_exception_handling(self, connection_manager):
        """Test cleanup task exception handling."""
        with patch.object(connection_manager, 'disconnect', side_effect=Exception("Disconnect error")):
            with patch('app.core.logging.logger.error') as mock_logger:
                # Connect a connection and make it inactive
                mock_websocket = MagicMock(spec=WebSocket)
                mock_websocket.accept = AsyncMock()
                connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
                connection = connection_manager.connections[connection_id]
                connection.last_ping = datetime.now() - timedelta(seconds=70)
                
                # Run one iteration of cleanup
                cleanup_task = asyncio.create_task(connection_manager._cleanup_inactive_connections())
                
                # Wait a bit for the task to run
                await asyncio.sleep(0.1)
                cleanup_task.cancel()
                
                try:
                    await cleanup_task
                except asyncio.CancelledError:
                    pass
                
                mock_logger.assert_called()

    def test_get_connection_count(self, connection_manager):
        """Test getting total connection count."""
        assert connection_manager.get_connection_count() == 0
        
        # Add mock connections
        connection_manager.connections["conn1"] = MagicMock()
        connection_manager.connections["conn2"] = MagicMock()
        
        assert connection_manager.get_connection_count() == 2

    def test_get_user_connection_count(self, connection_manager):
        """Test getting connection count for specific user."""
        assert connection_manager.get_user_connection_count("user-123") == 0
        
        # Add user connections
        connection_manager.user_connections["user-123"] = {"conn1", "conn2"}
        connection_manager.user_connections["user-456"] = {"conn3"}
        
        assert connection_manager.get_user_connection_count("user-123") == 2
        assert connection_manager.get_user_connection_count("user-456") == 1
        assert connection_manager.get_user_connection_count("user-999") == 0

    def test_get_session_count(self, connection_manager):
        """Test getting total session count."""
        assert connection_manager.get_session_count() == 0
        
        # Add session connections
        connection_manager.session_connections["session1"] = "conn1"
        connection_manager.session_connections["session2"] = "conn2"
        
        assert connection_manager.get_session_count() == 2

    # Test Integration Scenarios
    async def test_full_connection_lifecycle(self, connection_manager, mock_websocket):
        """Test complete connection lifecycle."""
        # Connect
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        assert connection_id in connection_manager.connections
        
        # Handle ping
        ping_message = {"type": "ping"}
        with patch('app.websocket.protocols.parse_message') as mock_parse:
            mock_message = MagicMock()
            mock_message.type = MessageType.PING
            mock_parse.return_value = mock_message
            
            await connection_manager.handle_message(connection_id, ping_message)
            
            # Verify ping timestamp was updated
            connection = connection_manager.connections[connection_id]
            assert connection.last_ping is not None
        
        # Disconnect
        await connection_manager.disconnect(connection_id)
        assert connection_id not in connection_manager.connections

    async def test_multiple_users_multiple_connections(self, connection_manager):
        """Test managing multiple users with multiple connections."""
        connections = []
        
        # Create connections for multiple users
        for user_idx in range(3):
            for device_idx in range(2):
                mock_ws = MagicMock(spec=WebSocket)
                mock_ws.accept = AsyncMock()
                
                conn_id = await connection_manager.connect(
                    mock_ws, f"user-{user_idx}", f"device-{device_idx}"
                )
                connections.append((conn_id, f"user-{user_idx}"))
        
        # Verify all connections are tracked
        assert len(connection_manager.connections) == 6
        assert len(connection_manager.user_connections) == 3
        
        for user_idx in range(3):
            assert len(connection_manager.user_connections[f"user-{user_idx}"]) == 2
        
        # Disconnect all connections
        for conn_id, user_id in connections:
            await connection_manager.disconnect(conn_id)
        
        # Verify cleanup
        assert len(connection_manager.connections) == 0
        assert len(connection_manager.user_connections) == 0

    async def test_connection_with_terminal_sessions(self, connection_manager, mock_websocket):
        """Test connection with terminal session management."""
        connection_id = await connection_manager.connect(mock_websocket, "user-123", "device-456")
        connection = connection_manager.connections[connection_id]
        
        # Add multiple terminal sessions
        for i in range(3):
            session = MagicMock(spec=TerminalSession)
            session.session_id = f"session-{i}"
            connection.add_terminal_session(session)
            connection_manager.session_connections[f"session-{i}"] = connection_id
        
        assert len(connection.terminal_sessions) == 3
        assert len(connection_manager.session_connections) == 3
        
        # Disconnect should clean up all sessions
        with patch.object(connection_manager, '_cleanup_terminal_session') as mock_cleanup:
            await connection_manager.disconnect(connection_id)
            
            assert mock_cleanup.call_count == 3
            assert len(connection_manager.session_connections) == 0