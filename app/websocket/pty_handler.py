"""
PTY (Pseudo-Terminal) handler for DevPocket API.

Handles terminal emulation, PTY processes, and terminal I/O streaming.
"""

import asyncio
import os
import signal
import subprocess
from typing import Optional, Callable, Awaitable
import pty
import termios
import struct
import fcntl

from app.core.logging import logger


class PTYHandler:
    """
    Handles PTY (pseudo-terminal) operations for terminal emulation.

    This class manages a pseudo-terminal process that can execute commands
    with full terminal emulation support, including ANSI escape sequences,
    interactive applications, and proper signal handling.
    """

    def __init__(
        self,
        output_callback: Callable[[str], Awaitable[None]],
        rows: int = 24,
        cols: int = 80,
    ):
        """
        Initialize PTY handler.

        Args:
            output_callback: Async callback for terminal output
            rows: Terminal rows
            cols: Terminal columns
        """
        self.output_callback = output_callback
        self.rows = rows
        self.cols = cols

        # PTY file descriptors
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None

        # Process management
        self.process: Optional[subprocess.Popen] = None
        self.shell_pid: Optional[int] = None

        # Async tasks
        self._output_task: Optional[asyncio.Task] = None
        self._running = False

        # Buffer for output processing
        self._output_buffer = bytearray()
        self._max_buffer_size = 8192

    async def start(self, command: Optional[str] = None) -> bool:
        """
        Start the PTY session.

        Args:
            command: Optional command to execute (defaults to shell)

        Returns:
            True if started successfully, False otherwise
        """
        try:
            # Create PTY
            self.master_fd, self.slave_fd = pty.openpty()

            # Set terminal size
            self.resize_terminal(self.cols, self.rows)

            # Configure terminal settings
            self._configure_terminal()

            # Start shell or command
            shell_cmd = command or self._get_default_shell()

            # Fork process with PTY
            self.shell_pid = os.fork()

            if self.shell_pid == 0:
                # Child process
                self._setup_child_process(shell_cmd)
            else:
                # Parent process
                os.close(self.slave_fd)  # Close slave in parent
                self.slave_fd = None

                # Make master FD non-blocking
                fcntl.fcntl(self.master_fd, fcntl.F_SETFL, os.O_NONBLOCK)

                # Start output reading task
                self._running = True
                self._output_task = asyncio.create_task(self._read_output_loop())

                logger.info(
                    f"PTY session started: pid={self.shell_pid}, size={self.cols}x{self.rows}"
                )
                return True

        except Exception as e:
            logger.error(f"Failed to start PTY session: {e}")
            await self.stop()
            return False

    async def stop(self) -> None:
        """Stop the PTY session and clean up resources."""
        self._running = False

        # Cancel output task
        if self._output_task and not self._output_task.done():
            self._output_task.cancel()
            try:
                await self._output_task
            except asyncio.CancelledError:
                pass

        # Terminate shell process
        if self.shell_pid:
            try:
                os.kill(self.shell_pid, signal.SIGTERM)
                # Wait for process to terminate
                try:
                    os.waitpid(self.shell_pid, 0)
                except ChildProcessError:
                    pass  # Process already terminated
            except ProcessLookupError:
                pass  # Process doesn't exist
            self.shell_pid = None

        # Close file descriptors
        if self.master_fd:
            os.close(self.master_fd)
            self.master_fd = None

        if self.slave_fd:
            os.close(self.slave_fd)
            self.slave_fd = None

        logger.info("PTY session stopped")

    async def write_input(self, data: str) -> bool:
        """
        Write input to the PTY.

        Args:
            data: Input data to write

        Returns:
            True if written successfully, False otherwise
        """
        if not self.master_fd or not self._running:
            return False

        try:
            # Convert string to bytes
            input_bytes = data.encode("utf-8")

            # Write to PTY master
            bytes_written = os.write(self.master_fd, input_bytes)

            if bytes_written != len(input_bytes):
                logger.warning(
                    f"Partial write: {bytes_written}/{len(input_bytes)} bytes"
                )

            return True

        except (OSError, IOError) as e:
            logger.error(f"Failed to write to PTY: {e}")
            return False

    def resize_terminal(self, cols: int, rows: int) -> bool:
        """
        Resize the terminal.

        Args:
            cols: Terminal columns
            rows: Terminal rows

        Returns:
            True if resized successfully, False otherwise
        """
        try:
            self.cols = cols
            self.rows = rows

            if self.master_fd:
                # Set terminal window size
                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)

                # Send SIGWINCH to shell process
                if self.shell_pid:
                    os.kill(self.shell_pid, signal.SIGWINCH)

            logger.debug(f"Terminal resized to {cols}x{rows}")
            return True

        except Exception as e:
            logger.error(f"Failed to resize terminal: {e}")
            return False

    def send_signal(self, sig: str) -> bool:
        """
        Send a signal to the shell process.

        Args:
            sig: Signal name (e.g., 'SIGINT', 'SIGTERM')

        Returns:
            True if signal sent successfully, False otherwise
        """
        if not self.shell_pid:
            return False

        try:
            # Map signal names to signal numbers
            signal_map = {
                "SIGINT": signal.SIGINT,  # Ctrl+C
                "SIGQUIT": signal.SIGQUIT,  # Ctrl+\
                "SIGTERM": signal.SIGTERM,  # Terminate
                "SIGKILL": signal.SIGKILL,  # Kill
                "SIGSTOP": signal.SIGSTOP,  # Ctrl+Z
                "SIGCONT": signal.SIGCONT,  # Continue
            }

            signal_num = signal_map.get(sig.upper())
            if signal_num is None:
                logger.warning(f"Unknown signal: {sig}")
                return False

            os.kill(self.shell_pid, signal_num)
            logger.debug(f"Sent {sig} to process {self.shell_pid}")
            return True

        except ProcessLookupError:
            logger.warning(f"Process {self.shell_pid} not found for signal {sig}")
            return False
        except Exception as e:
            logger.error(f"Failed to send signal {sig}: {e}")
            return False

    def _setup_child_process(self, command: str) -> None:
        """Set up the child process environment."""
        try:
            # Close master FD in child
            if self.master_fd:
                os.close(self.master_fd)

            # Make slave FD the controlling terminal
            os.setsid()
            fcntl.ioctl(self.slave_fd, termios.TIOCSCTTY, 0)

            # Redirect stdin, stdout, stderr to slave
            os.dup2(self.slave_fd, 0)  # stdin
            os.dup2(self.slave_fd, 1)  # stdout
            os.dup2(self.slave_fd, 2)  # stderr

            # Close slave FD after duplication
            if self.slave_fd > 2:
                os.close(self.slave_fd)

            # Set environment variables
            os.environ["TERM"] = "xterm-256color"
            os.environ["COLUMNS"] = str(self.cols)
            os.environ["LINES"] = str(self.rows)

            # Execute command
            if command.strip():
                # Execute specific command
                os.execve("/bin/sh", ["/bin/sh", "-c", command], os.environ)
            else:
                # Execute shell
                shell = self._get_default_shell()
                os.execve(shell, [shell, "-l"], os.environ)

        except Exception as e:
            logger.error(f"Failed to setup child process: {e}")
            os._exit(1)

    def _configure_terminal(self) -> None:
        """Configure terminal settings for optimal behavior."""
        try:
            if self.slave_fd:
                # Get current terminal attributes
                attrs = termios.tcgetattr(self.slave_fd)

                # Configure input modes
                attrs[0] &= ~(
                    termios.IGNBRK
                    | termios.BRKINT
                    | termios.PARMRK
                    | termios.ISTRIP
                    | termios.INLCR
                    | termios.IGNCR
                    | termios.ICRNL
                    | termios.IXON
                )
                attrs[0] |= termios.IGNPAR

                # Configure output modes
                attrs[1] &= ~termios.OPOST

                # Configure local modes
                attrs[3] &= ~(
                    termios.ECHO
                    | termios.ECHONL
                    | termios.ICANON
                    | termios.ISIG
                    | termios.IEXTEN
                )
                attrs[3] |= termios.ECHOCTL | termios.ECHOKE

                # Configure control characters
                attrs[6][termios.VMIN] = 1
                attrs[6][termios.VTIME] = 0

                # Apply settings
                termios.tcsetattr(self.slave_fd, termios.TCSANOW, attrs)

        except Exception as e:
            logger.warning(f"Failed to configure terminal settings: {e}")

    async def _read_output_loop(self) -> None:
        """Continuously read output from PTY and send to callback."""
        while self._running and self.master_fd:
            try:
                # Use asyncio to make the blocking read non-blocking
                loop = asyncio.get_event_loop()

                try:
                    # Read data from PTY (non-blocking)
                    data = await loop.run_in_executor(None, self._read_master_fd)

                    if data:
                        # Process and send output
                        await self._process_output(data)
                    else:
                        # No data available, short wait
                        await asyncio.sleep(0.01)

                except (OSError, IOError) as e:
                    if e.errno == 5:  # EIO - process ended
                        logger.info("PTY process ended")
                        break
                    else:
                        logger.error(f"PTY read error: {e}")
                        break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in output loop: {e}")
                break

        self._running = False

    def _read_master_fd(self) -> Optional[bytes]:
        """Read data from master FD (blocking operation for executor)."""
        try:
            return os.read(self.master_fd, 1024)
        except (OSError, IOError) as e:
            if e.errno == 11:  # EAGAIN - no data available
                return None
            else:
                raise

    async def _process_output(self, data: bytes) -> None:
        """Process raw output data and send to callback."""
        try:
            # Add to buffer
            self._output_buffer.extend(data)

            # Prevent buffer from growing too large
            if len(self._output_buffer) > self._max_buffer_size:
                # Keep only the last portion of the buffer
                excess = len(self._output_buffer) - self._max_buffer_size
                self._output_buffer = self._output_buffer[excess:]

            # Decode and send output
            try:
                output_text = data.decode("utf-8", errors="replace")
                await self.output_callback(output_text)
            except Exception as e:
                logger.error(f"Failed to send output via callback: {e}")

        except Exception as e:
            logger.error(f"Failed to process output: {e}")

    def _get_default_shell(self) -> str:
        """Get the default shell for the user."""
        # Try to get user's shell from environment or passwd
        shell = os.environ.get("SHELL")
        if shell and os.path.exists(shell):
            return shell

        # Fallback shells
        fallback_shells = ["/bin/bash", "/bin/sh", "/bin/zsh"]
        for shell in fallback_shells:
            if os.path.exists(shell):
                return shell

        # Ultimate fallback
        return "/bin/sh"

    @property
    def is_running(self) -> bool:
        """Check if PTY session is running."""
        return self._running and self.master_fd is not None

    def get_terminal_size(self) -> tuple[int, int]:
        """Get current terminal size as (cols, rows)."""
        return (self.cols, self.rows)
