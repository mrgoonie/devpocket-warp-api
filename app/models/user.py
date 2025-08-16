"""
User model for DevPocket API.
"""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID as PyUUID
from sqlalchemy import String, Boolean, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from .base import BaseModel


class UserRole(enum.Enum):
    """User role enumeration."""

    USER = "user"
    ADMIN = "admin"
    PREMIUM = "premium"


class User(BaseModel):
    """User model representing application users."""

    __tablename__ = "users"

    # Basic user information
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    role: Mapped[UserRole] = mapped_column(
        ENUM(UserRole, name="user_role", create_type=False),
        nullable=False,
        default=UserRole.USER,
        server_default="user",
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    verification_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    reset_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    reset_token_expires: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    openrouter_api_key: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Subscription information
    subscription_tier: Mapped[str] = mapped_column(
        String(50), nullable=False, default="free", server_default="'free'"
    )

    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Security fields
    failed_login_attempts: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default="0"
    )

    locked_until: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    last_login_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    sessions: Mapped[List["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )

    ssh_profiles: Mapped[List["SSHProfile"]] = relationship(
        "SSHProfile", back_populates="user", cascade="all, delete-orphan"
    )

    ssh_keys: Mapped[List["SSHKey"]] = relationship(
        "SSHKey", back_populates="user", cascade="all, delete-orphan"
    )

    settings: Mapped["UserSettings"] = relationship(
        "UserSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    sync_data: Mapped[List["SyncData"]] = relationship(
        "SyncData", back_populates="user", cascade="all, delete-orphan"
    )

    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    def can_login(self) -> bool:
        """Check if user can login."""
        return self.is_active and self.is_verified and not self.is_locked()

    def increment_failed_login(self) -> None:
        """Increment failed login attempts."""
        # Initialize to 0 if None (for new instances)
        if self.failed_login_attempts is None:
            self.failed_login_attempts = 0

        self.failed_login_attempts += 1

        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            from datetime import timedelta

            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)

    def reset_failed_login(self) -> None:
        """Reset failed login attempts."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


class UserSettings(BaseModel):
    """User settings model for storing user preferences."""

    __tablename__ = "user_settings"

    # Foreign key to user
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Terminal settings
    terminal_theme: Mapped[str] = mapped_column(
        String(50), nullable=False, default="dark", server_default="'dark'"
    )

    terminal_font_size: Mapped[int] = mapped_column(
        nullable=False, default=14, server_default="14"
    )

    terminal_font_family: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="'Fira Code'",
        server_default="'Fira Code'",
    )

    # AI preferences
    preferred_ai_model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="claude-3-haiku",
        server_default="'claude-3-haiku'",
    )

    ai_suggestions_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    ai_explanations_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # Sync settings
    sync_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    sync_commands: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    sync_ssh_profiles: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # Custom settings (JSON field for flexibility)
    custom_settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationship back to user
    user: Mapped["User"] = relationship("User", back_populates="settings")

    def __repr__(self) -> str:
        return f"<UserSettings(id={self.id}, user_id={self.user_id})>"
