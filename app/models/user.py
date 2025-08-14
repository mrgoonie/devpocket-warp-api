"""
User model for DevPocket API.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel


class User(BaseModel):
    """User model representing application users."""
    
    __tablename__ = "users"
    
    # Basic user information
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        nullable=False,
        index=True
    )
    
    username: Mapped[str] = mapped_column(
        String(50), 
        unique=True, 
        nullable=False,
        index=True
    )
    
    password_hash: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    
    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        nullable=False, 
        default=True,
        server_default="true"
    )
    
    is_verified: Mapped[bool] = mapped_column(
        Boolean, 
        nullable=False, 
        default=False,
        server_default="false"
    )
    
    # Subscription information
    subscription_tier: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="free",
        server_default="'free'",
        index=True
    )
    
    # API key validation
    has_api_key: Mapped[bool] = mapped_column(
        Boolean, 
        nullable=False, 
        default=False,
        server_default="false"
    )
    
    api_key_validated_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True
    )
    
    # Profile information
    display_name: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True
    )
    
    bio: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True
    )
    
    timezone: Mapped[Optional[str]] = mapped_column(
        String(50), 
        nullable=True,
        default="UTC"
    )
    
    # Authentication tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True
    )
    
    failed_login_attempts: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0"
    )
    
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        nullable=True
    )
    
    # Relationships
    sessions: Mapped[List["Session"]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    ssh_profiles: Mapped[List["SSHProfile"]] = relationship(
        "SSHProfile",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    ssh_keys: Mapped[List["SSHKey"]] = relationship(
        "SSHKey",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    settings: Mapped["UserSettings"] = relationship(
        "UserSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    sync_data: Mapped[List["SyncData"]] = relationship(
        "SyncData",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if self.locked_until is None:
            return False
        return datetime.now() < self.locked_until
    
    def can_login(self) -> bool:
        """Check if user can login."""
        return self.is_active and self.is_verified and not self.is_locked()
    
    def increment_failed_login(self) -> None:
        """Increment failed login attempts."""
        self.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            from datetime import timedelta
            self.locked_until = datetime.now() + timedelta(minutes=15)
    
    def reset_failed_login(self) -> None:
        """Reset failed login attempts."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = datetime.now()
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


class UserSettings(BaseModel):
    """User settings model for storing user preferences."""
    
    __tablename__ = "user_settings"
    
    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Terminal settings
    terminal_theme: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="dark",
        server_default="'dark'"
    )
    
    terminal_font_size: Mapped[int] = mapped_column(
        nullable=False,
        default=14,
        server_default="14"
    )
    
    terminal_font_family: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="'Fira Code'",
        server_default="'Fira Code'"
    )
    
    # AI preferences
    preferred_ai_model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="claude-3-haiku",
        server_default="'claude-3-haiku'"
    )
    
    ai_suggestions_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )
    
    ai_explanations_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )
    
    # Sync settings
    sync_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )
    
    sync_commands: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )
    
    sync_ssh_profiles: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )
    
    # Custom settings (JSON field for flexibility)
    custom_settings: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True
    )
    
    # Relationship back to user
    user: Mapped["User"] = relationship(
        "User",
        back_populates="settings"
    )
    
    def __repr__(self) -> str:
        return f"<UserSettings(id={self.id}, user_id={self.user_id})>"