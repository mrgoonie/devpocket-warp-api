"""
Pydantic schemas for authentication endpoints in DevPocket API.

Defines request/response models for user registration, login, token operations,
and password management with comprehensive validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


def is_password_strong(password: str) -> tuple[bool, list[str]]:
    """
    Check if a password meets strength requirements.

    Args:
        password: The password to check

    Returns:
        A tuple of (is_strong: bool, errors: list[str])
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")

    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")

    return len(errors) == 0, errors


# Base User Schemas
class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(
        ...,
        min_length=3,
        max_length=30,
        pattern="^[a-zA-Z0-9_-]+$",
        description="Username (alphanumeric, hyphens, underscores only)",
    )
    display_name: Optional[str] = Field(
        None, max_length=100, description="User's display name"
    )


class UserCreate(UserBase):
    """Schema for user registration."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (minimum 8 characters)",
    )
    device_id: Optional[str] = Field(
        None, description="Device identifier for session tracking"
    )
    device_type: Optional[str] = Field(
        None,
        pattern="^(ios|android|web)$",
        description="Device type (ios, android, or web)",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password meets strength requirements."""
        is_strong, errors = is_password_strong(v)
        if not is_strong:
            raise ValueError(f"Password requirements not met: {'; '.join(errors)}")
        return v


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str = Field(..., description="Username or email address")
    password: str = Field(..., description="User password")
    device_id: Optional[str] = Field(
        None, description="Device identifier for session tracking"
    )
    device_type: Optional[str] = Field(
        None,
        pattern="^(ios|android|web)$",
        description="Device type (ios, android, or web)",
    )


class UserResponse(UserBase):
    """Schema for user data responses."""

    id: str = Field(..., description="User unique identifier")
    subscription_tier: str = Field(..., description="User's subscription tier")
    is_active: bool = Field(..., description="Whether user account is active")
    is_verified: bool = Field(..., description="Whether user email is verified")
    has_api_key: bool = Field(
        ..., description="Whether user has validated their OpenRouter API key"
    )
    created_at: datetime = Field(..., description="User account creation timestamp")
    last_login_at: Optional[datetime] = Field(
        default=None, description="Last login timestamp"
    )

    class Config:
        from_attributes = True


# Token Schemas
class Token(BaseModel):
    """Schema for authentication token response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(
        default="bearer", description="Token type (always 'bearer')"
    )
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse = Field(..., description="Authenticated user information")


class TokenRefresh(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str = Field(..., description="Valid refresh token")


class TokenRefreshResponse(BaseModel):
    """Schema for token refresh response."""

    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(
        default="bearer", description="Token type (always 'bearer')"
    )
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenBlacklist(BaseModel):
    """Schema for token blacklist request."""

    token: str = Field(..., description="Token to blacklist")


# Password Management Schemas
class PasswordChange(BaseModel):
    """Schema for password change request."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ..., min_length=8, max_length=128, description="New password"
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, v):
        """Validate new password meets strength requirements."""
        is_strong, errors = is_password_strong(v)
        if not is_strong:
            raise ValueError(f"Password requirements not met: {'; '.join(errors)}")
        return v


class ForgotPassword(BaseModel):
    """Schema for forgot password request."""

    email: EmailStr = Field(..., description="Email address of the account")


class ResetPassword(BaseModel):
    """Schema for password reset request."""

    token: str = Field(..., description="Password reset token from email")
    new_password: str = Field(
        ..., min_length=8, max_length=128, description="New password"
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate new password meets strength requirements."""
        is_strong, errors = is_password_strong(v)
        if not is_strong:
            raise ValueError(f"Password requirements not met: {'; '.join(errors)}")
        return v


# Response Schemas
class MessageResponse(BaseModel):
    """Generic message response schema."""

    message: str = Field(..., description="Response message")


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: dict = Field(..., description="Error details")

    class Config:
        schema_extra = {
            "example": {
                "error": {
                    "code": 400,
                    "message": "Invalid request data",
                    "type": "validation_error",
                    "details": ["Field 'password' is required"],
                }
            }
        }


# Account Management Schemas
class AccountLockInfo(BaseModel):
    """Schema for account lock information."""

    is_locked: bool = Field(..., description="Whether the account is currently locked")
    locked_until: Optional[datetime] = Field(
        None, description="When the account lock expires"
    )
    failed_attempts: int = Field(..., description="Number of failed login attempts")


class UserSettings(BaseModel):
    """Schema for user settings."""

    terminal_theme: str = Field(
        default="dark", description="Terminal color theme preference"
    )
    terminal_font_size: int = Field(
        default=14, ge=8, le=32, description="Terminal font size"
    )
    terminal_font_family: str = Field(
        default="Fira Code", description="Terminal font family"
    )
    preferred_ai_model: str = Field(
        default="claude-3-haiku",
        description="Preferred AI model for suggestions",
    )
    ai_suggestions_enabled: bool = Field(
        default=True, description="Whether AI suggestions are enabled"
    )
    ai_explanations_enabled: bool = Field(
        default=True, description="Whether AI explanations are enabled"
    )
    sync_enabled: bool = Field(
        default=True, description="Whether cross-device sync is enabled"
    )
    sync_commands: bool = Field(
        default=True, description="Whether command history sync is enabled"
    )
    sync_ssh_profiles: bool = Field(
        default=True, description="Whether SSH profile sync is enabled"
    )


class UserSettingsUpdate(BaseModel):
    """Schema for updating user settings."""

    terminal_theme: Optional[str] = None
    terminal_font_size: Optional[int] = Field(default=None, ge=8, le=32)
    terminal_font_family: Optional[str] = None
    preferred_ai_model: Optional[str] = None
    ai_suggestions_enabled: Optional[bool] = None
    ai_explanations_enabled: Optional[bool] = None
    sync_enabled: Optional[bool] = None
    sync_commands: Optional[bool] = None
    sync_ssh_profiles: Optional[bool] = None


# API Key Validation Schema
class APIKeyValidation(BaseModel):
    """Schema for OpenRouter API key validation."""

    api_key: str = Field(..., description="OpenRouter API key to validate")


class APIKeyValidationResponse(BaseModel):
    """Schema for API key validation response."""

    is_valid: bool = Field(..., description="Whether the API key is valid")
    key_name: Optional[str] = Field(
        default=None, description="Name/description of the API key"
    )
    remaining_credits: Optional[float] = Field(
        default=None, description="Remaining credits (if available)"
    )
    rate_limit: Optional[dict] = Field(
        default=None, description="Rate limit information"
    )
