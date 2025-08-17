"""
WebSocket message protocols and data structures.
"""

from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Union, cast

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """WebSocket message types."""

    # Terminal I/O
    INPUT = "input"
    OUTPUT = "output"

    # Control messages
    RESIZE = "resize"
    SIGNAL = "signal"

    # Session management
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    STATUS = "status"

    # Error handling
    ERROR = "error"

    # Heartbeat
    PING = "ping"
    PONG = "pong"


class TerminalMessage(BaseModel):
    """Base WebSocket terminal message."""

    type: MessageType
    session_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    data: str | dict[str, Any] | None = None

    class Config:
        use_enum_values = True
        json_encoders: ClassVar[dict] = {datetime: lambda v: v.isoformat()}


class InputMessage(TerminalMessage):
    """Terminal input message from client."""

    type: MessageType = MessageType.INPUT
    data: str
    session_id: str


class OutputMessage(TerminalMessage):
    """Terminal output message to client."""

    type: MessageType = MessageType.OUTPUT
    data: str
    session_id: str


class ResizeMessage(TerminalMessage):
    """Terminal resize message."""

    type: MessageType = MessageType.RESIZE
    session_id: str
    data: dict[str, int] = Field(
        description="Terminal dimensions", examples=[{"rows": 24, "cols": 80}]
    )

    @property
    def rows(self) -> int:
        """Get terminal rows."""
        return int(self.data.get("rows", 24))

    @property
    def cols(self) -> int:
        """Get terminal columns."""
        return int(self.data.get("cols", 80))


class SignalMessage(TerminalMessage):
    """Terminal signal message (Ctrl+C, etc.)."""

    type: MessageType = MessageType.SIGNAL
    session_id: str
    data: dict[str, str] = Field(
        description="Signal information",
        examples=[{"signal": "SIGINT", "key": "ctrl+c"}],
    )

    @property
    def signal(self) -> str:
        """Get signal name."""
        return str(self.data.get("signal", ""))

    @property
    def key(self) -> str:
        """Get key combination."""
        return str(self.data.get("key", ""))


class ConnectMessage(TerminalMessage):
    """Session connect message."""

    type: MessageType = MessageType.CONNECT
    data: dict[str, Any] = Field(
        description="Connection parameters",
        examples=[
            {
                "session_type": "ssh",
                "ssh_profile_id": "uuid",
                "terminal_size": {"rows": 24, "cols": 80},
            }
        ],
    )

    @property
    def session_type(self) -> str:
        """Get session type."""
        return str(self.data.get("session_type", "terminal"))

    @property
    def ssh_profile_id(self) -> str | None:
        """Get SSH profile ID if applicable."""
        return self.data.get("ssh_profile_id")

    @property
    def terminal_size(self) -> dict[str, int]:
        """Get terminal size."""
        result = self.data.get("terminal_size", {"rows": 24, "cols": 80})
        return dict(result) if isinstance(result, dict) else {"rows": 24, "cols": 80}


class StatusMessage(TerminalMessage):
    """Session status message."""

    type: MessageType = MessageType.STATUS
    session_id: str
    data: dict[str, Any] = Field(
        description="Status information",
        examples=[
            {
                "status": "connected",
                "message": "SSH connection established",
                "server_info": {"version": "OpenSSH_8.0"},
            }
        ],
    )

    @property
    def status(self) -> str:
        """Get status."""
        return str(self.data.get("status", "unknown"))

    @property
    def message(self) -> str:
        """Get status message."""
        return str(self.data.get("message", ""))

    @property
    def server_info(self) -> dict[str, Any]:
        """Get server information."""
        result = self.data.get("server_info", {})
        return dict(result) if isinstance(result, dict) else {}


class ErrorMessage(TerminalMessage):
    """Error message."""

    type: MessageType = MessageType.ERROR
    data: dict[str, Any] = Field(
        description="Error information",
        examples=[
            {
                "error": "connection_failed",
                "message": "SSH connection failed",
                "details": {"host": "example.com", "port": 22},
            }
        ],
    )

    @property
    def error(self) -> str:
        """Get error code."""
        return str(self.data.get("error", "unknown_error"))

    @property
    def message(self) -> str:
        """Get error message."""
        return str(self.data.get("message", ""))

    @property
    def details(self) -> dict[str, Any]:
        """Get error details."""
        result = self.data.get("details", {})
        return dict(result) if isinstance(result, dict) else {}


class HeartbeatMessage(TerminalMessage):
    """Heartbeat message for connection health."""

    type: MessageType = MessageType.PING
    data: dict[str, Any] | None = Field(
        default=None, description="Optional heartbeat data"
    )


# Type alias for any parsed message
ParsedMessage = Union[
    InputMessage,
    OutputMessage,
    ResizeMessage,
    SignalMessage,
    ConnectMessage,
    StatusMessage,
    ErrorMessage,
    HeartbeatMessage,
    TerminalMessage,
]


def parse_message(data: dict[str, Any]) -> ParsedMessage:
    """
    Parse incoming WebSocket message into appropriate message type.

    Args:
        data: Raw message data

    Returns:
        Parsed terminal message

    Raises:
        ValueError: If message type is invalid or required fields are missing
    """
    try:
        message_type = MessageType(data.get("type"))
    except ValueError:
        raise ValueError(f"Invalid message type: {data.get('type')}") from None

    # Map message types to their specific classes
    message_classes = {
        MessageType.INPUT: InputMessage,
        MessageType.OUTPUT: OutputMessage,
        MessageType.RESIZE: ResizeMessage,
        MessageType.SIGNAL: SignalMessage,
        MessageType.CONNECT: ConnectMessage,
        MessageType.STATUS: StatusMessage,
        MessageType.ERROR: ErrorMessage,
        MessageType.PING: HeartbeatMessage,
        MessageType.PONG: HeartbeatMessage,
        MessageType.DISCONNECT: TerminalMessage,
    }

    message_class = message_classes.get(message_type, TerminalMessage)

    try:
        result = message_class(**data)
        return cast(ParsedMessage, result)
    except Exception as e:
        raise ValueError(f"Invalid message format for {message_type}: {e!s}") from e


def create_output_message(session_id: str, data: str) -> OutputMessage:
    """Create an output message for terminal data."""
    return OutputMessage(session_id=session_id, data=data)


def create_status_message(
    session_id: str,
    status: str,
    message: str = "",
    server_info: dict[str, Any] | None = None,
) -> StatusMessage:
    """Create a status message."""
    return StatusMessage(
        session_id=session_id,
        data={
            "status": status,
            "message": message,
            "server_info": server_info or {},
        },
    )


def create_error_message(
    error: str,
    message: str = "",
    details: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> ErrorMessage:
    """Create an error message."""
    return ErrorMessage(
        session_id=session_id,
        data={"error": error, "message": message, "details": details or {}},
    )
