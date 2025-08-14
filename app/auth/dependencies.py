"""
FastAPI dependencies for authentication and authorization.

Provides reusable dependency functions for protecting routes,
extracting user information, and handling authentication.
"""

from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import verify_token, decode_token, is_token_blacklisted
from app.core.logging import logger
from app.db.database import get_db
from app.models.user import User
from app.repositories.user import UserRepository


# OAuth2 scheme configuration
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    scheme_name="JWT",
    auto_error=False  # Don't automatically raise 401, let us handle it
)

# HTTP Bearer scheme for alternative token extraction
http_bearer = HTTPBearer(auto_error=False)


class AuthenticationError(HTTPException):
    """Custom authentication error."""
    
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class InactiveUserError(HTTPException):
    """Error for inactive user accounts."""
    
    def __init__(self, detail: str = "Inactive user account"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


async def get_token_from_request(
    request: Request,
    oauth2_token: Annotated[Optional[str], Depends(oauth2_scheme)] = None,
    bearer_token: Annotated[Optional[HTTPAuthorizationCredentials], Depends(http_bearer)] = None,
) -> Optional[str]:
    """
    Extract JWT token from request using multiple methods.
    
    Tries to get token from:
    1. Authorization header (Bearer token)
    2. OAuth2 scheme
    3. Cookie (if configured)
    
    Args:
        request: FastAPI request object
        oauth2_token: Token from OAuth2 scheme
        bearer_token: Token from HTTP Bearer scheme
        
    Returns:
        The JWT token if found, None otherwise
    """
    # Try Bearer token first
    if bearer_token and bearer_token.credentials:
        return bearer_token.credentials
    
    # Try OAuth2 token
    if oauth2_token:
        return oauth2_token
    
    # Try cookie (optional, for web clients)
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
    
    return None


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[Optional[str], Depends(get_token_from_request)]
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        db: Database session
        token: JWT token from request
        
    Returns:
        The authenticated user
        
    Raises:
        AuthenticationError: If authentication fails
    """
    if not token:
        logger.warning("No authentication token provided")
        raise AuthenticationError("Authentication token required")
    
    try:
        # Check if token is blacklisted
        if await is_token_blacklisted(token):
            logger.warning("Attempted use of blacklisted token")
            raise AuthenticationError("Token has been revoked")
        
        # Decode and verify token
        payload = verify_token(token)
        if not payload:
            logger.warning("Invalid or expired token")
            raise AuthenticationError("Invalid or expired token")
        
        # Extract user identifier
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Token missing user identifier")
            raise AuthenticationError("Invalid token format")
        
        # Get user from database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        
        if not user:
            logger.warning(f"User not found for ID: {user_id}")
            raise AuthenticationError("User not found")
        
        logger.debug(f"User authenticated: {user.username}")
        return user
        
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise AuthenticationError("Authentication failed")


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Get the current authenticated and active user.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        The active user
        
    Raises:
        InactiveUserError: If user account is inactive
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.username}")
        raise InactiveUserError("Account has been deactivated")
    
    if not current_user.is_verified:
        logger.warning(f"Unverified user attempted access: {current_user.username}")
        raise InactiveUserError("Email verification required")
    
    if current_user.is_locked():
        logger.warning(f"Locked user attempted access: {current_user.username}")
        raise InactiveUserError("Account is temporarily locked")
    
    return current_user


async def get_optional_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[Optional[str], Depends(get_token_from_request)]
) -> Optional[User]:
    """
    Get the current user if authenticated, None if not.
    
    Useful for endpoints that work with or without authentication.
    
    Args:
        db: Database session
        token: JWT token from request
        
    Returns:
        The authenticated user or None
    """
    if not token:
        return None
    
    try:
        return await get_current_user(db, token)
    except (AuthenticationError, InactiveUserError):
        return None


async def require_subscription_tier(
    min_tier: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    Require a minimum subscription tier for access.
    
    Args:
        min_tier: Minimum required subscription tier
        current_user: The authenticated user
        
    Returns:
        The user if they have sufficient tier
        
    Raises:
        HTTPException: If subscription tier is insufficient
    """
    tier_hierarchy = {
        "free": 0,
        "pro": 1,
        "team": 2,
        "enterprise": 3
    }
    
    user_tier_level = tier_hierarchy.get(current_user.subscription_tier, 0)
    required_tier_level = tier_hierarchy.get(min_tier, 999)
    
    if user_tier_level < required_tier_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This feature requires {min_tier} subscription or higher"
        )
    
    return current_user


def require_pro_tier() -> callable:
    """Dependency factory for Pro tier requirement."""
    async def _require_pro(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        return await require_subscription_tier("pro", current_user)
    return _require_pro


def require_team_tier() -> callable:
    """Dependency factory for Team tier requirement."""
    async def _require_team(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        return await require_subscription_tier("team", current_user)
    return _require_team


def require_enterprise_tier() -> callable:
    """Dependency factory for Enterprise tier requirement."""
    async def _require_enterprise(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        return await require_subscription_tier("enterprise", current_user)
    return _require_enterprise


async def get_user_from_token(
    token: str,
    db: AsyncSession
) -> Optional[User]:
    """
    Utility function to get user from a token directly.
    
    Useful for WebSocket authentication and background tasks.
    
    Args:
        token: JWT token
        db: Database session
        
    Returns:
        The user if token is valid, None otherwise
    """
    try:
        # Check if token is blacklisted
        if await is_token_blacklisted(token):
            return None
        
        # Decode and verify token
        payload = verify_token(token)
        if not payload:
            return None
        
        # Extract user identifier
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Get user from database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        
        if not user or not user.is_active or not user.is_verified:
            return None
        
        return user
        
    except Exception as e:
        logger.error(f"Error getting user from token: {e}")
        return None


# Convenience aliases
require_auth = get_current_active_user
optional_auth = get_optional_current_user