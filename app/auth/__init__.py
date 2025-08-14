"""
Authentication module for DevPocket API.

This module provides JWT-based authentication functionality including:
- Password hashing and verification
- JWT token creation and validation
- Authentication dependencies
- Password reset functionality
"""

from .security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
    is_token_blacklisted,
    blacklist_token,
    generate_password_reset_token,
    verify_password_reset_token,
)

from .dependencies import (
    get_current_user,
    get_current_active_user,
    get_optional_current_user,
    require_auth,
)

__all__ = [
    # Security utilities
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "decode_token",
    "is_token_blacklisted",
    "blacklist_token",
    "generate_password_reset_token",
    "verify_password_reset_token",
    
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_optional_current_user",
    "require_auth",
]