"""
Authentication router for DevPocket API.

Handles all authentication-related endpoints including user registration,
login, token management, and password operations.
"""

from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user, get_current_user
from app.auth.schemas import (
    AccountLockInfo,
    EmailVerificationRequest,
    ForgotPassword,
    MessageResponse,
    PasswordChange,
    ResetPassword,
    Token,
    TokenRefreshRequest,
    TokenRefreshResponse,
    UserCreate,
    UserResponse,
)
from app.auth.security import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_password_reset_token,
    hash_password,
    verify_password,
    verify_password_reset_token,
)
from app.core.config import settings
from app.core.logging import logger
from app.db.database import get_db
from app.models.user import User
from app.repositories.user import UserRepository

# Create router instance
router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
    responses={
        401: {"description": "Authentication failed"},
        403: {"description": "Access forbidden"},
        422: {"description": "Validation error"},
    },
)


# Rate limiting storage (in production, use Redis)
_rate_limit_storage: dict[str, Any] = {}


def check_rate_limit(
    request: Request, key: str, max_attempts: int = 5, window: int = 900
) -> bool:
    """
    Simple in-memory rate limiting check.
    In production, this should use Redis for distributed rate limiting.

    Args:
        request: FastAPI request object
        key: Rate limiting key (e.g., email or IP)
        max_attempts: Maximum attempts allowed
        window: Time window in seconds

    Returns:
        True if request is allowed, False if rate limited
    """
    now = datetime.now()
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{key}"

    if rate_key not in _rate_limit_storage:
        _rate_limit_storage[rate_key] = []

    # Clean old attempts
    _rate_limit_storage[rate_key] = [
        attempt_time
        for attempt_time in _rate_limit_storage[rate_key]
        if (now - attempt_time).total_seconds() < window
    ]

    # Check if rate limited
    if len(_rate_limit_storage[rate_key]) >= max_attempts:
        return False

    # Record this attempt
    _rate_limit_storage[rate_key].append(now)
    return True


async def send_password_reset_email(email: str) -> None:
    """
    Send password reset email (placeholder implementation).
    In production, integrate with email service provider.

    Args:
        email: Recipient email address
    """
    # Placeholder for email sending logic - in production, the token would be passed
    logger.info(f"Password reset requested for {email}")


async def send_verification_email(email: str) -> None:
    """
    Send email verification email (placeholder implementation).
    In production, integrate with email service provider.

    Args:
        email: Recipient email address
    """
    # Placeholder for email sending logic - in production, the token would be passed
    logger.info(f"Email verification requested for {email}")


# Authentication Endpoints


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account with email, username, and password",
)
async def register_user(
    user_data: UserCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Register a new user account."""

    # Rate limiting for registration
    if not check_rate_limit(
        request, f"register:{user_data.email}", max_attempts=3, window=3600
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later.",
        )

    try:
        # Validate password strength
        from app.auth.security import is_password_strong

        is_strong, errors = is_password_strong(user_data.password)
        if not is_strong:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password requirements not met: {'; '.join(errors)}",
            )

        # Check if user already exists
        user_repo = UserRepository(db)

        existing_user = await user_repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        existing_user = await user_repo.get_by_username(user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

        # Hash password
        password_hash = hash_password(user_data.password)

        # Create user
        user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=password_hash,
            display_name=user_data.display_name,
            subscription_tier="free",
            is_active=True,
            is_verified=False,  # In production, require email verification
        )

        created_user = await user_repo.create(user)
        await db.commit()

        # Generate tokens
        token_data = {"sub": str(created_user.id), "email": created_user.email}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        logger.info(f"User registered successfully: {created_user.username}")

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_expiration_hours * 3600,
            user=UserResponse.from_user(created_user),
        )

    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.warning(f"Database integrity error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists",
        ) from e
    except Exception as e:
        await db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again.",
        ) from e


@router.post(
    "/login",
    response_model=Token,
    summary="Login user",
    description="Authenticate user with username/email and password",
)
async def login_user(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Authenticate user and return JWT tokens."""

    # Rate limiting for login attempts
    if request and not check_rate_limit(
        request, f"login:{form_data.username}", max_attempts=5, window=900
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again in 15 minutes.",
        )

    try:
        user_repo = UserRepository(db)

        # Get user by username or email
        user = await user_repo.get_by_username(form_data.username)
        if not user:
            user = await user_repo.get_by_email(form_data.username)

        # Check if user exists and password is correct
        if not user or not verify_password(form_data.password, user.password_hash):
            # Increment failed login attempts if user exists
            if user:
                user.increment_failed_login()
                await user_repo.update(user)
                await db.commit()

            logger.warning(f"Failed login attempt for: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if account is locked
        if user.is_locked():
            logger.warning(f"Login attempt on locked account: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account is locked until {user.locked_until}. Please try again later.",
            )

        # Check if account is active and verified
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account has been deactivated",
            )

        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email verification required",
            )

        # Reset failed login attempts and update last login
        user.reset_failed_login()
        await user_repo.update(user)
        await db.commit()

        # Generate tokens
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "subscription_tier": user.subscription_tier,
        }

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        logger.info(f"User logged in successfully: {user.username}")

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_expiration_hours * 3600,
            user=UserResponse.from_user(user),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again.",
        ) from e


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="Refresh access token",
    description="Generate a new access token using a valid refresh token",
)
async def refresh_token(
    request_data: TokenRefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenRefreshResponse:
    """Refresh access token using refresh token."""

    try:
        # Decode and verify refresh token
        payload = decode_token(request_data.refresh_token)

        # Verify this is a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate UUID format
        try:
            from uuid import UUID

            UUID(user_id)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None

        # Verify user still exists and is active
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)

        if not user or not user.is_active or not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate new access and refresh tokens
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "subscription_tier": user.subscription_tier,
        }

        new_access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)

        logger.debug(f"Token refreshed for user: {user.username}")

        return TokenRefreshResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_expiration_hours * 3600,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout user",
    description="Logout user and blacklist current token",
)
async def logout_user(
    current_user: Annotated[User, Depends(get_current_user)], request: Request
) -> MessageResponse:
    """Logout user and blacklist the current token."""

    try:
        # Extract token from request
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

            # Blacklist the token
            await blacklist_token(token)
            logger.info(f"User logged out: {current_user.username}")

        return MessageResponse(message="Logout successful")

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return MessageResponse(message="Logout completed")  # Don't fail logout


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get current authenticated user information",
)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    """Get current user information."""
    return UserResponse.from_user(current_user)


