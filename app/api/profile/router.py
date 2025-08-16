"""
User Profile & Settings API router for DevPocket.
"""

from typing import Annotated, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.db.database import get_db
from app.models.user import User
from .schemas import (
    UserProfileResponse,
    UserProfileUpdate,
    UserSettings,
    UserSettingsResponse,
    MessageResponse,
)
from .service import ProfileService


router = APIRouter(
    prefix="/api/profile",
    tags=["User Profile & Settings"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Access forbidden"},
        500: {"description": "Internal server error"},
    },
)


# Profile Management Endpoints
@router.get("/", response_model=UserProfileResponse, summary="Get User Profile")
async def get_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserProfileResponse:
    """Retrieve current user's profile information."""
    service = ProfileService(db)
    return await service.get_profile(current_user)


@router.put("/", response_model=UserProfileResponse, summary="Update User Profile")
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserProfileResponse:
    """Update current user's profile information."""
    service = ProfileService(db)
    return await service.update_profile(current_user, profile_data)


@router.delete("/", response_model=MessageResponse, summary="Delete User Account")
async def delete_account(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Delete current user's account and all associated data."""
    service = ProfileService(db)
    await service.delete_account(current_user)
    return MessageResponse(message="Account successfully deleted")


@router.get("/stats", response_model=Dict[str, Any], summary="Get Account Statistics")
async def get_account_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Dict[str, Any]:
    """Get current user's account statistics and usage information."""
    service = ProfileService(db)
    return await service.get_account_stats(current_user)


# Settings Management Endpoints
@router.get(
    "/settings",
    response_model=UserSettingsResponse,
    summary="Get User Settings",
)
async def get_settings(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserSettingsResponse:
    """Retrieve current user's settings."""
    service = ProfileService(db)
    return await service.get_settings(current_user)


@router.put(
    "/settings",
    response_model=UserSettingsResponse,
    summary="Update User Settings",
)
async def update_settings(
    settings_data: UserSettings,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserSettingsResponse:
    """Update current user's settings."""
    service = ProfileService(db)
    return await service.update_settings(current_user, settings_data)


@router.post(
    "/settings/reset",
    response_model=UserSettingsResponse,
    summary="Reset Settings to Default",
)
async def reset_settings_to_default(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserSettingsResponse:
    """Reset current user's settings to default values."""
    service = ProfileService(db)
    default_settings = UserSettings()  # Uses default values from schema
    return await service.update_settings(current_user, default_settings)
