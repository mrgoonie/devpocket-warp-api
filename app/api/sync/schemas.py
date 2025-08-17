"""
Pydantic schemas for multi-device synchronization endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SyncStatus(str, Enum):
    """Synchronization status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class SyncDataType(str, Enum):
    """Types of data that can be synchronized."""

    SSH_PROFILES = "ssh_profiles"
    SESSIONS = "sessions"
    COMMANDS = "commands"
    SETTINGS = "settings"
    AI_PREFERENCES = "ai_preferences"
    ALL = "all"


# Sync Data Schemas
class SyncDataRequest(BaseModel):
    """Schema for synchronization data request."""

    data_types: list[SyncDataType] = Field(..., description="Types of data to sync")
    device_id: str = Field(..., description="Unique device identifier")
    device_name: str = Field(..., description="Human-readable device name")
    last_sync_timestamp: datetime | None = Field(
        None, description="Last synchronization time"
    )
    include_deleted: bool = Field(default=False, description="Include deleted items")


class SyncDataResponse(BaseModel):
    """Schema for synchronization data response."""

    data: dict[str, list[dict[str, Any]]] = Field(
        ..., description="Synchronized data by type"
    )
    sync_timestamp: datetime = Field(..., description="Current sync timestamp")
    total_items: int = Field(..., description="Total items synchronized")
    conflicts: list[dict[str, Any]] = Field(
        default=[], description="Synchronization conflicts"
    )
    device_count: int = Field(..., description="Number of devices for this user")


class SyncConflictResolution(BaseModel):
    """Schema for resolving sync conflicts."""

    conflict_id: str = Field(..., description="Conflict identifier")
    resolution: str = Field(
        ..., description="Resolution strategy: local, remote, merge"
    )
    resolved_data: dict[str, Any] | None = Field(
        None, description="Resolved data if using merge"
    )


# Device Management Schemas
class DeviceInfo(BaseModel):
    """Schema for device information."""

    device_id: str = Field(..., description="Device ID")
    device_name: str = Field(..., description="Device name")
    device_type: str = Field(..., description="Device type (mobile, desktop, tablet)")
    os_info: str | None = Field(
        default=None, description="Operating system information"
    )
    app_version: str | None = Field(default=None, description="App version")
    last_sync: datetime | None = Field(default=None, description="Last sync timestamp")
    is_active: bool = Field(default=True, description="Device active status")


class DeviceRegistration(BaseModel):
    """Schema for device registration."""

    device_name: str = Field(..., max_length=100, description="Device name")
    device_type: str = Field(..., description="Device type")
    os_info: str | None = Field(default=None, description="OS information")
    app_version: str | None = Field(default=None, description="App version")


class SyncStats(BaseModel):
    """Schema for synchronization statistics."""

    total_syncs: int = Field(..., description="Total sync operations")
    successful_syncs: int = Field(..., description="Successful syncs")
    failed_syncs: int = Field(..., description="Failed syncs")
    last_sync: datetime | None = Field(default=None, description="Last sync time")
    active_devices: int = Field(..., description="Number of active devices")
    total_conflicts: int = Field(..., description="Total conflicts encountered")
    resolved_conflicts: int = Field(..., description="Resolved conflicts")


# Common Response Schemas
class MessageResponse(BaseModel):
    """Schema for simple message responses."""

    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
