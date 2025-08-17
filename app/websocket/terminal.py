"""
Terminal session management for WebSocket connections.

Manages different types of terminal sessions (SSH, PTY, local) and coordinates
between WebSocket connections and terminal handlers.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.session import Session
from app.models.ssh_profile import SSHProfile
from app.repositories.session import SessionRepository
from app.repositories.ssh_profile import SSHProfileRepository
from .protocols import (
    create_output_message,
    create_status_message,
    create_error_message,
)
from .pty_handler import PTYHandler
from .ssh_handler import SSHHandler

if TYPE_CHECKING:
    from .manager import Connection


class TerminalSession:
    """
    Manages a terminal session with WebSocket communication.

    This class coordinates between different terminal handlers (PTY, SSH)
    and the WebSocket connection, providing a unified interface for
    terminal operations.
    """

    def __init__(
        self,
        session_id: str,
        connection: "Connection",
        ssh_profile_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ):
        """
        Initialize terminal session.

        Args:
            session_id: Database session ID
            connection: WebSocket connection
            ssh_profile_id: Optional SSH profile ID for SSH sessions
            db: Database session
        """
        self.session_id = session_id
        self.connection = connection
        self.ssh_profile_id = ssh_profile_id
        self.db = db

        # Session state
        self._running = False
        self._session_type = "terminal"

        # Terminal handlers
        self.pty_handler: Optional[PTYHandler] = None
        self.ssh_handler: Optional[SSHHandler] = None

        # Terminal configuration
        self.rows = 24
        self.cols = 80

        # Database models
        self.db_session: Optional[Session] = None
        self.ssh_profile: Optional[SSHProfile] = None

    async def start(self) -> bool:
        """
        Start the terminal session.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            # Load session from database
            if self.db:
                session_repo = SessionRepository(self.db)
                self.db_session = await session_repo.get(self.session_id)

                if not self.db_session:
                    logger.error(f"Session not found: {self.session_id}")
                    return False

                # Get terminal dimensions
                self.rows = self.db_session.terminal_rows
                self.cols = self.db_session.terminal_cols
                self._session_type = self.db_session.session_type

            # Determine session type and start appropriate handler
            if self.ssh_profile_id:
                return await self._start_ssh_session()
            else:
                return await self._start_pty_session()

        except Exception as e:
            logger.error(f"Failed to start terminal session {self.session_id}: {e}")
            await self._send_error("session_start_failed", str(e))
            return False

    async def stop(self) -> None:
        """Stop the terminal session and clean up resources."""
        self._running = False

        # Stop handlers
        if self.ssh_handler:
            await self.ssh_handler.disconnect()
            self.ssh_handler = None

        if self.pty_handler:
            await self.pty_handler.stop()
            self.pty_handler = None

        # Update database session
        if self.db_session and self.db:
            try:
                session_repo = SessionRepository(self.db)
                self.db_session.end_session()
                await session_repo.update(
                    self.db_session,  # Pass the session object instead of just ID
                    is_active=False,
                    ended_at=datetime.now(),
                )
                await self.db.commit()
            except Exception as e:
                logger.error(f"Failed to update session in database: {e}")

        logger.info(f"Terminal session stopped: {self.session_id}")

    async def handle_input(self, data: str) -> None:
        """
        Handle input from WebSocket client.

        Args:
            data: Input data from client
        """
        if not self._running:
            return

        try:
            # Route input to appropriate handler
            if self.ssh_handler:
                success = await self.ssh_handler.write_input(data)
            elif self.pty_handler:
                success = await self.pty_handler.write_input(data)
            else:
                logger.warning(
                    f"No handler available for input in session {self.session_id}"
                )
                return

            if not success:
                await self._send_error(
                    "input_failed", "Failed to send input to terminal"
                )

        except Exception as e:
            logger.error(f"Failed to handle input in session {self.session_id}: {e}")
            await self._send_error("input_error", str(e))

    async def handle_resize(self, cols: int, rows: int) -> None:
        """
        Handle terminal resize request.

        Args:
            cols: New terminal columns
            rows: New terminal rows
        """
        if not self._running:
            return

        try:
            self.cols = cols
            self.rows = rows

            # Resize handler
            success = False
            if self.ssh_handler:
                success = await self.ssh_handler.resize_terminal(cols, rows)
            elif self.pty_handler:
                success = self.pty_handler.resize_terminal(cols, rows)

            # Update database
            if self.db_session and self.db:
                try:
                    session_repo = SessionRepository(self.db)
                    await session_repo.update(
                        self.db_session,  # Pass the session object instead of just ID
                        terminal_cols=cols,
                        terminal_rows=rows,
                    )
                    await self.db.commit()
                except Exception as e:
                    logger.warning(f"Failed to update terminal size in database: {e}")

            if success:
                logger.debug(
                    f"Terminal resized to {cols}x{rows} for session {self.session_id}"
                )
            else:
                await self._send_error("resize_failed", "Failed to resize terminal")

        except Exception as e:
            logger.error(f"Failed to handle resize in session {self.session_id}: {e}")
            await self._send_error("resize_error", str(e))

    async def handle_signal(self, signal_name: str) -> None:
        """
        Handle signal request (Ctrl+C, etc.).

        Args:
            signal_name: Signal name to send
        """
        if not self._running:
            return

        try:
            # Send signal to appropriate handler
            success = False
            if self.ssh_handler:
                success = self.ssh_handler.send_signal(signal_name)
            elif self.pty_handler:
                success = self.pty_handler.send_signal(signal_name)

            if success:
                logger.debug(f"Signal {signal_name} sent to session {self.session_id}")
            else:
                logger.warning(
                    f"Failed to send signal {signal_name} to session {self.session_id}"
                )

        except Exception as e:
            logger.error(f"Failed to handle signal in session {self.session_id}: {e}")

    async def _start_ssh_session(self) -> bool:
        """Start an SSH terminal session."""
        try:
            # Load SSH profile from database
            if not self.db:
                raise Exception("Database session required for SSH")

            ssh_repo = SSHProfileRepository(self.db)

            if self.ssh_profile_id is None:
                await self._send_error(
                    "ssh_profile_required", "SSH profile ID is required"
                )
                return False

            self.ssh_profile = await ssh_repo.get(self.ssh_profile_id)

            if not self.ssh_profile:
                await self._send_error("ssh_profile_not_found", "SSH profile not found")
                return False

            # Get SSH key if available
            ssh_key = None
            if self.ssh_profile.ssh_key:
                ssh_key = self.ssh_profile.ssh_key

            # Create SSH handler
            self.ssh_handler = SSHHandler(
                ssh_profile=self.ssh_profile,
                ssh_key=ssh_key,
                output_callback=self._handle_output,
                rows=self.rows,
                cols=self.cols,
            )

            # Connect to SSH server
            connect_result = await self.ssh_handler.connect()

            if not connect_result["success"]:
                await self._send_error(
                    connect_result.get("error", "ssh_connection_failed"),
                    connect_result.get("message", "SSH connection failed"),
                )
                return False

            # Update database session with SSH details
            if self.db_session:
                session_repo = SessionRepository(self.db)
                await session_repo.update(
                    self.db_session,  # Pass the session object instead of just ID
                    ssh_host=self.ssh_profile.host,
                    ssh_port=self.ssh_profile.port,
                    ssh_username=self.ssh_profile.username,
                    session_type="ssh",
                )
                await self.db.commit()

            self._running = True

            # Send success status
            await self._send_status(
                "connected",
                f"Connected to {self.ssh_profile.username}@{self.ssh_profile.host}",
                connect_result.get("server_info", {}),
            )

            logger.info(f"SSH session started: {self.session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start SSH session {self.session_id}: {e}")
            await self._send_error("ssh_session_failed", str(e))
            return False

    async def _start_pty_session(self) -> bool:
        """Start a PTY terminal session."""
        try:
            # Create PTY handler
            self.pty_handler = PTYHandler(
                output_callback=self._handle_output,
                rows=self.rows,
                cols=self.cols,
            )

            # Start PTY
            success = await self.pty_handler.start()

            if not success:
                await self._send_error("pty_start_failed", "Failed to start terminal")
                return False

            self._running = True

            # Send success status
            await self._send_status("connected", "Terminal session started")

            logger.info(f"PTY session started: {self.session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start PTY session {self.session_id}: {e}")
            await self._send_error("pty_session_failed", str(e))
            return False

    async def _handle_output(self, data: str) -> None:
        """
        Handle output from terminal handlers and send to WebSocket.

        Args:
            data: Terminal output data
        """
        try:
            # Create output message
            message = create_output_message(self.session_id, data)

            # Send to WebSocket connection
            await self.connection.send_message(message)

            # Update session activity
            if self.db_session:
                self.db_session.update_activity()

        except Exception as e:
            logger.error(f"Failed to handle output in session {self.session_id}: {e}")

    async def _send_status(
        self,
        status: str,
        message: str = "",
        server_info: Optional[dict] = None,
    ) -> None:
        """Send status message to client."""
        try:
            status_msg = create_status_message(
                self.session_id, status, message, server_info
            )
            await self.connection.send_message(status_msg)
        except Exception as e:
            logger.error(f"Failed to send status message: {e}")

    async def _send_error(self, error: str, message: str) -> None:
        """Send error message to client."""
        try:
            error_msg = create_error_message(error, message, session_id=self.session_id)
            await self.connection.send_message(error_msg)
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

    @property
    def is_running(self) -> bool:
        """Check if terminal session is running."""
        return self._running

    @property
    def session_type(self) -> str:
        """Get session type."""
        return self._session_type

    @property
    def terminal_size(self) -> tuple[int, int]:
        """Get terminal size as (cols, rows)."""
        return (self.cols, self.rows)

    def get_status(self) -> dict:
        """Get session status information."""
        status = {
            "session_id": self.session_id,
            "session_type": self._session_type,
            "running": self._running,
            "terminal_size": {"cols": self.cols, "rows": self.rows},
        }

        if self.ssh_handler:
            status["ssh_info"] = self.ssh_handler.connection_info
        elif self.pty_handler:
            status["pty_info"] = {
                "running": self.pty_handler.is_running,
                "terminal_size": self.pty_handler.get_terminal_size(),
            }

        return status
