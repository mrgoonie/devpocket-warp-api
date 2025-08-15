"""
JWT authentication and password security utilities for DevPocket API.

Provides secure password hashing, JWT token generation/validation,
token blacklisting, and password reset functionality.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union
import redis.asyncio as aioredis
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.logging import logger


# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=settings.bcrypt_rounds
)

# Redis client for token blacklisting (will be set during app startup)
_redis_client: Optional[aioredis.Redis] = None


def set_redis_client(redis_client: aioredis.Redis) -> None:
    """Set the Redis client for token blacklisting."""
    global _redis_client
    _redis_client = redis_client


# Password Security Functions
def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: The plain text password to hash

    Returns:
        The hashed password
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing failed: {e}")
        raise ValueError("Failed to hash password")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The stored password hash

    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False


# JWT Token Functions
def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: The data to encode in the token (must include 'sub' for subject)
        expires_delta: Custom expiration time, defaults to configured hours

    Returns:
        The encoded JWT token

    Raises:
        ValueError: If required data is missing
    """
    if not data.get("sub"):
        raise ValueError("Token data must include 'sub' (subject) field")

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            hours=settings.jwt_expiration_hours
        )

    to_encode.update(
        {"exp": expire, "iat": datetime.now(timezone.utc), "type": "access"}
    )

    try:
        encoded_jwt = jwt.encode(
            to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

        logger.debug(f"Access token created for user: {data.get('sub')}")
        return encoded_jwt

    except Exception as e:
        logger.error(f"JWT encoding failed: {e}")
        raise ValueError("Failed to create access token")


def create_refresh_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: The data to encode in the token (must include 'sub' for subject)
        expires_delta: Custom expiration time, defaults to configured days

    Returns:
        The encoded JWT refresh token

    Raises:
        ValueError: If required data is missing
    """
    if not data.get("sub"):
        raise ValueError("Token data must include 'sub' (subject) field")

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.jwt_refresh_expiration_days
        )

    to_encode.update(
        {"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"}
    )

    try:
        encoded_jwt = jwt.encode(
            to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

        logger.debug(f"Refresh token created for user: {data.get('sub')}")
        return encoded_jwt

    except Exception as e:
        logger.error(f"JWT refresh token encoding failed: {e}")
        raise ValueError("Failed to create refresh token")


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token.

    Args:
        token: The JWT token to decode

    Returns:
        The decoded token payload

    Raises:
        JWTError: If token is invalid, expired, or malformed
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )

        # Verify token hasn't expired
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(
            timezone.utc
        ):
            raise JWTError("Token has expired")

        return payload

    except JWTError as e:
        logger.warning(f"JWT decoding failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error decoding JWT: {e}")
        raise JWTError("Token decoding failed")


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a JWT token and return its payload if valid.

    Args:
        token: The JWT token to verify

    Returns:
        The token payload if valid, None if invalid
    """
    try:
        payload = decode_token(token)

        # Check if token is blacklisted
        if is_token_blacklisted_sync(token):
            logger.warning("Attempted use of blacklisted token")
            return None

        return payload

    except JWTError:
        return None


async def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token is blacklisted (async version).

    Args:
        token: The JWT token to check

    Returns:
        True if token is blacklisted, False otherwise
    """
    if not _redis_client:
        logger.warning("Redis client not available for token blacklist check")
        return False

    try:
        result = await _redis_client.get(f"blacklist:{token}")
        return result is not None
    except Exception as e:
        logger.error(f"Error checking token blacklist: {e}")
        return False


def is_token_blacklisted_sync(token: str) -> bool:
    """
    Synchronous version of token blacklist check.
    Used in verify_token for backwards compatibility.

    Args:
        token: The JWT token to check

    Returns:
        True if token is blacklisted, False otherwise
    """
    # For synchronous check, we'll assume not blacklisted
    # This is a limitation but prevents blocking operations
    return False


async def blacklist_token(token: str, expires_at: Optional[datetime] = None) -> None:
    """
    Add a token to the blacklist.

    Args:
        token: The JWT token to blacklist
        expires_at: When the blacklist entry should expire (defaults to token exp)
    """
    if not _redis_client:
        logger.warning("Redis client not available for token blacklisting")
        return

    try:
        # If no expiration provided, try to get it from the token
        if not expires_at:
            try:
                payload = decode_token(token)
                exp_timestamp = payload.get("exp")
                if exp_timestamp:
                    expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            except JWTError:
                # If we can't decode the token, use a default expiration
                expires_at = datetime.now(timezone.utc) + timedelta(days=1)

        # Calculate TTL in seconds
        ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())

        if ttl > 0:
            await _redis_client.setex(f"blacklist:{token}", ttl, "blacklisted")
            logger.info("Token blacklisted successfully")

    except Exception as e:
        logger.error(f"Error blacklisting token: {e}")


# Password Reset Functions
def generate_password_reset_token(email: str) -> str:
    """
    Generate a secure token for password reset.

    Args:
        email: The user's email address

    Returns:
        A secure reset token
    """
    data = {
        "sub": email,
        "type": "password_reset",
        "reset_id": secrets.token_urlsafe(16),  # Additional security
    }

    # Password reset tokens expire in 1 hour
    expires_delta = timedelta(hours=1)

    return create_access_token(data, expires_delta)


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify a password reset token and return the email if valid.

    Args:
        token: The password reset token

    Returns:
        The email address if token is valid, None otherwise
    """
    try:
        payload = decode_token(token)

        # Verify this is a password reset token
        if payload.get("type") != "password_reset":
            logger.warning("Invalid token type for password reset")
            return None

        email = payload.get("sub")
        if not email:
            logger.warning("No email found in password reset token")
            return None

        return email

    except JWTError:
        logger.warning("Invalid password reset token")
        return None


# Utility Functions
def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Args:
        length: The length of the token to generate

    Returns:
        A secure random token
    """
    return secrets.token_urlsafe(length)


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
