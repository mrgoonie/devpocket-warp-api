"""
Pydantic schemas for user profile and settings endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class UserProfileResponse(BaseModel):
    """Schema for user profile response."""
    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    display_name: Optional[str] = Field(None, description="Display name")
    subscription_tier: str = Field(..., description="Subscription tier")
    created_at: datetime = Field(..., description="Account creation date")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile."""
    display_name: Optional[str] = Field(None, max_length=100, description="Display name")
    email: Optional[str] = Field(None, description="Email address")


class UserSettings(BaseModel):
    """Schema for user settings."""
    theme: str = Field(default="dark", description="UI theme preference")
    timezone: str = Field(default="UTC", description="User timezone")
    language: str = Field(default="en", description="Language preference")
    terminal_preferences: Dict[str, Any] = Field(default={}, description="Terminal preferences")
    ai_preferences: Dict[str, Any] = Field(default={}, description="AI service preferences")
    sync_enabled: bool = Field(default=True, description="Multi-device sync enabled")
    notifications_enabled: bool = Field(default=True, description="Notifications enabled")


class UserSettingsResponse(UserSettings):
    """Schema for user settings response."""
    user_id: str = Field(..., description="User ID")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Schema for simple message responses."""
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")