"""
SSH Profile repository for DevPocket API.
"""

from typing import Optional, List, Any, Union
from uuid import UUID as PyUUID
from sqlalchemy import select, and_, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ssh_profile import SSHProfile, SSHKey
from .base import BaseRepository


class SSHProfileRepository(BaseRepository[SSHProfile]):
    """Repository for SSH Profile model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(SSHProfile, session)

    async def get_user_profiles(
        self,
        user_id: Union[str, PyUUID],
        active_only: bool = True,
        offset: int = 0,
        limit: int = 100,
    ) -> List[SSHProfile]:
        """Get SSH profiles for a user."""
        query = select(SSHProfile).where(SSHProfile.user_id == user_id)

        if active_only:
            query = query.where(SSHProfile.is_active == True)

        query = (
            query.order_by(desc(SSHProfile.last_used_at), SSHProfile.name)
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_profile_with_key(self, profile_id: str) -> Optional[SSHProfile]:
        """Get SSH profile with SSH key loaded."""
        result = await self.session.execute(
            select(SSHProfile)
            .where(SSHProfile.id == profile_id)
            .options(selectinload(SSHProfile.ssh_key))
        )
        return result.scalar_one_or_none()

    async def get_profile_by_name(
        self, user_id: Union[str, PyUUID], name: str
    ) -> Optional[SSHProfile]:
        """Get SSH profile by name for a user."""
        result = await self.session.execute(
            select(SSHProfile).where(
                and_(SSHProfile.user_id == user_id, SSHProfile.name == name)
            )
        )
        return result.scalar_one_or_none()

    async def is_profile_name_taken(
        self, user_id: str, name: str, exclude_profile_id: Optional[str] = None
    ) -> bool:
        """Check if profile name is already taken by the user."""
        query = select(func.count(SSHProfile.id)).where(
            and_(SSHProfile.user_id == user_id, SSHProfile.name == name)
        )

        if exclude_profile_id:
            query = query.where(SSHProfile.id != exclude_profile_id)

        result = await self.session.execute(query)
        count = result.scalar()
        return count is not None and count > 0

    async def create_profile(
        self,
        user_id: Union[str, PyUUID],
        name: str,
        host: str,
        username: str,
        **kwargs: Any,
    ) -> SSHProfile:
        """Create a new SSH profile."""
        profile = SSHProfile(
            user_id=user_id, name=name, host=host, username=username, **kwargs
        )

        self.session.add(profile)
        await self.session.flush()
        await self.session.refresh(profile)

        return profile

    async def record_connection_attempt(
        self, profile_id: str, success: bool
    ) -> Optional[SSHProfile]:
        """Record a connection attempt for the profile."""
        profile = await self.get_by_id(profile_id)
        if profile:
            profile.record_connection_attempt(success)
            await self.session.flush()
            await self.session.refresh(profile)
        return profile

    async def get_profiles_by_host(
        self,
        host: str,
        user_id: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[SSHProfile]:
        """Get profiles connecting to a specific host."""
        query = select(SSHProfile).where(SSHProfile.host == host)

        if user_id:
            query = query.where(SSHProfile.user_id == user_id)

        query = (
            query.order_by(desc(SSHProfile.last_used_at)).offset(offset).limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_most_used_profiles(
        self, user_id: Union[str, PyUUID], limit: int = 10
    ) -> List[SSHProfile]:
        """Get most frequently used SSH profiles."""
        result = await self.session.execute(
            select(SSHProfile)
            .where(SSHProfile.user_id == user_id)
            .order_by(desc(SSHProfile.connection_count))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_profiles(
        self,
        user_id: Union[str, PyUUID],
        search_term: str,
        offset: int = 0,
        limit: int = 100,
    ) -> List[SSHProfile]:
        """Search SSH profiles by name, host, or username."""
        search_pattern = f"%{search_term}%"
        result = await self.session.execute(
            select(SSHProfile)
            .where(
                and_(
                    SSHProfile.user_id == user_id,
                    or_(
                        SSHProfile.name.ilike(search_pattern),
                        SSHProfile.host.ilike(search_pattern),
                        SSHProfile.username.ilike(search_pattern),
                        SSHProfile.description.ilike(search_pattern),
                    ),
                )
            )
            .order_by(SSHProfile.name)
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def deactivate_profile(self, profile_id: str) -> Optional[SSHProfile]:
        """Deactivate an SSH profile."""
        return await self.update(profile_id, is_active=False)

    async def reactivate_profile(self, profile_id: str) -> Optional[SSHProfile]:
        """Reactivate an SSH profile."""
        return await self.update(profile_id, is_active=True)


class SSHKeyRepository(BaseRepository[SSHKey]):
    """Repository for SSH Key model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(SSHKey, session)

    async def get_user_keys(
        self,
        user_id: Union[str, PyUUID],
        active_only: bool = True,
        offset: int = 0,
        limit: int = 100,
    ) -> List[SSHKey]:
        """Get SSH keys for a user."""
        query = select(SSHKey).where(SSHKey.user_id == user_id)

        if active_only:
            query = query.where(SSHKey.is_active == True)

        query = (
            query.order_by(desc(SSHKey.last_used_at), SSHKey.name)
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_key_by_fingerprint(self, fingerprint: str) -> Optional[SSHKey]:
        """Get SSH key by fingerprint."""
        result = await self.session.execute(
            select(SSHKey).where(SSHKey.fingerprint == fingerprint)
        )
        return result.scalar_one_or_none()

    async def get_key_by_name(
        self, user_id: Union[str, PyUUID], name: str
    ) -> Optional[SSHKey]:
        """Get SSH key by name for a user."""
        result = await self.session.execute(
            select(SSHKey).where(and_(SSHKey.user_id == user_id, SSHKey.name == name))
        )
        return result.scalar_one_or_none()

    async def is_key_name_taken(
        self, user_id: str, name: str, exclude_key_id: Optional[str] = None
    ) -> bool:
        """Check if key name is already taken by the user."""
        query = select(func.count(SSHKey.id)).where(
            and_(SSHKey.user_id == user_id, SSHKey.name == name)
        )

        if exclude_key_id:
            query = query.where(SSHKey.id != exclude_key_id)

        result = await self.session.execute(query)
        count = result.scalar()
        return count is not None and count > 0

    async def is_fingerprint_exists(
        self, fingerprint: str, exclude_key_id: Optional[str] = None
    ) -> bool:
        """Check if fingerprint already exists."""
        query = select(func.count(SSHKey.id)).where(SSHKey.fingerprint == fingerprint)

        if exclude_key_id:
            query = query.where(SSHKey.id != exclude_key_id)

        result = await self.session.execute(query)
        count = result.scalar()
        return count is not None and count > 0

    async def create_key(
        self,
        user_id: Union[str, PyUUID],
        name: str,
        key_type: str,
        encrypted_private_key: bytes,
        public_key: str,
        **kwargs: Any,
    ) -> SSHKey:
        """Create a new SSH key."""
        key = SSHKey(
            user_id=user_id,
            name=name,
            key_type=key_type,
            encrypted_private_key=encrypted_private_key,
            public_key=public_key,
            **kwargs,
        )

        # Generate fingerprint
        key.fingerprint = key.generate_fingerprint()

        self.session.add(key)
        await self.session.flush()
        await self.session.refresh(key)

        return key

    async def record_key_usage(self, key_id: str) -> Optional[SSHKey]:
        """Record usage of an SSH key."""
        key = await self.get_by_id(key_id)
        if key:
            key.record_usage()
            await self.session.flush()
            await self.session.refresh(key)
        return key

    async def get_keys_by_type(
        self,
        user_id: Union[str, PyUUID],
        key_type: str,
        offset: int = 0,
        limit: int = 100,
    ) -> List[SSHKey]:
        """Get SSH keys by type."""
        result = await self.session.execute(
            select(SSHKey)
            .where(and_(SSHKey.user_id == user_id, SSHKey.key_type == key_type))
            .order_by(desc(SSHKey.created_at))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_most_used_keys(
        self, user_id: Union[str, PyUUID], limit: int = 10
    ) -> List[SSHKey]:
        """Get most frequently used SSH keys."""
        result = await self.session.execute(
            select(SSHKey)
            .where(SSHKey.user_id == user_id)
            .order_by(desc(SSHKey.usage_count))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_keys(
        self,
        user_id: Union[str, PyUUID],
        search_term: str,
        offset: int = 0,
        limit: int = 100,
    ) -> List[SSHKey]:
        """Search SSH keys by name, comment, or fingerprint."""
        search_pattern = f"%{search_term}%"
        result = await self.session.execute(
            select(SSHKey)
            .where(
                and_(
                    SSHKey.user_id == user_id,
                    or_(
                        SSHKey.name.ilike(search_pattern),
                        SSHKey.comment.ilike(search_pattern),
                        SSHKey.fingerprint.ilike(search_pattern),
                    ),
                )
            )
            .order_by(SSHKey.name)
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def deactivate_key(self, key_id: str) -> Optional[SSHKey]:
        """Deactivate an SSH key."""
        return await self.update(key_id, is_active=False)

    async def reactivate_key(self, key_id: str) -> Optional[SSHKey]:
        """Reactivate an SSH key."""
        return await self.update(key_id, is_active=True)

    async def get_key_stats(self, user_id: Union[str, PyUUID, None] = None) -> dict:
        """Get SSH key statistics."""
        base_query = select(SSHKey)

        if user_id:
            base_query = base_query.where(SSHKey.user_id == user_id)

        # Total keys
        total_keys = await self.session.execute(
            select(func.count(SSHKey.id)).select_from(base_query.subquery())
        )

        # Keys by type
        type_breakdown = await self.session.execute(
            select(SSHKey.key_type, func.count(SSHKey.id))
            .select_from(base_query.subquery())
            .group_by(SSHKey.key_type)
        )

        # Active keys
        active_keys = await self.session.execute(
            select(func.count(SSHKey.id))
            .select_from(base_query.subquery())
            .where(SSHKey.is_active == True)
        )

        return {
            "total_keys": total_keys.scalar(),
            "active_keys": active_keys.scalar(),
            "type_breakdown": {row[0]: row[1] for row in type_breakdown.fetchall()},
        }
