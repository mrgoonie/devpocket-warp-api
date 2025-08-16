"""
Sync data model for DevPocket API.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID as PyUUID
from sqlalchemy import String, ForeignKey, Text, Boolean, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel


class SyncData(BaseModel):
    """Sync data model for cross-device synchronization."""

    __tablename__ = "sync_data"

    # Foreign key to user
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Sync metadata
    sync_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # commands, ssh_profiles, settings, history

    sync_key: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )  # Unique identifier for the synced item

    # Data content
    data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Sync status
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )

    # Device information
    source_device_id: Mapped[str] = mapped_column(String(255), nullable=False)

    source_device_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # ios, android, web

    # Conflict resolution
    conflict_data: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Store conflicting versions for manual resolution

    resolved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Sync timestamps
    synced_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="now()", index=True
    )

    last_modified_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="now()"
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sync_data")

    # Methods
    def mark_as_deleted(self, device_id: str, device_type: str) -> None:
        """Mark sync data as deleted."""
        self.is_deleted = True
        self.source_device_id = device_id
        self.source_device_type = device_type
        self.last_modified_at = datetime.now()
        self.version += 1

    def update_data(
        self, new_data: dict, device_id: str, device_type: str
    ) -> None:
        """Update sync data with new content."""
        self.data = new_data
        self.source_device_id = device_id
        self.source_device_type = device_type
        self.last_modified_at = datetime.now()
        self.version += 1

    def create_conflict(self, conflicting_data: dict) -> None:
        """Create a conflict entry when data differs across devices."""
        self.conflict_data = {
            "current_data": self.data,
            "conflicting_data": conflicting_data,
            "conflict_created_at": datetime.now().isoformat(),
        }

    def resolve_conflict(
        self, chosen_data: dict, device_id: str, device_type: str
    ) -> None:
        """Resolve a data conflict by choosing one version."""
        self.data = chosen_data
        self.conflict_data = None
        self.resolved_at = datetime.now()
        self.source_device_id = device_id
        self.source_device_type = device_type
        self.version += 1

    @property
    def has_conflict(self) -> bool:
        """Check if this sync data has unresolved conflicts."""
        return self.conflict_data is not None and self.resolved_at is None

    @property
    def age_in_hours(self) -> float:
        """Get age of sync data in hours."""
        return (datetime.now() - self.last_modified_at).total_seconds() / 3600

    @classmethod
    def create_sync_item(
        cls,
        user_id: PyUUID,
        sync_type: str,
        sync_key: str,
        data: dict,
        device_id: str,
        device_type: str,
    ) -> "SyncData":
        """Create a new sync data item."""
        return cls(
            user_id=user_id,
            sync_type=sync_type,
            sync_key=sync_key,
            data=data,
            source_device_id=device_id,
            source_device_type=device_type,
            synced_at=datetime.now(),
            last_modified_at=datetime.now(),
        )

    def __repr__(self) -> str:
        return f"<SyncData(id={self.id}, user_id={self.user_id}, sync_type={self.sync_type}, sync_key={self.sync_key})>"
