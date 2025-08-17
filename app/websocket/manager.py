"""
WebSocket connection manager for DevPocket API.

Manages WebSocket connections, message routing, and session lifecycle.
"""

import asyncio
import contextlib
import uuid
from datetime import datetime

import redis.asyncio as aioredis
from fastapi import WebSocket

from app.core.logging import logger
from app.db.database import AsyncSessionLocal
from app.repositories.session import SessionRepository

from .protocols import (
    HeartbeatMessage,
    MessageType,
    TerminalMessage,
    create_error_message,
    create_status_message,
    parse_message,
)
from .terminal import TerminalSession


class Connection:
    """Represents a WebSocket connection with associated data."""

    def __init__(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: str,
        device_id: str,
    ):
        self.websocket = websocket
        self.connection_id = connection_id
        self.user_id = user_id
        self.device_id = device_id
        self.connected_at = datetime.now()
        self.last_ping = datetime.now()
        self.terminal_sessions: dict[str, TerminalSession] = {}

    async def send_message(self, message: TerminalMessage) -> bool:
        """
        Send a message through the WebSocket connection.

        Args:
            message: Terminal message to send

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            message_data = message.model_dump(mode="json")
            await self.websocket.send_json(message_data)
            return True
        except Exception as e:
            logger.error(
                f"Failed to send message on connection {self.connection_id}: {e}"
            )
            return False

    async def send_text(self, text: str) -> bool:
        """Send raw text through the WebSocket."""
        try:
            await self.websocket.send_text(text)
            return True
        except Exception as e:
            logger.error(f"Failed to send text on connection {self.connection_id}: {e}")
            return False

    def add_terminal_session(self, session: TerminalSession) -> None:
        """Add a terminal session to this connection."""
        self.terminal_sessions[session.session_id] = session

    def remove_terminal_session(self, session_id: str) -> TerminalSession | None:
        """Remove and return a terminal session."""
        return self.terminal_sessions.pop(session_id, None)

    def get_terminal_session(self, session_id: str) -> TerminalSession | None:
        """Get a terminal session by ID."""
        return self.terminal_sessions.get(session_id)

    def update_ping(self) -> None:
        """Update last ping timestamp."""
        self.last_ping = datetime.now()


class ConnectionManager:
    """Manages all WebSocket connections and routing."""

    def __init__(self, redis_client: aioredis.Redis | None = None):
        self.connections: dict[str, Connection] = {}
        self.user_connections: dict[str, set[str]] = {}  # user_id -> connection_ids
        self.session_connections: dict[str, str] = {}  # session_id -> connection_id
        self.redis = redis_client
        self._cleanup_task: asyncio.Task | None = None

    async def start_background_tasks(self) -> None:
        """Start background tasks for connection management."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(
                self._cleanup_inactive_connections()
            )

    async def stop_background_tasks(self) -> None:
        """Stop background tasks."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task

    async def connect(self, websocket: WebSocket, user_id: str, device_id: str) -> str:
        """
        Register a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            user_id: User ID
            device_id: Device ID

        Returns:
            Connection ID
        """
        await websocket.accept()

        connection_id = str(uuid.uuid4())
        connection = Connection(websocket, connection_id, user_id, device_id)

        # Register connection
        self.connections[connection_id] = connection

        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)

        # Log connection
        logger.info(
            f"WebSocket connected: connection_id={connection_id}, "
            f"user_id={user_id}, device_id={device_id}"
        )

        # Start background tasks if needed
        await self.start_background_tasks()

        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """
        Disconnect and clean up a WebSocket connection.

        Args:
            connection_id: Connection ID to disconnect
        """
        connection = self.connections.get(connection_id)
        if not connection:
            return

        try:
            # Close all terminal sessions for this connection
            for session in list(connection.terminal_sessions.values()):
                await self._cleanup_terminal_session(session)

            # Remove from user connections
            if connection.user_id in self.user_connections:
                self.user_connections[connection.user_id].discard(connection_id)
                if not self.user_connections[connection.user_id]:
                    del self.user_connections[connection.user_id]

            # Remove session mappings
            sessions_to_remove = [
                session_id
                for session_id, conn_id in self.session_connections.items()
                if conn_id == connection_id
            ]
            for session_id in sessions_to_remove:
                del self.session_connections[session_id]

            # Remove connection
            del self.connections[connection_id]

            logger.info(f"WebSocket disconnected: connection_id={connection_id}")

        except Exception as e:
            logger.error(f"Error during disconnect cleanup: {e}")

    async def handle_message(self, connection_id: str, message_data: dict) -> None:
        """
        Handle incoming WebSocket message.

        Args:
            connection_id: Connection ID
            message_data: Raw message data
        """
        connection = self.connections.get(connection_id)
        if not connection:
            logger.warning(f"Message from unknown connection: {connection_id}")
            return

        try:
            message = parse_message(message_data)

            # Handle heartbeat messages
            if message.type == MessageType.PING:
                connection.update_ping()
                pong = HeartbeatMessage(type=MessageType.PONG)
                await connection.send_message(pong)
                return

            # Route message based on type
            if message.type == MessageType.CONNECT:
                await self._handle_connect_message(connection, message)
            elif message.type == MessageType.DISCONNECT:
                await self._handle_disconnect_message(connection, message)
            elif message.type in [
                MessageType.INPUT,
                MessageType.RESIZE,
                MessageType.SIGNAL,
            ]:
                await self._handle_terminal_message(connection, message)
            else:
                logger.warning(f"Unhandled message type: {message.type}")

        except ValueError as e:
            logger.warning(f"Invalid message from {connection_id}: {e}")
            error_msg = create_error_message("invalid_message", str(e))
            await connection.send_message(error_msg)
        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {e}")
            error_msg = create_error_message("message_handling_error", "Internal error")
            await connection.send_message(error_msg)

    async def _handle_connect_message(
        self, connection: Connection, message: TerminalMessage
    ) -> None:
        """Handle session connect message."""
        try:
            # Type guard: ensure message.data is a dictionary
            if not isinstance(message.data, dict):
                logger.error(f"Invalid connect message data type: {type(message.data)}")
                error_msg = create_error_message(
                    "invalid_message_data",
                    "Connect message data must be a dictionary",
                    {"received_type": str(type(message.data))},
                )
                await connection.send_message(error_msg)
                return

            # Get database session
            async with AsyncSessionLocal() as db:
                session_repo = SessionRepository(db)

                # Extract terminal size safely
                terminal_size = message.data.get("terminal_size", {})
                if isinstance(terminal_size, dict):
                    cols = terminal_size.get("cols", 80)
                    rows = terminal_size.get("rows", 24)
                else:
                    cols = 80
                    rows = 24

                # Create or get session
                session_data = {
                    "user_id": connection.user_id,
                    "device_id": connection.device_id,
                    "device_type": "web",  # Could be enhanced to detect actual device type
                    "session_type": message.data.get("session_type", "terminal"),
                    "terminal_cols": cols,
                    "terminal_rows": rows,
                    "is_active": True,
                }

                # Add SSH details if applicable
                ssh_profile_id = message.data.get("ssh_profile_id")
                if ssh_profile_id:
                    session_data.update(
                        {
                            "session_type": "ssh",
                            # SSH details will be populated by terminal session
                        }
                    )

                db_session = await session_repo.create(session_data)
                await db.commit()

                # Create terminal session
                terminal_session = TerminalSession(
                    session_id=str(db_session.id),  # Convert UUID to string
                    connection=connection,
                    ssh_profile_id=ssh_profile_id,
                    db=db,
                )

                # Register terminal session
                connection.add_terminal_session(terminal_session)
                self.session_connections[
                    str(db_session.id)
                ] = connection.connection_id  # Convert UUID to string

                # Start the terminal session
                await terminal_session.start()

                # Send success status
                status_msg = create_status_message(
                    str(db_session.id),
                    "connected",
                    "Session started successfully",  # Convert UUID to string
                )
                await connection.send_message(status_msg)

        except Exception as e:
            logger.error(f"Failed to create terminal session: {e}")
            error_msg = create_error_message(
                "session_creation_failed",
                "Failed to create terminal session",
                {"error": str(e)},
            )
            await connection.send_message(error_msg)

    async def _handle_disconnect_message(
        self, connection: Connection, message: TerminalMessage
    ) -> None:
        """Handle session disconnect message."""
        if not message.session_id:
            return

        session = connection.get_terminal_session(message.session_id)
        if session:
            await self._cleanup_terminal_session(session)
            connection.remove_terminal_session(message.session_id)
            self.session_connections.pop(message.session_id, None)

    async def _handle_terminal_message(
        self, connection: Connection, message: TerminalMessage
    ) -> None:
        """Handle terminal I/O messages."""
        if not message.session_id:
            error_msg = create_error_message(
                "missing_session_id", "Session ID required"
            )
            await connection.send_message(error_msg)
            return

        session = connection.get_terminal_session(message.session_id)
        if not session:
            error_msg = create_error_message(
                "session_not_found",
                "Terminal session not found",
                session_id=message.session_id,
            )
            await connection.send_message(error_msg)
            return

        # Route to terminal session
        if message.type == MessageType.INPUT:
            # Type guard for input data
            if isinstance(message.data, str):
                await session.handle_input(message.data)
            else:
                logger.warning(f"Invalid input data type: {type(message.data)}")

        elif message.type == MessageType.RESIZE:
            # Type guard for resize data
            if isinstance(message.data, dict):
                cols = message.data.get("cols", 80)
                rows = message.data.get("rows", 24)
                await session.handle_resize(cols, rows)
            else:
                logger.warning(f"Invalid resize data type: {type(message.data)}")

        elif message.type == MessageType.SIGNAL:
            # Type guard for signal data
            if isinstance(message.data, dict):
                signal = message.data.get("signal", "")
                await session.handle_signal(signal)
            else:
                logger.warning(f"Invalid signal data type: {type(message.data)}")

    async def _cleanup_terminal_session(self, session: TerminalSession) -> None:
        """Clean up a terminal session."""
        try:
            await session.stop()
        except Exception as e:
            logger.error(
                f"Error cleaning up terminal session {session.session_id}: {e}"
            )

    async def _cleanup_inactive_connections(self) -> None:
        """Background task to clean up inactive connections."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                current_time = datetime.now()
                inactive_connections = []

                for connection_id, connection in self.connections.items():
                    # Consider connection inactive if no ping for 60 seconds
                    time_since_ping = (
                        current_time - connection.last_ping
                    ).total_seconds()
                    if time_since_ping > 60:
                        inactive_connections.append(connection_id)

                # Disconnect inactive connections
                for connection_id in inactive_connections:
                    logger.info(f"Cleaning up inactive connection: {connection_id}")
                    await self.disconnect(connection_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self.connections)

    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of connections for a specific user."""
        return len(self.user_connections.get(user_id, set()))

    def get_session_count(self) -> int:
        """Get total number of active terminal sessions."""
        return len(self.session_connections)


# Global connection manager instance
connection_manager = ConnectionManager()
