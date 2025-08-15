"""
Terminal service for DevPocket API.

Provides high-level terminal operations and session management
for use by other application services.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.session import Session
from app.models.ssh_profile import SSHProfile
from app.repositories.session import SessionRepository
from app.repositories.ssh_profile import SSHProfileRepository
from app.websocket.manager import connection_manager


class TerminalService:
    """Service for terminal operations and session management."""

    def __init__(self, db: AsyncSession):
        """
        Initialize terminal service.

        Args:
            db: Database session
        """
        self.db = db
        self.session_repo = SessionRepository(db)
        self.ssh_profile_repo = SSHProfileRepository(db)

    async def get_active_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all active terminal sessions for a user.

        Args:
            user_id: User ID

        Returns:
            List of active session information
        """
        try:
            # Get active sessions from database
            sessions = await self.session_repo.get_user_active_sessions(user_id)

            session_list = []
            for session in sessions:
                session_info = {
                    "id": session.id,
                    "session_name": session.session_name,
                    "session_type": session.session_type,
                    "device_type": session.device_type,
                    "device_name": session.device_name,
                    "created_at": session.created_at.isoformat(),
                    "last_activity_at": session.last_activity_at.isoformat()
                    if session.last_activity_at
                    else None,
                    "terminal_size": {
                        "cols": session.terminal_cols,
                        "rows": session.terminal_rows,
                    },
                    "is_connected": session.id
                    in connection_manager.session_connections,
                }

                # Add SSH information if applicable
                if session.is_ssh_session():
                    session_info["ssh_info"] = {
                        "host": session.ssh_host,
                        "port": session.ssh_port,
                        "username": session.ssh_username,
                    }

                session_list.append(session_info)

            return session_list

        except Exception as e:
            logger.error(f"Failed to get active sessions for user {user_id}: {e}")
            return []

    async def get_session_details(
        self, session_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific session.

        Args:
            session_id: Session ID
            user_id: User ID (for authorization)

        Returns:
            Session details or None if not found/unauthorized
        """
        try:
            session = await self.session_repo.get(session_id)

            if not session or session.user_id != user_id:
                return None

            # Get connection status
            is_connected = session_id in connection_manager.session_connections
            connection_id = connection_manager.session_connections.get(session_id)

            # Get terminal session status if connected
            terminal_status = None
            if is_connected and connection_id:
                connection = connection_manager.connections.get(connection_id)
                if connection:
                    terminal_session = connection.get_terminal_session(session_id)
                    if terminal_session:
                        terminal_status = terminal_session.get_status()

            session_details = {
                "id": session.id,
                "session_name": session.session_name,
                "session_type": session.session_type,
                "device_type": session.device_type,
                "device_name": session.device_name,
                "device_id": session.device_id,
                "created_at": session.created_at.isoformat(),
                "last_activity_at": session.last_activity_at.isoformat()
                if session.last_activity_at
                else None,
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "is_active": session.is_active,
                "terminal_size": {
                    "cols": session.terminal_cols,
                    "rows": session.terminal_rows,
                },
                "connection_status": {
                    "is_connected": is_connected,
                    "connection_id": connection_id,
                    "terminal_status": terminal_status,
                },
                "command_count": session.command_count,
                "duration": session.duration,
            }

            # Add SSH information if applicable
            if session.is_ssh_session():
                session_details["ssh_info"] = {
                    "host": session.ssh_host,
                    "port": session.ssh_port,
                    "username": session.ssh_username,
                }

            return session_details

        except Exception as e:
            logger.error(f"Failed to get session details for {session_id}: {e}")
            return None

    async def terminate_session(self, session_id: str, user_id: str) -> bool:
        """
        Terminate a terminal session.

        Args:
            session_id: Session ID to terminate
            user_id: User ID (for authorization)

        Returns:
            True if terminated successfully, False otherwise
        """
        try:
            # Get session and verify ownership
            session = await self.session_repo.get(session_id)

            if not session or session.user_id != user_id:
                logger.warning(
                    f"Unauthorized session termination attempt: {session_id} by {user_id}"
                )
                return False

            # Disconnect WebSocket connection if active
            if session_id in connection_manager.session_connections:
                connection_id = connection_manager.session_connections[session_id]
                connection = connection_manager.connections.get(connection_id)

                if connection:
                    terminal_session = connection.get_terminal_session(session_id)
                    if terminal_session:
                        await terminal_session.stop()
                        connection.remove_terminal_session(session_id)

                    # Remove from session mapping
                    del connection_manager.session_connections[session_id]

            # Update session in database
            session.end_session()
            await self.session_repo.update(
                session_id, {"is_active": False, "ended_at": session.ended_at}
            )
            await self.db.commit()

            logger.info(f"Session terminated: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to terminate session {session_id}: {e}")
            return False

    async def get_session_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        session_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get session history for a user.

        Args:
            user_id: User ID
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip
            session_type: Optional filter by session type

        Returns:
            Dictionary with sessions and pagination info
        """
        try:
            # Get sessions from database
            sessions = await self.session_repo.get_user_sessions(
                user_id=user_id,
                limit=limit,
                offset=offset,
                session_type=session_type,
                include_inactive=True,
            )

            total_count = await self.session_repo.get_user_session_count(
                user_id=user_id, session_type=session_type
            )

            session_list = []
            for session in sessions:
                session_info = {
                    "id": session.id,
                    "session_name": session.session_name,
                    "session_type": session.session_type,
                    "device_type": session.device_type,
                    "device_name": session.device_name,
                    "created_at": session.created_at.isoformat(),
                    "ended_at": session.ended_at.isoformat()
                    if session.ended_at
                    else None,
                    "duration": session.duration,
                    "command_count": session.command_count,
                    "is_active": session.is_active,
                    "terminal_size": {
                        "cols": session.terminal_cols,
                        "rows": session.terminal_rows,
                    },
                }

                # Add SSH info if applicable
                if session.is_ssh_session():
                    session_info["ssh_info"] = {
                        "host": session.ssh_host,
                        "port": session.ssh_port,
                        "username": session.ssh_username,
                    }

                session_list.append(session_info)

            return {
                "sessions": session_list,
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(sessions) < total_count,
                },
            }

        except Exception as e:
            logger.error(f"Failed to get session history for user {user_id}: {e}")
            return {
                "sessions": [],
                "pagination": {
                    "total": 0,
                    "limit": limit,
                    "offset": offset,
                    "has_more": False,
                },
            }

    async def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get WebSocket connection and session statistics.

        Returns:
            Dictionary with connection statistics
        """
        try:
            stats = {
                "total_connections": connection_manager.get_connection_count(),
                "total_sessions": connection_manager.get_session_count(),
                "connection_details": [],
            }

            # Get details for each connection (limited for performance)
            for conn_id, connection in list(connection_manager.connections.items())[
                :10
            ]:
                conn_details = {
                    "connection_id": conn_id,
                    "user_id": connection.user_id,
                    "device_id": connection.device_id,
                    "connected_at": connection.connected_at.isoformat(),
                    "session_count": len(connection.terminal_sessions),
                    "last_ping": connection.last_ping.isoformat(),
                }
                stats["connection_details"].append(conn_details)

            return stats

        except Exception as e:
            logger.error(f"Failed to get connection stats: {e}")
            return {
                "total_connections": 0,
                "total_sessions": 0,
                "connection_details": [],
            }

    def get_user_connection_count(self, user_id: str) -> int:
        """
        Get number of active connections for a user.

        Args:
            user_id: User ID

        Returns:
            Number of active connections
        """
        return connection_manager.get_user_connection_count(user_id)
