"""
Pydantic schemas for command management endpoints.

Contains request and response models for command history, analytics, and search operations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class MessageResponse(BaseModel):
    """Generic message response schema."""

    message: str = Field(..., description="Response message")


class CommandStatus(str, Enum):
    """Command execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class CommandType(str, Enum):
    """Command type classification."""

    SYSTEM = "system"
    FILE = "file"
    NETWORK = "network"
    PROCESS = "process"
    TEXT = "text"
    GIT = "git"
    PACKAGE = "package"
    DATABASE = "database"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class OutputFormat(str, Enum):
    """Command output format."""

    TEXT = "text"
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    TABLE = "table"


# Command Base Schemas
class CommandBase(BaseModel):
    """Base schema for command."""

    command: str = Field(
        ..., min_length=1, max_length=10000, description="Command text"
    )
    working_directory: Optional[str] = Field(
        None, max_length=1000, description="Working directory"
    )
    environment: Optional[Dict[str, str]] = Field(
        None, description="Environment variables"
    )
    timeout_seconds: int = Field(
        default=30, ge=1, le=3600, description="Command timeout"
    )
    capture_output: bool = Field(default=True, description="Capture output")


class CommandExecute(CommandBase):
    """Schema for executing command."""

    session_id: str = Field(..., description="Terminal session ID")
    input_data: Optional[str] = Field(None, description="Input data for command")
    async_execution: bool = Field(default=False, description="Execute asynchronously")


class CommandResponse(CommandBase):
    """Schema for command response."""

    id: str = Field(..., description="Command unique identifier")
    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")

    # Execution details
    status: CommandStatus = Field(..., description="Command status")
    exit_code: Optional[int] = Field(None, description="Exit code")

    # Output
    stdout: str = Field(default="", description="Standard output")
    stderr: str = Field(default="", description="Standard error")
    output_truncated: bool = Field(default=False, description="Output truncated flag")
    output_size: int = Field(default=0, description="Total output size in bytes")

    # Timing
    executed_at: datetime = Field(..., description="Execution timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    duration_ms: int = Field(
        default=0, description="Execution duration in milliseconds"
    )

    # Classification
    command_type: CommandType = Field(
        default=CommandType.UNKNOWN, description="Command type"
    )
    is_dangerous: bool = Field(
        default=False, description="Potentially dangerous command flag"
    )

    # Metadata
    pid: Optional[int] = Field(None, description="Process ID")
    signal: Optional[int] = Field(
        None, description="Signal that terminated the process"
    )

    # History context
    sequence_number: int = Field(default=0, description="Sequence in session")
    parent_command_id: Optional[str] = Field(
        None, description="Parent command ID for pipes/chains"
    )

    model_config = ConfigDict(from_attributes=True)


class CommandListResponse(BaseModel):
    """Schema for command list response."""

    commands: List[CommandResponse]
    total: int
    offset: int
    limit: int
    session_id: Optional[str] = None


# Command History Schemas
class CommandHistoryEntry(BaseModel):
    """Schema for command history entry with additional context."""

    id: str = Field(..., description="Command ID")
    command: str = Field(..., description="Command text")
    working_directory: str = Field(..., description="Working directory")
    status: CommandStatus = Field(..., description="Status")
    exit_code: Optional[int] = Field(None, description="Exit code")
    executed_at: datetime = Field(..., description="Execution time")
    duration_ms: int = Field(..., description="Duration in milliseconds")

    # Session context
    session_id: str = Field(..., description="Session ID")
    session_name: str = Field(..., description="Session name")
    session_type: str = Field(..., description="Session type")

    # Classification
    command_type: CommandType = Field(..., description="Command type")
    is_dangerous: bool = Field(..., description="Dangerous command flag")

    # Output summary
    output_size: int = Field(..., description="Output size")
    has_output: bool = Field(..., description="Has output")
    has_error: bool = Field(..., description="Has error output")


class CommandHistoryResponse(BaseModel):
    """Schema for command history response."""

    entries: List[CommandHistoryEntry]
    total: int
    offset: int
    limit: int
    filters_applied: Optional[Dict[str, Any]] = None


