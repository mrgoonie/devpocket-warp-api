"""
Security utilities for DevPocket API.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.core.config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        bool: True if password is correct
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Token payload data
        expires_delta: Optional custom expiration time

    Returns:
        str: JWT token
    """
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

    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Token payload data
        expires_delta: Optional custom expiration time

    Returns:
        str: JWT refresh token
    """
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

    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token to verify
        token_type: Expected token type (access or refresh)

    Returns:
        Dict[str, Any]: Token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )

        # Check token type
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(
            timezone.utc
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def generate_session_id() -> str:
    """
    Generate a secure session ID.

    Returns:
        str: Random session ID
    """
    import uuid

    return str(uuid.uuid4())


def validate_password_strength(password: str) -> bool:
    """
    Validate password strength.

    Args:
        password: Password to validate

    Returns:
        bool: True if password meets requirements
    """
    # Minimum length
    if len(password) < 8:
        return False

    # Must contain at least one uppercase letter
    if not any(c.isupper() for c in password):
        return False

    # Must contain at least one lowercase letter
    if not any(c.islower() for c in password):
        return False

    # Must contain at least one digit
    if not any(c.isdigit() for c in password):
        return False

    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal attacks.

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename
    """
    import re
    import os

    # Remove directory traversal attempts
    filename = os.path.basename(filename)

    # Remove potentially dangerous characters
    filename = re.sub(r"[^\w\-_\.]", "_", filename)

    # Limit length
    if len(filename) > 255:
        filename = filename[:255]

    # Ensure it's not empty
    if not filename:
        filename = "unnamed_file"

    return filename


def validate_ssh_host(host: str) -> bool:
    """
    Validate SSH host format.

    Args:
        host: SSH host to validate

    Returns:
        bool: True if host format is valid
    """
    import re

    # Check for basic format (IP or hostname)
    ip_pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
    hostname_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"

    if re.match(ip_pattern, host) or re.match(hostname_pattern, host):
        return True

    return False


def validate_ssh_port(port: int) -> bool:
    """
    Validate SSH port number.

    Args:
        port: SSH port to validate

    Returns:
        bool: True if port is valid
    """
    return 1 <= port <= 65535


def rate_limit_key(ip: str, endpoint: str) -> str:
    """
    Generate a rate limiting key.

    Args:
        ip: Client IP address
        endpoint: API endpoint

    Returns:
        str: Rate limiting key
    """
    return f"rate_limit:{ip}:{endpoint}"


def get_client_ip(request) -> str:
    """
    Extract client IP address from request.

    Args:
        request: FastAPI request object

    Returns:
        str: Client IP address
    """
    # Check for forwarded IP (reverse proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    # Check for real IP (some proxies)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct connection
    return request.client.host if request.client else "unknown"
