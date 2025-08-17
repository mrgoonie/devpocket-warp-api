"""
User repository for DevPocket API.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, UserSettings

from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email_or_username(self, identifier: str) -> User | None:
        """Get user by email or username."""
        result = await self.session.execute(
            select(User).where(
                or_(User.email == identifier, User.username == identifier)
            )
        )
        return result.scalar_one_or_none()

    async def get_with_settings(self, user_id: str) -> User | None:
        """Get user with settings."""
        result = await self.session.execute(
            select(User).where(User.id == user_id).options(selectinload(User.settings))
        )
        return result.scalar_one_or_none()

    async def get_with_all_relationships(self, user_id: str) -> User | None:
        """Get user with all relationships loaded."""
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.settings),
                selectinload(User.sessions),
                selectinload(User.ssh_profiles),
                selectinload(User.ssh_keys),
            )
        )
        return result.scalar_one_or_none()

    async def create_user_with_settings(
        self, email: str, username: str, password_hash: str, **kwargs: Any
    ) -> User:
        """Create a new user with default settings."""
        # Create user
        user = User(
            email=email,
            username=username,
            hashed_password=password_hash,
            **kwargs,
        )
        self.session.add(user)
        await self.session.flush()

        # Create default settings
        settings = UserSettings(user_id=user.id)
        self.session.add(settings)
        await self.session.flush()

        # Refresh to get the relationships
        await self.session.refresh(user, ["settings"])

        return user

    async def is_email_taken(
        self, email: str, exclude_user_id: str | None = None
    ) -> bool:
        """Check if email is already taken by another user."""
        query = select(func.count(User.id)).where(User.email == email)

        if exclude_user_id:
            query = query.where(User.id != exclude_user_id)

        result = await self.session.execute(query)
        count = result.scalar()
        return count is not None and count > 0

    async def is_username_taken(
        self, username: str, exclude_user_id: str | None = None
    ) -> bool:
        """Check if username is already taken by another user."""
        query = select(func.count(User.id)).where(User.username == username)

        if exclude_user_id:
            query = query.where(User.id != exclude_user_id)

        result = await self.session.execute(query)
        count = result.scalar()
        return count is not None and count > 0

    async def get_active_users(self, offset: int = 0, limit: int = 100) -> list[User]:
        """Get all active users."""
        result = await self.session.execute(
            select(User)
            .where(User.is_active is True)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_users_by_subscription(
        self, subscription_tier: str, offset: int = 0, limit: int = 100
    ) -> list[User]:
        """Get users by subscription tier."""
        result = await self.session.execute(
            select(User)
            .where(User.subscription_tier == subscription_tier)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_locked_users(self) -> list[User]:
        """Get all currently locked users."""
        now = datetime.now()
        result = await self.session.execute(
            select(User).where(
                and_(User.locked_until.is_not(None), User.locked_until > now)
            )
        )
        return list(result.scalars().all())

    async def unlock_expired_users(self) -> int:
        """Unlock users whose lock time has expired."""
        now = datetime.now()
        result = await self.session.execute(
            select(User).where(
                and_(User.locked_until.is_not(None), User.locked_until <= now)
            )
        )
        expired_users = list(result.scalars().all())

        for user in expired_users:
            user.locked_until = None
            user.failed_login_attempts = 0

        return len(expired_users)

    async def get_users_with_api_keys(
        self, offset: int = 0, limit: int = 100
    ) -> list[User]:
        """Get users who have validated API keys."""
        result = await self.session.execute(
            select(User)
            .where(User.openrouter_api_key.is_not(None))
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_users(
        self, search_term: str, offset: int = 0, limit: int = 100
    ) -> list[User]:
        """Search users by username, email, or display name."""
        search_pattern = f"%{search_term}%"
        result = await self.session.execute(
            select(User)
            .where(
                or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.full_name.ilike(search_pattern),
                )
            )
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_stats(self, user_id: str) -> dict:
        """Get comprehensive user statistics."""
        user = await self.get_with_all_relationships(user_id)
        if not user:
            return {}

        return {
            "user_id": user_id,
            "account_created": user.created_at,
            "last_login": user.last_login_at,
            "subscription_tier": user.subscription_tier,
            "total_sessions": len(user.sessions),
            "active_sessions": len([s for s in user.sessions if s.is_active]),
            "ssh_profiles_count": len(user.ssh_profiles),
            "ssh_keys_count": len(user.ssh_keys),
            "has_api_key": user.openrouter_api_key is not None,
            "last_login_at": user.last_login_at,
        }

    async def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp and reset failed attempts."""
        await self.update(
            user_id,
            last_login_at=datetime.now(),
            failed_login_attempts=0,
            locked_until=None,
        )

    async def increment_failed_login(self, user_id: str) -> User | None:
        """Increment failed login attempts and potentially lock account."""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        user.increment_failed_login()
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account."""
        updated_user = await self.update(user_id, is_active=False)
        return updated_user is not None

    async def reactivate_user(self, user_id: str) -> bool:
        """Reactivate a user account."""
        updated_user = await self.update(user_id, is_active=True)
        return updated_user is not None