# Command Search Schemas
class CommandSearchRequest(BaseModel):
    """Schema for command search request."""

    query: Optional[str] = Field(
        None, min_length=1, max_length=500, description="Search query"
    )

    # Filters
    session_id: Optional[str] = Field(None, description="Filter by session ID")
    command_type: Optional[CommandType] = Field(
        None, description="Filter by command type"
    )
    status: Optional[CommandStatus] = Field(None, description="Filter by status")
    exit_code: Optional[int] = Field(None, description="Filter by exit code")

    # Date range
    executed_after: Optional[datetime] = Field(None, description="Executed after date")
    executed_before: Optional[datetime] = Field(
        None, description="Executed before date"
    )

    # Duration filters
    min_duration_ms: Optional[int] = Field(
        None, ge=0, description="Minimum duration filter"
    )
    max_duration_ms: Optional[int] = Field(
        None, ge=0, description="Maximum duration filter"
    )

    # Output filters
    has_output: Optional[bool] = Field(None, description="Has stdout output")
    has_error: Optional[bool] = Field(None, description="Has stderr output")
    output_contains: Optional[str] = Field(None, description="Output contains text")

    # Working directory filter
    working_directory: Optional[str] = Field(
        None, description="Filter by working directory"
    )

    # Dangerous commands filter
    include_dangerous: bool = Field(
        default=True, description="Include dangerous commands"
    )
    only_dangerous: bool = Field(default=False, description="Only dangerous commands")

    # Sorting and pagination
    sort_by: str = Field(default="executed_at", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order: asc, desc")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    limit: int = Field(default=50, ge=1, le=500, description="Pagination limit")


# Command Analytics Schemas
class CommandUsageStats(BaseModel):
    """Schema for command usage statistics."""

    total_commands: int = Field(..., description="Total commands executed")
    unique_commands: int = Field(..., description="Unique commands executed")
    successful_commands: int = Field(..., description="Successful commands")
    failed_commands: int = Field(..., description="Failed commands")

    # Performance metrics
    average_duration_ms: float = Field(..., description="Average execution duration")
    median_duration_ms: float = Field(..., description="Median execution duration")
    total_execution_time_ms: int = Field(..., description="Total execution time")

    # Command type breakdown
    commands_by_type: Dict[str, int] = Field(..., description="Commands by type")
    commands_by_status: Dict[str, int] = Field(..., description="Commands by status")

    # Time-based metrics
    commands_today: int = Field(..., description="Commands executed today")
    commands_this_week: int = Field(..., description="Commands executed this week")
    commands_this_month: int = Field(..., description="Commands executed this month")

    # Top commands
    most_used_commands: List[Dict[str, Any]] = Field(
        ..., description="Most frequently used commands"
    )
    longest_running_commands: List[Dict[str, Any]] = Field(
        ..., description="Longest running commands"
    )


class SessionCommandStats(BaseModel):
    """Schema for session-specific command statistics."""

    session_id: str = Field(..., description="Session ID")
    session_name: str = Field(..., description="Session name")
    total_commands: int = Field(..., description="Total commands in session")
    successful_commands: int = Field(..., description="Successful commands")
    failed_commands: int = Field(..., description="Failed commands")
    average_duration_ms: float = Field(..., description="Average command duration")
    last_command_at: Optional[datetime] = Field(
        None, description="Last command timestamp"
    )
    most_used_command: Optional[str] = Field(None, description="Most used command")


class CommandTypeStats(BaseModel):
    """Schema for command type statistics."""

    command_type: CommandType = Field(..., description="Command type")
    count: int = Field(..., description="Number of commands")
    success_rate: float = Field(..., description="Success rate percentage")
    average_duration_ms: float = Field(..., description="Average duration")
    examples: List[str] = Field(..., description="Example commands")


# Frequent Commands Schemas
class FrequentCommand(BaseModel):
    """Schema for frequently used command."""

    command_template: str = Field(..., description="Command template/pattern")
    usage_count: int = Field(..., description="Usage count")
    last_used: datetime = Field(..., description="Last used timestamp")
    success_rate: float = Field(..., description="Success rate")
    average_duration_ms: float = Field(..., description="Average duration")
    variations: List[str] = Field(..., description="Command variations")
    sessions_used: int = Field(..., description="Number of sessions used in")
    command_type: CommandType = Field(..., description="Command type")


class FrequentCommandsResponse(BaseModel):
    """Schema for frequent commands response."""

    commands: List[FrequentCommand]
    total_analyzed: int = Field(..., description="Total commands analyzed")
    analysis_period_days: int = Field(..., description="Analysis period in days")
    generated_at: datetime = Field(..., description="Analysis generation timestamp")


# Command Suggestions Schemas
class CommandSuggestion(BaseModel):
    """Schema for command suggestion."""

    command: str = Field(..., description="Suggested command")
    description: str = Field(..., description="Command description")
    confidence: float = Field(..., ge=0, le=1, description="Suggestion confidence")
    category: CommandType = Field(..., description="Command category")

    # Context
    relevant_context: Optional[str] = Field(None, description="Relevant context")
    prerequisites: List[str] = Field(default=[], description="Prerequisites")
    examples: List[str] = Field(default=[], description="Usage examples")

    # Safety
    is_safe: bool = Field(default=True, description="Safe to execute")
    warnings: List[str] = Field(default=[], description="Safety warnings")


class CommandSuggestionRequest(BaseModel):
    """Schema for command suggestion request."""

    context: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Context or description",
    )
    session_id: Optional[str] = Field(None, description="Session context")
    working_directory: Optional[str] = Field(
        None, description="Current working directory"
    )
    previous_commands: Optional[List[str]] = Field(
        None, max_items=10, description="Recent commands"
    )
    preferred_tools: Optional[List[str]] = Field(
        None, description="Preferred tools/utilities"
    )
    max_suggestions: int = Field(
        default=5, ge=1, le=20, description="Maximum suggestions"
    )


