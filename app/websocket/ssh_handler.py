"""
SSH handler for WebSocket terminal sessions.

Integrates SSH connections with PTY support for real-time terminal communication.
"""

import asyncio
import threading
from typing import Optional, Callable, Awaitable, Dict, Any
import paramiko
from paramiko import SSHClient, Channel

from app.core.logging import logger
from app.models.ssh_profile import SSHProfile, SSHKey
from app.services.ssh_client import SSHClientService


class SSHHandler:
    """
    Handles SSH connections with PTY support for WebSocket terminals.

    This class manages SSH connections, channel creation, and terminal I/O
    for real-time terminal communication through WebSockets.
    """

    def __init__(
        self,
        ssh_profile: SSHProfile,
        ssh_key: Optional[SSHKey],
        output_callback: Callable[[str], Awaitable[None]],
        rows: int = 24,
        cols: int = 80,
    ):
        """
        Initialize SSH handler.

        Args:
            ssh_profile: SSH profile configuration
            ssh_key: SSH key for authentication (optional)
            output_callback: Async callback for terminal output
            rows: Terminal rows
            cols: Terminal columns
        """
        self.ssh_profile = ssh_profile
        self.ssh_key = ssh_key
        self.output_callback = output_callback
        self.rows = rows
        self.cols = cols

        # SSH connection components
        self.ssh_client: Optional[SSHClient] = None
        self.ssh_channel: Optional[Channel] = None
        self.ssh_service = SSHClientService()

        # Connection state
        self._connected = False
        self._running = False

        # Threading for SSH I/O
        self._output_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Server information
        self.server_info: Dict[str, Any] = {}

    async def connect(self) -> Dict[str, Any]:
        """
        Establish SSH connection with PTY support.

        Returns:
            Dictionary with connection result and server information
        """
        try:
            logger.info(
                f"Connecting to SSH: {self.ssh_profile.username}@{self.ssh_profile.host}:{self.ssh_profile.port}"
            )

            # Create SSH client
            self.ssh_client = SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Prepare connection parameters
            connect_params = {
                "hostname": self.ssh_profile.host,
                "port": self.ssh_profile.port,
                "username": self.ssh_profile.username,
                "timeout": 30,
                "banner_timeout": 30,
                "auth_timeout": 30,
            }

            # Add authentication
            if self.ssh_key:
                try:
                    private_key = self.ssh_service._load_private_key(self.ssh_key)
                    connect_params["pkey"] = private_key
                    auth_method = "publickey"
                except Exception as e:
                    return {
                        "success": False,
                        "message": f"Failed to load SSH key: {str(e)}",
                        "error": "key_load_failed",
                    }
            elif self.ssh_profile.password:
                connect_params["password"] = self.ssh_profile.password
                auth_method = "password"
            else:
                return {
                    "success": False,
                    "message": "No authentication method available",
                    "error": "no_auth_method",
                }

            # Connect to SSH server
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self.ssh_client.connect(**connect_params)
            )

            # Get server information
            transport = self.ssh_client.get_transport()
            if transport:
                self.server_info = {
                    "version": transport.remote_version,
                    "cipher": (
                        transport.get_cipher()[0]
                        if transport.get_cipher()
                        else "unknown"
                    ),
                    "host_key_type": transport.get_host_key().get_name(),
                    "auth_method": auth_method,
                }

            # Create interactive shell channel
            await self._create_shell_channel()

            self._connected = True
            self._running = True

            # Start output reading thread
            self._output_thread = threading.Thread(
                target=self._read_output_loop, daemon=True
            )
            self._output_thread.start()

            logger.info(f"SSH connection established: {self.ssh_profile.host}")

            return {
                "success": True,
                "message": "SSH connection established",
                "server_info": self.server_info,
            }

        except paramiko.AuthenticationException as e:
            logger.warning(f"SSH authentication failed: {e}")
            await self.disconnect()
            return {
                "success": False,
                "message": f"Authentication failed: {str(e)}",
                "error": "authentication_failed",
            }
        except paramiko.SSHException as e:
            logger.warning(f"SSH connection failed: {e}")
            await self.disconnect()
            return {
                "success": False,
                "message": f"SSH connection failed: {str(e)}",
                "error": "connection_failed",
            }
        except Exception as e:
            logger.error(f"Unexpected SSH connection error: {e}")
            await self.disconnect()
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "error": "unexpected_error",
            }

    async def disconnect(self) -> None:
        """Disconnect SSH session and clean up resources."""
        self._running = False
        self._connected = False

        # Signal stop and wait for output thread
        self._stop_event.set()
        if self._output_thread and self._output_thread.is_alive():
            self._output_thread.join(timeout=5)

        # Close SSH channel
        if self.ssh_channel:
            try:
                self.ssh_channel.close()
            except Exception as e:
                logger.warning(f"Error closing SSH channel: {e}")
            self.ssh_channel = None

        # Close SSH client
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except Exception as e:
                logger.warning(f"Error closing SSH client: {e}")
            self.ssh_client = None

        logger.info(f"SSH session disconnected: {self.ssh_profile.host}")

    async def write_input(self, data: str) -> bool:
        """
        Send input to the SSH session.

        Args:
            data: Input data to send

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.ssh_channel or not self._connected:
            return False

        try:
            # Send data to SSH channel
            bytes_sent = self.ssh_channel.send(data)
            return bytes_sent > 0

        except Exception as e:
            logger.error(f"Failed to send SSH input: {e}")
            return False

    async def resize_terminal(self, cols: int, rows: int) -> bool:
        """
        Resize the SSH terminal.

        Args:
            cols: Terminal columns
            rows: Terminal rows

        Returns:
            True if resized successfully, False otherwise
        """
        if not self.ssh_channel or not self._connected:
            return False

        try:
            self.cols = cols
            self.rows = rows

            # Resize SSH channel terminal
            self.ssh_channel.resize_pty(cols, rows)

            logger.debug(f"SSH terminal resized to {cols}x{rows}")
            return True

        except Exception as e:
            logger.error(f"Failed to resize SSH terminal: {e}")
            return False

    def send_signal(self, signal_name: str) -> bool:
        """
        Send a signal to the remote process.

        Args:
            signal_name: Signal name (e.g., 'SIGINT', 'SIGTERM')

        Returns:
            True if signal sent successfully, False otherwise
        """
        if not self.ssh_channel or not self._connected:
            return False

        try:
            # Map common signals to key sequences
            signal_sequences = {
                "SIGINT": "\x03",  # Ctrl+C
                "SIGQUIT": "\x1c",  # Ctrl+\
                "SIGTERM": "\x15",  # Ctrl+U
                "SIGTSTP": "\x1a",  # Ctrl+Z
            }

            sequence = signal_sequences.get(signal_name.upper())
            if sequence:
                self.ssh_channel.send(sequence)
                logger.debug(f"Sent {signal_name} signal via key sequence")
                return True
            else:
                logger.warning(f"No key sequence mapping for signal: {signal_name}")
                return False

        except Exception as e:
            logger.error(f"Failed to send signal {signal_name}: {e}")
            return False

    async def _create_shell_channel(self) -> None:
        """Create an interactive shell channel with PTY."""
        if not self.ssh_client:
            raise Exception("SSH client not connected")

        # Create channel
        self.ssh_channel = self.ssh_client.invoke_shell(
            term="xterm-256color", width=self.cols, height=self.rows
        )

        # Configure channel
        self.ssh_channel.settimeout(0.1)  # Non-blocking reads

        logger.debug("SSH shell channel created with PTY support")

    def _read_output_loop(self) -> None:
        """Read output from SSH channel in a separate thread."""
        logger.debug("Starting SSH output reading loop")

        while self._running and self.ssh_channel and not self._stop_event.is_set():
            try:
                if self.ssh_channel.recv_ready():
                    # Read available data
                    data = self.ssh_channel.recv(1024)
                    if data:
                        # Decode and send via callback
                        try:
                            output_text = data.decode("utf-8", errors="replace")
                            # Schedule callback in asyncio loop
                            asyncio.run_coroutine_threadsafe(
                                self.output_callback(output_text),
                                asyncio.get_event_loop(),
                            )
                        except Exception as e:
                            logger.error(f"Failed to process SSH output: {e}")
                    else:
                        # Channel closed
                        logger.info("SSH channel closed by remote host")
                        break

                # Check stderr
                if self.ssh_channel.recv_stderr_ready():
                    stderr_data = self.ssh_channel.recv_stderr(1024)
                    if stderr_data:
                        stderr_text = stderr_data.decode("utf-8", errors="replace")
                        # Send stderr as regular output (many terminals do this)
                        asyncio.run_coroutine_threadsafe(
                            self.output_callback(stderr_text),
                            asyncio.get_event_loop(),
                        )

                # Short sleep to prevent busy waiting
                if not self._stop_event.wait(0.01):
                    continue

            except Exception as e:
                if self._running:  # Only log if we're supposed to be running
                    logger.error(f"SSH output reading error: {e}")
                break

        logger.debug("SSH output reading loop ended")

    @property
    def is_connected(self) -> bool:
        """Check if SSH session is connected."""
        return self._connected and self.ssh_channel is not None

    @property
    def connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        return {
            "host": self.ssh_profile.host,
            "port": self.ssh_profile.port,
            "username": self.ssh_profile.username,
            "connected": self.is_connected,
            "server_info": self.server_info,
        }

    def get_terminal_size(self) -> tuple[int, int]:
        """Get current terminal size as (cols, rows)."""
        return (self.cols, self.rows)
