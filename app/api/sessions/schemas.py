"""
Pydantic schemas for terminal session management endpoints.

Contains request and response models for terminal sessions, session operations, and history.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, validator


class SessionType(str, Enum):
    """Terminal session types."""

    SSH = "ssh"
    LOCAL = "local"


class SessionStatus(str, Enum):
    """Terminal session status."""

    PENDING = "pending"
    CONNECTING = "connecting"
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    FAILED = "failed"
    TERMINATED = "terminated"


class SessionMode(str, Enum):
    """Terminal session mode."""

    INTERACTIVE = "interactive"
    BATCH = "batch"
    SCRIPT = "script"


# Terminal Session Schemas
class SessionBase(BaseModel):
    """Base schema for terminal session."""

    name: str = Field(..., min_length=1, max_length=100, description="Session name")
    session_type: SessionType = Field(..., description="Session type")
    description: str | None = Field(
        None, max_length=500, description="Session description"
    )

    # Session configuration
    mode: SessionMode = Field(
        default=SessionMode.INTERACTIVE, description="Session mode"
    )
    terminal_size: dict[str, int] | None = Field(
        default={"cols": 80, "rows": 24}, description="Terminal dimensions"
    )
    environment: dict[str, str] | None = Field(
        default=None, description="Environment variables"
    )
    working_directory: str | None = Field(
        None, max_length=1000, description="Initial working directory"
    )

    # Timeout settings
    idle_timeout: int = Field(
        default=1800, ge=60, le=86400, description="Idle timeout in seconds"
    )
    max_duration: int = Field(
        default=14400,
        ge=300,
        le=86400,
        description="Maximum session duration in seconds",
    )

    # Feature flags
    enable_logging: bool = Field(default=True, description="Enable session logging")
    enable_recording: bool = Field(
        default=False, description="Enable session recording"
    )
    auto_reconnect: bool = Field(
        default=True, description="Enable automatic reconnection"
    )


class SessionCreate(SessionBase):
    """Schema for creating terminal session."""

    ssh_profile_id: str | None = Field(
        None, description="SSH profile ID for SSH sessions"
    )
    connection_params: dict[str, Any] | None = Field(
        None, description="Additional connection parameters"
    )

    @validator("ssh_profile_id")
    def validate_ssh_session(cls, v: str | None, values: dict) -> str | None:
        """Validate SSH session requirements."""
        if values.get("session_type") == SessionType.SSH and not v:
            raise ValueError("SSH profile ID is required for SSH sessions")
        return v


class SessionUpdate(BaseModel):
    """Schema for updating terminal session."""

    name: str | None = Field(
        None, min_length=1, max_length=100, description="Session name"
    )
    description: str | None = Field(
        None, max_length=500, description="Session description"
    )

    # Configuration updates
    terminal_size: dict[str, int] | None = Field(
        None, description="Terminal dimensions"
    )
    environment: dict[str, str] | None = Field(
        None, description="Environment variables"
    )
    working_directory: str | None = Field(
        None, max_length=1000, description="Working directory"
    )

    # Timeout settings
    idle_timeout: int | None = Field(
        None, ge=60, le=86400, description="Idle timeout in seconds"
    )
    max_duration: int | None = Field(
        None, ge=300, le=86400, description="Maximum session duration"
    )

    # Feature flags
    enable_logging: bool | None = Field(
        default=None, description="Enable session logging"
    )
    enable_recording: bool | None = Field(None, description="Enable session recording")
    auto_reconnect: bool | None = Field(
        None, description="Enable automatic reconnection"
    )


class SessionResponse(SessionBase):
    """Schema for terminal session response."""

    id: str = Field(..., description="Session unique identifier")
    user_id: str = Field(..., description="Owner user ID")
    status: SessionStatus = Field(..., description="Current session status")

    # Connection details
    ssh_profile_id: str | None = Field(
        default=None, description="Associated SSH profile ID"
    )
    connection_info: dict[str, Any] | None = Field(
        None, description="Connection information"
    )

    # Session metrics
    start_time: datetime | None = Field(default=None, description="Session start time")
    end_time: datetime | None = Field(default=None, description="Session end time")
    last_activity: datetime | None = Field(None, description="Last activity timestamp")
    duration_seconds: int = Field(default=0, description="Total session duration")
    command_count: int = Field(default=0, description="Number of commands executed")

    # Status information
    error_message: str | None = Field(default=None, description="Last error message")
    exit_code: int | None = Field(default=None, description="Session exit code")
    pid: int | None = Field(default=None, description="Process ID for local sessions")

    # Metadata
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(..., description="Session active status")

    model_config = ConfigDict(from_attributes=True)


class SessionListResponse(BaseModel):
    """Schema for session list response."""

    sessions: list[SessionResponse]
    total: int
    offset: int
    limit: int


# Session Operation Schemas
class SessionCommand(BaseModel):
    """Schema for session command execution."""

    command: str = Field(
        ..., min_length=1, max_length=10000, description="Command to execute"
    )
    input_data: str | None = Field(default=None, description="Input data for command")
    timeout: int = Field(
        default=30, ge=1, le=300, description="Command timeout in seconds"
    )
    capture_output: bool = Field(default=True, description="Capture command output")
    working_directory: str | None = Field(None, description="Command working directory")


class SessionCommandResponse(BaseModel):
    """Schema for session command execution response."""

    command_id: str = Field(..., description="Command execution ID")
    command: str = Field(..., description="Executed command")
    status: str = Field(..., description="Command execution status")

    # Output
    stdout: str = Field(..., description="Standard output")
    stderr: str = Field(..., description="Standard error")
    exit_code: int = Field(..., description="Command exit code")

    # Timing
    start_time: datetime = Field(..., description="Command start time")
    end_time: datetime = Field(..., description="Command end time")
    duration_ms: int = Field(..., description="Execution duration in milliseconds")

    # Session context
    session_id: str = Field(..., description="Associated session ID")
    working_directory: str = Field(..., description="Command working directory")


# Session History Schemas
class SessionHistoryEntry(BaseModel):
    """Schema for session history entry."""

    id: str = Field(..., description="History entry ID")
    timestamp: datetime = Field(..., description="Entry timestamp")
    entry_type: str = Field(
        ..., description="Entry type: command, output, error, event"
    )
    content: str = Field(..., description="Entry content")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata"
    )


class SessionHistoryResponse(BaseModel):
    """Schema for session history response."""

    session_id: str = Field(..., description="Session ID")
    entries: list[SessionHistoryEntry] = Field(..., description="History entries")
    total_entries: int = Field(..., description="Total number of entries")
    start_time: datetime | None = Field(default=None, description="History start time")
    end_time: datetime | None = Field(default=None, description="History end time")


# Session Search and Filter Schemas
class SessionSearchRequest(BaseModel):
    """Schema for session search request."""

    search_term: str | None = Field(
        None, min_length=1, max_length=100, description="Search term"
    )
    session_type: SessionType | None = Field(None, description="Filter by session type")
    status: SessionStatus | None = Field(default=None, description="Filter by status")
    ssh_profile_id: str | None = Field(
        default=None, description="Filter by SSH profile"
    )

    # Date range filters
    created_after: datetime | None = Field(
        default=None, description="Created after date"
    )
    created_before: datetime | None = Field(
        default=None, description="Created before date"
    )
    active_after: datetime | None = Field(default=None, description="Active after date")

    # Sorting and pagination
    sort_by: str = Field(
        default="created_at",
        description="Sort field: created_at, last_activity, name, duration",
    )
    sort_order: str = Field(default="desc", description="Sort order: asc, desc")
    active_only: bool = Field(default=False, description="Show only active sessions")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    limit: int = Field(default=50, ge=1, le=100, description="Pagination limit")


# Session Statistics Schemas
class SessionStats(BaseModel):
    """Schema for session statistics."""

    total_sessions: int = Field(..., description="Total number of sessions")
    active_sessions: int = Field(..., description="Number of active sessions")
    sessions_by_type: dict[str, int] = Field(..., description="Session count by type")
    sessions_by_status: dict[str, int] = Field(
        ..., description="Session count by status"
    )

    # Usage metrics
    total_duration_hours: float = Field(
        ..., description="Total session duration in hours"
    )
    average_session_duration_minutes: float = Field(
        ..., description="Average session duration in minutes"
    )
    total_commands: int = Field(..., description="Total commands executed")
    average_commands_per_session: float = Field(
        ..., description="Average commands per session"
    )

    # Recent activity
    sessions_today: int = Field(..., description="Sessions started today")
    sessions_this_week: int = Field(..., description="Sessions started this week")
    most_used_profiles: list[dict[str, Any]] = Field(
        ..., description="Most used SSH profiles"
    )


# WebSocket Communication Schemas
class WSMessage(BaseModel):
    """Schema for WebSocket message."""

    type: str = Field(..., description="Message type")
    data: str | dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Message timestamp"
    )
    session_id: str | None = Field(default=None, description="Associated session ID")


class WSTerminalInput(BaseModel):
    """Schema for WebSocket terminal input."""

    type: str = Field(default="input", description="Message type")
    data: str = Field(..., description="Input data")
    session_id: str = Field(..., description="Session ID")


class WSTerminalOutput(BaseModel):
    """Schema for WebSocket terminal output."""

    type: str = Field(default="output", description="Message type")
    data: str = Field(..., description="Output data")
    session_id: str = Field(..., description="Session ID")
    stream: str = Field(default="stdout", description="Output stream: stdout, stderr")


class WSTerminalResize(BaseModel):
    """Schema for WebSocket terminal resize."""

    type: str = Field(default="resize", description="Message type")
    cols: int = Field(..., ge=1, le=500, description="Terminal columns")
    rows: int = Field(..., ge=1, le=200, description="Terminal rows")
    session_id: str = Field(..., description="Session ID")


class WSSessionEvent(BaseModel):
    """Schema for WebSocket session event."""

    type: str = Field(default="event", description="Message type")
    event: str = Field(
        ..., description="Event name: connected, disconnected, error, etc."
    )
    data: dict[str, Any] | None = Field(default=None, description="Event data")
    session_id: str = Field(..., description="Session ID")


# Session Recording Schemas
class SessionRecording(BaseModel):
    """Schema for session recording metadata."""

    id: str = Field(..., description="Recording ID")
    session_id: str = Field(..., description="Associated session ID")
    filename: str = Field(..., description="Recording filename")
    file_size: int = Field(..., description="Recording file size in bytes")
    duration_seconds: int = Field(..., description="Recording duration")
    format: str = Field(default="asciicast", description="Recording format")

    # Metadata
    created_at: datetime = Field(..., description="Recording creation time")
    updated_at: datetime = Field(..., description="Last update time")
    is_available: bool = Field(..., description="Recording availability status")


# Batch Operation Schemas
class BatchSessionOperation(BaseModel):
    """Schema for batch session operations."""

    session_ids: Annotated[
        list[str], Field(min_length=1, max_length=50, description="Session IDs")
    ]
    operation: str = Field(..., description="Operation: terminate, delete, archive")
    force: bool = Field(default=False, description="Force operation")


class BatchSessionResponse(BaseModel):
    """Schema for batch session operation response."""

    success_count: int = Field(..., description="Number of successful operations")
    error_count: int = Field(..., description="Number of failed operations")
    results: list[dict[str, Any]] = Field(
        ..., description="Operation results per session"
    )
    message: str = Field(..., description="Overall operation message")


# Session Template Schemas
class SessionTemplate(BaseModel):
    """Schema for session template."""

    name: str = Field(..., min_length=1, max_length=100, description="Template name")
    description: str | None = Field(
        None, max_length=500, description="Template description"
    )
    session_type: SessionType = Field(..., description="Session type")

    # Template configuration
    default_config: dict[str, Any] = Field(
        ..., description="Default session configuration"
    )
    ssh_profile_id: str | None = Field(
        default=None, description="Default SSH profile ID"
    )
    environment: dict[str, str] | None = Field(
        None, description="Default environment variables"
    )

    # Template metadata
    is_public: bool = Field(default=False, description="Template visibility")
    tags: list[str] = Field(default=[], description="Template tags")


class SessionTemplateResponse(SessionTemplate):
    """Schema for session template response."""

    id: str = Field(..., description="Template ID")
    user_id: str = Field(..., description="Template owner ID")
    usage_count: int = Field(default=0, description="Template usage count")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


# Error and Status Schemas
class SessionError(BaseModel):
    """Schema for session error information."""

    error_type: str = Field(..., description="Error type")
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(default=None, description="Error details")
    timestamp: datetime = Field(..., description="Error timestamp")
    session_id: str = Field(..., description="Associated session ID")


class SessionHealthCheck(BaseModel):
    """Schema for session health check."""

    session_id: str = Field(..., description="Session ID")
    is_healthy: bool = Field(..., description="Health status")
    status: SessionStatus = Field(..., description="Current status")
    last_activity: datetime | None = Field(default=None, description="Last activity")
    uptime_seconds: int = Field(..., description="Session uptime")
    connection_stable: bool = Field(..., description="Connection stability")
    response_time_ms: int | None = Field(
        None, description="Response time in milliseconds"
    )


# Common Response Schemas
class MessageResponse(BaseModel):
    """Schema for simple message responses."""

    message: str = Field(..., description="Response message")
    session_id: str | None = Field(default=None, description="Associated session ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