# Command Templates Schemas
class CommandTemplate(BaseModel):
    """Schema for command template."""

    name: str = Field(..., min_length=1, max_length=100, description="Template name")
    description: str = Field(..., max_length=500, description="Template description")
    command_template: str = Field(..., description="Command template with placeholders")
    category: CommandType = Field(..., description="Command category")

    # Template parameters
    parameters: Dict[str, Dict[str, Any]] = Field(
        ..., description="Template parameters with validation"
    )

    # Usage info
    usage_examples: List[str] = Field(default=[], description="Usage examples")
    tags: List[str] = Field(default=[], description="Template tags")
    is_public: bool = Field(default=False, description="Public template")


class CommandTemplateResponse(CommandTemplate):
    """Schema for command template response."""

    id: str = Field(..., description="Template ID")
    user_id: str = Field(..., description="Template owner")
    usage_count: int = Field(default=0, description="Usage count")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")

    model_config = ConfigDict(from_attributes=True)


# Export and Import Schemas
class CommandExportRequest(BaseModel):
    """Schema for command export request."""

    session_ids: Optional[List[str]] = Field(
        None, description="Specific sessions to export"
    )
    date_from: Optional[datetime] = Field(None, description="Export from date")
    date_to: Optional[datetime] = Field(None, description="Export to date")
    include_output: bool = Field(default=False, description="Include command output")
    include_errors: bool = Field(default=True, description="Include error commands")
    format: OutputFormat = Field(default=OutputFormat.JSON, description="Export format")
    max_commands: int = Field(
        default=10000, ge=1, le=50000, description="Maximum commands"
    )


class CommandExportResponse(BaseModel):
    """Schema for command export response."""

    export_id: str = Field(..., description="Export job ID")
    status: str = Field(..., description="Export status")
    total_commands: int = Field(..., description="Total commands to export")
    file_url: Optional[str] = Field(None, description="Download URL when ready")
    expires_at: Optional[datetime] = Field(None, description="URL expiration")
    created_at: datetime = Field(..., description="Export creation time")


# Command Monitoring Schemas
class CommandMetrics(BaseModel):
    """Schema for real-time command metrics."""

    active_commands: int = Field(..., description="Currently running commands")
    queued_commands: int = Field(..., description="Queued commands")
    completed_today: int = Field(..., description="Commands completed today")
    failed_today: int = Field(..., description="Commands failed today")

    # Performance metrics
    avg_response_time_ms: float = Field(..., description="Average response time")
    success_rate_24h: float = Field(..., description="24-hour success rate")

    # Resource usage
    total_cpu_time_ms: int = Field(..., description="Total CPU time used")
    peak_memory_usage_mb: Optional[int] = Field(None, description="Peak memory usage")

    # Error analysis
    top_error_types: List[Dict[str, int]] = Field(..., description="Top error types")
    timestamp: datetime = Field(..., description="Metrics timestamp")


# Error and Alert Schemas
class CommandAlert(BaseModel):
    """Schema for command alerts."""

    id: str = Field(..., description="Alert ID")
    command_id: str = Field(..., description="Related command ID")
    alert_type: str = Field(..., description="Alert type")
    severity: str = Field(..., description="Alert severity")
    message: str = Field(..., description="Alert message")
    details: Dict[str, Any] = Field(..., description="Alert details")
    triggered_at: datetime = Field(..., description="Alert trigger time")
    resolved_at: Optional[datetime] = Field(None, description="Alert resolution time")
    is_resolved: bool = Field(default=False, description="Alert resolution status")


# Batch Operations Schemas
class BulkCommandOperation(BaseModel):
    """Schema for bulk command operations."""

    command_ids: List[str] = Field(
        ..., min_items=1, max_items=1000, description="Command IDs"
    )
    operation: str = Field(..., description="Operation: delete, archive, export")
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Operation parameters"
    )


class BulkCommandResponse(BaseModel):
    """Schema for bulk command operation response."""

    success_count: int = Field(..., description="Successful operations")
    error_count: int = Field(..., description="Failed operations")
    results: List[Dict[str, Any]] = Field(..., description="Operation results")
    operation: str = Field(..., description="Performed operation")
    message: str = Field(..., description="Operation summary")
