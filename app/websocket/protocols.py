"""
WebSocket message protocols and data structures.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, Union
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
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Optional[Union[str, Dict[str, Any]]] = None

    class Config:
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}


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
    data: Dict[str, int] = Field(
        description="Terminal dimensions", example={"rows": 24, "cols": 80}
    )

    @property
    def rows(self) -> int:
        """Get terminal rows."""
        return self.data.get("rows", 24)

    @property
    def cols(self) -> int:
        """Get terminal columns."""
        return self.data.get("cols", 80)


class SignalMessage(TerminalMessage):
    """Terminal signal message (Ctrl+C, etc.)."""

    type: MessageType = MessageType.SIGNAL
    session_id: str
    data: Dict[str, str] = Field(
        description="Signal information", example={"signal": "SIGINT", "key": "ctrl+c"}
    )

    @property
    def signal(self) -> str:
        """Get signal name."""
        return self.data.get("signal", "")

    @property
    def key(self) -> str:
        """Get key combination."""
        return self.data.get("key", "")


class ConnectMessage(TerminalMessage):
    """Session connect message."""

    type: MessageType = MessageType.CONNECT
    data: Dict[str, Any] = Field(
        description="Connection parameters",
        example={
            "session_type": "ssh",
            "ssh_profile_id": "uuid",
            "terminal_size": {"rows": 24, "cols": 80},
        },
    )

    @property
    def session_type(self) -> str:
        """Get session type."""
        return self.data.get("session_type", "terminal")

    @property
    def ssh_profile_id(self) -> Optional[str]:
        """Get SSH profile ID if applicable."""
        return self.data.get("ssh_profile_id")

    @property
    def terminal_size(self) -> Dict[str, int]:
        """Get terminal size."""
        return self.data.get("terminal_size", {"rows": 24, "cols": 80})


class StatusMessage(TerminalMessage):
    """Session status message."""

    type: MessageType = MessageType.STATUS
    session_id: str
    data: Dict[str, Any] = Field(
        description="Status information",
        example={
            "status": "connected",
            "message": "SSH connection established",
            "server_info": {"version": "OpenSSH_8.0"},
        },
    )

    @property
    def status(self) -> str:
        """Get status."""
        return self.data.get("status", "unknown")

    @property
    def message(self) -> str:
        """Get status message."""
        return self.data.get("message", "")

    @property
    def server_info(self) -> Dict[str, Any]:
        """Get server information."""
        return self.data.get("server_info", {})


class ErrorMessage(TerminalMessage):
    """Error message."""

    type: MessageType = MessageType.ERROR
    data: Dict[str, Any] = Field(
        description="Error information",
        example={
            "error": "connection_failed",
            "message": "SSH connection failed",
            "details": {"host": "example.com", "port": 22},
        },
    )

    @property
    def error(self) -> str:
        """Get error code."""
        return self.data.get("error", "unknown_error")

    @property
    def message(self) -> str:
        """Get error message."""
        return self.data.get("message", "")

    @property
    def details(self) -> Dict[str, Any]:
        """Get error details."""
        return self.data.get("details", {})


class HeartbeatMessage(TerminalMessage):
    """Heartbeat message for connection health."""

    type: MessageType = MessageType.PING
    data: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional heartbeat data"
    )


def parse_message(data: Dict[str, Any]) -> TerminalMessage:
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
        raise ValueError(f"Invalid message type: {data.get('type')}")

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
        return message_class(**data)
    except Exception as e:
        raise ValueError(f"Invalid message format for {message_type}: {str(e)}")


def create_output_message(session_id: str, data: str) -> OutputMessage:
    """Create an output message for terminal data."""
    return OutputMessage(session_id=session_id, data=data)


def create_status_message(
    session_id: str,
    status: str,
    message: str = "",
    server_info: Optional[Dict[str, Any]] = None,
) -> StatusMessage:
    """Create a status message."""
    return StatusMessage(
        session_id=session_id,
        data={"status": status, "message": message, "server_info": server_info or {}},
    )


def create_error_message(
    error: str,
    message: str = "",
    details: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> ErrorMessage:
    """Create an error message."""
    return ErrorMessage(
        session_id=session_id,
        data={"error": error, "message": message, "details": details or {}},
    )