# Password Management Endpoints


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset",
    description="Send password reset email to user",
)
async def forgot_password(
    request_data: ForgotPassword,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Send password reset email."""

    # Rate limiting for password reset
    if not check_rate_limit(
        request, f"reset:{request_data.email}", max_attempts=3, window=3600
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset attempts. Please try again later.",
        )

    try:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_email(request_data.email)

        # Always return success for security (don't reveal if email exists)
        if user and user.is_active:
            generate_password_reset_token(user.email)
            background_tasks.add_task(send_password_reset_email, user.email)
            logger.info(f"Password reset requested for: {user.email}")

        return MessageResponse(message="Password reset email sent successfully.")

    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        return MessageResponse(
            message="If the email exists in our system, you will receive a password reset link."
        )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password",
    description="Reset password using reset token",
)
async def reset_password(
    reset_data: ResetPassword, db: Annotated[AsyncSession, Depends(get_db)]
) -> MessageResponse:
    """Reset user password using reset token."""

    try:
        # Verify reset token
        email = verify_password_reset_token(reset_data.token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        # Get user
        user_repo = UserRepository(db)
        user = await user_repo.get_by_email(email)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Validate password strength
        from app.auth.security import is_password_strong

        is_strong, errors = is_password_strong(reset_data.new_password)
        if not is_strong:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password requirements not met: {'; '.join(errors)}",
            )

        # Update password
        user.password_hash = hash_password(reset_data.new_password)
        user.failed_login_attempts = 0  # Reset failed attempts
        user.locked_until = None  # Unlock account if locked

        await user_repo.update(user)
        await db.commit()

        logger.info(f"Password reset successful for: {user.email}")

        return MessageResponse(message="Password reset successful")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed. Please try again.",
        ) from e


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password",
    description="Change user password with current password verification",
)
async def change_password(
    password_data: PasswordChange,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Change user password."""

    try:
        # Verify current password
        if not verify_password(
            password_data.current_password, current_user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        # Update password
        current_user.password_hash = hash_password(password_data.new_password)

        user_repo = UserRepository(db)
        await user_repo.update(current_user)
        await db.commit()

        logger.info(f"Password changed for user: {current_user.username}")

        return MessageResponse(message="Password changed successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed. Please try again.",
        ) from e


# Account Management Endpoints


@router.get(
    "/account-status",
    response_model=AccountLockInfo,
    summary="Get account status",
    description="Get current account lock status and failed login attempts",
)
async def get_account_status(
    current_user: Annotated[User, Depends(get_current_user)],
) -> AccountLockInfo:
    """Get account lock status information."""
    return AccountLockInfo(
        is_locked=current_user.is_locked(),
        locked_until=current_user.locked_until,
        failed_attempts=current_user.failed_login_attempts,
    )


# Email Verification Endpoints


@router.post(
    "/verify-email-request",
    response_model=MessageResponse,
    summary="Request email verification",
    description="Send email verification link to user",
)
async def request_email_verification(
    request_data: EmailVerificationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Send email verification email."""

    # Rate limiting for email verification
    if not check_rate_limit(
        request, f"verify:{request_data.email}", max_attempts=3, window=3600
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many email verification attempts. Please try again later.",
        )

    try:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_email(request_data.email)

        if not user:
            # Return success for security (don't reveal if email exists)
            return MessageResponse(
                message="If the email exists in our system, you will receive a verification email."
            )

        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified",
            )

        if not user.is_active:
            # Return success for security (don't reveal if account is inactive)
            return MessageResponse(
                message="If the email exists in our system, you will receive a verification email."
            )

        # Generate verification token
        create_access_token(
            {"sub": user.email, "type": "email_verification"},
            expires_delta=timedelta(hours=24),
        )

        background_tasks.add_task(send_verification_email, user.email)
        logger.info(f"Email verification requested for: {user.email}")

        return MessageResponse(message="Verification email sent successfully.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification request error: {e}")
        return MessageResponse(
            message="If the email exists in our system, you will receive a verification email."
        )


@router.get(
    "/verify-email/{token}",
    response_model=MessageResponse,
    summary="Verify email address",
    description="Verify user email using verification token",
)
async def verify_email(
    token: str, db: Annotated[AsyncSession, Depends(get_db)]
) -> MessageResponse:
    """Verify user email address using verification token."""

    try:
        # Decode and verify token
        payload = decode_token(token)

        # Verify this is an email verification token
        if payload.get("type") != "email_verification":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token",
            )

        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token",
            )

        # Get user
        user_repo = UserRepository(db)
        user = await user_repo.get_by_email(email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token",
            )

        if user.is_verified:
            return MessageResponse(message="Email is already verified")

        # Verify the email
        user.is_verified = True
        await user_repo.update(user)
        await db.commit()

        logger.info(f"Email verified successfully for: {user.email}")

        return MessageResponse(message="Email verified successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        ) from e
