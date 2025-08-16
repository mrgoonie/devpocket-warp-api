"""
Command model for DevPocket API.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID as PyUUID
from sqlalchemy import String, ForeignKey, Integer, Text, Float, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel


class Command(BaseModel):
    """Command model representing executed terminal commands."""

    __tablename__ = "commands"

    # Foreign key to session
    session_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Command details
    command: Mapped[str] = mapped_column(
        Text, nullable=False, index=True  # For command history searches
    )

    # Command execution results
    output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    error_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    exit_code: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True  # For filtering by success/failure
    )

    # Command status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="'pending'",
        index=True,
    )  # pending, running, success, error, cancelled, timeout

    # Execution timing
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    execution_time: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # Execution time in seconds

    # Command metadata
    working_directory: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )

    environment_vars: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string of environment variables

    # AI-related fields
    was_ai_suggested: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false", index=True
    )

    ai_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Command classification
    command_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )  # file_operation, network, system, git, etc.

    # Security flags
    is_sensitive: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )  # Commands containing passwords, keys, etc.

    # Relationships
    session: Mapped["Session"] = relationship(
        "Session", back_populates="commands"
    )

    # Computed properties
    @property
    def user_id(self) -> PyUUID:
        """Get user ID through session relationship."""
        return self.session.user_id if self.session else None

    @property
    def is_successful(self) -> bool:
        """Check if command executed successfully."""
        return self.exit_code == 0 and self.status == "success"

    @property
    def has_error(self) -> bool:
        """Check if command had an error."""
        return self.exit_code != 0 or self.status == "error"

    @property
    def duration_ms(self) -> Optional[int]:
        """Get execution duration in milliseconds."""
        if self.execution_time is not None:
            return int(self.execution_time * 1000)
        return None

    def start_execution(self) -> None:
        """Mark command as started."""
        self.status = "running"
        self.started_at = datetime.now()

    def complete_execution(
        self, exit_code: int, output: str = None, error_output: str = None
    ) -> None:
        """Mark command as completed with results."""
        self.completed_at = datetime.now()
        self.exit_code = exit_code
        self.output = output
        self.error_output = error_output

        # Set status based on exit code
        self.status = "success" if exit_code == 0 else "error"

        # Calculate execution time
        if self.started_at:
            duration = self.completed_at - self.started_at
            self.execution_time = duration.total_seconds()

    def cancel_execution(self) -> None:
        """Mark command as cancelled."""
        self.status = "cancelled"
        self.completed_at = datetime.now()

        if self.started_at:
            duration = self.completed_at - self.started_at
            self.execution_time = duration.total_seconds()

    def timeout_execution(self) -> None:
        """Mark command as timed out."""
        self.status = "timeout"
        self.completed_at = datetime.now()

        if self.started_at:
            duration = self.completed_at - self.started_at
            self.execution_time = duration.total_seconds()

    def classify_command(self) -> str:
        """Classify the command type based on the command string."""
        command_lower = self.command.lower().strip()

        # Git commands
        if command_lower.startswith(("git ", "gh ")):
            return "git"

        # File operations
        elif any(
            command_lower.startswith(cmd)
            for cmd in [
                "ls",
                "cd",
                "mkdir",
                "rmdir",
                "rm ",
                "cp ",
                "mv ",
                "find",
                "locate",
            ]
        ):
            return "file_operation"

        # Network commands
        elif any(
            command_lower.startswith(cmd)
            for cmd in [
                "ping",
                "curl",
                "wget",
                "ssh",
                "scp",
                "rsync",
                "netstat",
            ]
        ):
            return "network"

        # System commands
        elif any(
            command_lower.startswith(cmd)
            for cmd in [
                "ps",
                "top",
                "htop",
                "kill",
                "systemctl",
                "service",
                "df",
                "du",
                "mount",
                "umount",
            ]
        ):
            return "system"

        # Package management
        elif any(
            command_lower.startswith(cmd)
            for cmd in ["apt", "yum", "dnf", "pip", "npm", "yarn", "brew"]
        ):
            return "package_management"

        # Development
        elif any(
            command_lower.startswith(cmd)
            for cmd in [
                "docker",
                "kubectl",
                "make",
                "cmake",
                "gcc",
                "python",
                "node",
                "java",
            ]
        ):
            return "development"

        else:
            return "other"

    def check_sensitive_content(self) -> bool:
        """Check if command contains sensitive information."""
        command_lower = self.command.lower()
        sensitive_patterns = [
            "password",
            "passwd",
            "secret",
            "key",
            "token",
            "auth",
            "credential",
            "api_key",
            "private",
            "ssh-keygen",
        ]

        return any(pattern in command_lower for pattern in sensitive_patterns)

    def __repr__(self) -> str:
        return f"<Command(id={self.id}, session_id={self.session_id}, command='{self.command[:50]}...', status={self.status})>"


# Database indexes for performance optimization
Index("idx_commands_session_created", Command.session_id, Command.created_at)
Index("idx_commands_status_created", Command.status, Command.created_at)
Index(
    "idx_commands_user_command", Command.session_id, Command.command
)  # For command history by user
Index(
    "idx_commands_ai_suggested", Command.was_ai_suggested, Command.created_at
)  # For AI analytics
