"""
User profile and settings service for DevPocket API.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.logging import logger
from app.models.user import User
# from app.models.user_settings import UserSettings as UserSettingsModel
from app.repositories.user import UserRepository
# from app.repositories.user_settings import UserSettingsRepository
from .schemas import UserProfileUpdate, UserSettings, UserProfileResponse, UserSettingsResponse


class ProfileService:
    """Service class for user profile and settings management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.settings_repo = UserSettingsRepository(session)

    async def get_profile(self, user: User) -> UserProfileResponse:
        """Get user profile information."""
        try:
            return UserProfileResponse(
                id=str(user.id),
                username=user.username,
                email=user.email,
                display_name=user.display_name,
                subscription_tier=user.subscription_tier.value if user.subscription_tier else "free",
                created_at=user.created_at,
                updated_at=user.updated_at
            )

        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user profile"
            )

    async def update_profile(self, user: User, profile_data: UserProfileUpdate) -> UserProfileResponse:
        """Update user profile information."""
        try:
            # Check if email is being changed and if it's already taken
            if profile_data.email and profile_data.email != user.email:
                existing_user = await self.user_repo.get_by_email(profile_data.email)
                if existing_user and existing_user.id != user.id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email address is already registered"
                    )

            # Update user profile
            update_data = {}
            if profile_data.display_name is not None:
                update_data["display_name"] = profile_data.display_name
            if profile_data.email is not None:
                update_data["email"] = profile_data.email

            if update_data:
                updated_user = await self.user_repo.update(user.id, update_data)
                await self.session.commit()
            else:
                updated_user = user

            return UserProfileResponse(
                id=str(updated_user.id),
                username=updated_user.username,
                email=updated_user.email,
                display_name=updated_user.display_name,
                subscription_tier=updated_user.subscription_tier.value if updated_user.subscription_tier else "free",
                created_at=updated_user.created_at,
                updated_at=updated_user.updated_at
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user profile"
            )

    async def get_settings(self, user: User) -> UserSettingsResponse:
        """Get user settings."""
        try:
            settings = await self.settings_repo.get_by_user_id(user.id)
            
            if not settings:
                # Create default settings
                default_settings = UserSettingsModel(
                    user_id=user.id,
                    theme="dark",
                    timezone="UTC",
                    language="en",
                    terminal_preferences={},
                    ai_preferences={},
                    sync_enabled=True,
                    notifications_enabled=True
                )
                settings = await self.settings_repo.create(default_settings)
                await self.session.commit()

            return UserSettingsResponse(
                user_id=str(settings.user_id),
                theme=settings.theme,
                timezone=settings.timezone,
                language=settings.language,
                terminal_preferences=settings.terminal_preferences or {},
                ai_preferences=settings.ai_preferences or {},
                sync_enabled=settings.sync_enabled,
                notifications_enabled=settings.notifications_enabled,
                updated_at=settings.updated_at
            )

        except Exception as e:
            logger.error(f"Error getting user settings: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user settings"
            )

    async def update_settings(self, user: User, settings_data: UserSettings) -> UserSettingsResponse:
        """Update user settings."""
        try:
            existing_settings = await self.settings_repo.get_by_user_id(user.id)
            
            update_data = {
                "theme": settings_data.theme,
                "timezone": settings_data.timezone,
                "language": settings_data.language,
                "terminal_preferences": settings_data.terminal_preferences,
                "ai_preferences": settings_data.ai_preferences,
                "sync_enabled": settings_data.sync_enabled,
                "notifications_enabled": settings_data.notifications_enabled,
                "updated_at": datetime.utcnow()
            }

            if existing_settings:
                updated_settings = await self.settings_repo.update(existing_settings.id, update_data)
            else:
                # Create new settings
                new_settings = UserSettingsModel(user_id=user.id, **update_data)
                updated_settings = await self.settings_repo.create(new_settings)

            await self.session.commit()

            return UserSettingsResponse(
                user_id=str(updated_settings.user_id),
                theme=updated_settings.theme,
                timezone=updated_settings.timezone,
                language=updated_settings.language,
                terminal_preferences=updated_settings.terminal_preferences or {},
                ai_preferences=updated_settings.ai_preferences or {},
                sync_enabled=updated_settings.sync_enabled,
                notifications_enabled=updated_settings.notifications_enabled,
                updated_at=updated_settings.updated_at
            )

        except Exception as e:
            logger.error(f"Error updating user settings: {e}")
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user settings"
            )

    async def delete_account(self, user: User) -> bool:
        """Delete user account and all associated data."""
        try:
            # This would cascade delete all associated data
            await self.user_repo.delete(user.id)
            await self.session.commit()
            
            logger.info(f"User account deleted: {user.id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting user account: {e}")
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user account"
            )

    async def get_account_stats(self, user: User) -> Dict[str, Any]:
        """Get user account statistics."""
        try:
            stats = await self.user_repo.get_user_stats(user.id)
            
            return {
                "profile_completeness": self._calculate_profile_completeness(user),
                "account_age_days": (datetime.utcnow() - user.created_at).days,
                "total_sessions": stats.get("total_sessions", 0),
                "total_commands": stats.get("total_commands", 0),
                "ssh_profiles": stats.get("ssh_profiles", 0),
                "active_devices": stats.get("active_devices", 0),
                "storage_used_mb": stats.get("storage_used_mb", 0),
                "last_login": stats.get("last_login")
            }

        except Exception as e:
            logger.error(f"Error getting account stats: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get account statistics"
            )

    def _calculate_profile_completeness(self, user: User) -> int:
        """Calculate profile completeness percentage."""
        completeness = 0
        fields = [
            user.username,
            user.email,
            user.display_name
        ]
        
        completed_fields = sum(1 for field in fields if field is not None and field.strip())
        return int((completed_fields / len(fields)) * 100)