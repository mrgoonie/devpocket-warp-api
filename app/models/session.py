"""
Session model for DevPocket API.
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID as PyUUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .command import Command
    from .user import User


class Session(BaseModel):
    """Session model representing user terminal sessions."""

    __tablename__ = "sessions"

    # Foreign key to user
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Device information
    device_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    device_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # ios, android, web

    device_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Session metadata
    session_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Alias for compatibility with services expecting 'name'
    @property
    def name(self) -> str | None:
        """Get session name (alias for session_name)."""
        return self.session_name

    @name.setter
    def name(self, value: str | None) -> None:
        """Set session name (alias for session_name)."""
        self.session_name = value

    session_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="terminal",
        server_default="'terminal'",
    )  # terminal, ssh, pty

    # Connection information
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True  # IPv6 max length
    )

    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Session status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )

    # Session status string (computed from is_active and other fields)
    @property
    def status(self) -> str:
        """Get session status as string."""
        if not self.is_active:
            return "terminated"
        elif self.ssh_host and not hasattr(self, "_ssh_connected"):
            return "connecting"
        else:
            return "active"

    @status.setter
    def status(self, value: str) -> None:
        """Set session status."""
        if value == "terminated":
            self.is_active = False
            if not self.ended_at:
                self.ended_at = datetime.now()
        elif value == "active":
            self.is_active = True
        # For other statuses like "connecting", we just store internally

    last_activity_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)

    # Alias for compatibility with services expecting 'last_activity'
    @property
    def last_activity(self) -> datetime | None:
        """Get last activity timestamp (alias for last_activity_at)."""
        return self.last_activity_at

    @last_activity.setter
    def last_activity(self, value: datetime | None) -> None:
        """Set last activity timestamp (alias for last_activity_at)."""
        self.last_activity_at = value

    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Session timing
    @property
    def start_time(self) -> datetime:
        """Get session start time (alias for created_at)."""
        return self.created_at

    @property
    def end_time(self) -> datetime | None:
        """Get session end time (alias for ended_at)."""
        return self.ended_at

    @end_time.setter
    def end_time(self, value: datetime | None) -> None:
        """Set session end time (alias for ended_at)."""
        self.ended_at = value

    @property
    def duration_seconds(self) -> int | None:
        """Get session duration in seconds."""
        if not self.ended_at:
            return None
        return int((self.ended_at - self.created_at).total_seconds())

    @duration_seconds.setter
    def duration_seconds(self, value: int | None) -> None:
        """Set session duration in seconds (computed field, setter for compatibility)."""
        # This is computed from start/end times, but we provide setter for compatibility
        if value is not None and not self.ended_at:
            self.ended_at = self.created_at + timedelta(seconds=value)

    # SSH connection details (if applicable)
    ssh_host: Mapped[str | None] = mapped_column(String(255), nullable=True)

    ssh_port: Mapped[int | None] = mapped_column(Integer, nullable=True)

    ssh_username: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Terminal configuration
    terminal_cols: Mapped[int] = mapped_column(
        Integer, nullable=False, default=80, server_default="80"
    )

    terminal_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=24, server_default="24"
    )

    # Environment variables (JSON string)
    environment: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON string of environment variables

    # Session error information
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    commands: Mapped[list["Command"]] = relationship(
        "Command", back_populates="session", cascade="all, delete-orphan"
    )

    # Session statistics
    @property
    def command_count(self) -> int:
        """Get the number of commands executed in this session."""
        return len(self.commands)

    @property
    def duration(self) -> int | None:
        """Get session duration in seconds."""
        if not self.ended_at:
            return None
        return int((self.ended_at - self.created_at).total_seconds())

    def is_ssh_session(self) -> bool:
        """Check if this is an SSH session."""
        return self.ssh_host is not None

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity_at = datetime.now()

    def end_session(self) -> None:
        """End the session."""
        self.is_active = False
        self.ended_at = datetime.now()

    def resize_terminal(self, cols: int, rows: int) -> None:
        """Update terminal dimensions."""
        self.terminal_cols = cols
        self.terminal_rows = rows
        self.update_activity()

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, user_id={self.user_id}, device_type={self.device_type}, active={self.is_active})>"
