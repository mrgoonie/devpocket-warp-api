"""
Session model for DevPocket API.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, ForeignKey, Integer, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel


class Session(BaseModel):
    """Session model representing user terminal sessions."""
    
    __tablename__ = "sessions"
    
    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Device information
    device_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    
    device_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )  # ios, android, web
    
    device_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    
    # Session metadata
    session_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    
    session_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="terminal",
        server_default="'terminal'"
    )  # terminal, ssh, pty
    
    # Connection information
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True
    )
    
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Session status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True
    )
    
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        index=True
    )
    
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True
    )
    
    # SSH connection details (if applicable)
    ssh_host: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    ssh_port: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    ssh_username: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    
    # Terminal configuration
    terminal_cols: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=80,
        server_default="80"
    )
    
    terminal_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=24,
        server_default="24"
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions"
    )
    
    commands: Mapped[List["Command"]] = relationship(
        "Command",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    
    # Session statistics
    @property
    def command_count(self) -> int:
        """Get the number of commands executed in this session."""
        return len(self.commands)
    
    @property
    def duration(self) -> Optional[int]:
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