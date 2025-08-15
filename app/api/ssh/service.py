"""
SSH service layer for DevPocket API.

Contains business logic for SSH profile and key management,
connection testing, and related operations.
"""

import asyncio
import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.core.logging import logger
from app.models.user import User
from app.models.ssh_profile import SSHProfile, SSHKey
from app.repositories.ssh_profile import SSHProfileRepository, SSHKeyRepository
from app.services.ssh_client import SSHClientService
from .schemas import (
    SSHProfileCreate,
    SSHProfileUpdate,
    SSHProfileResponse,
    SSHKeyCreate,
    SSHKeyUpdate,
    SSHKeyResponse,
    SSHConnectionTestRequest,
    SSHConnectionTestResponse,
    SSHProfileSearchRequest,
    SSHKeySearchRequest,
    SSHProfileStats,
    SSHKeyStats,
)


class SSHProfileService:
    """Service class for SSH profile management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.profile_repo = SSHProfileRepository(session)
        self.key_repo = SSHKeyRepository(session)
        self.ssh_client = SSHClientService()

    async def create_profile(
        self, user: User, profile_data: SSHProfileCreate
    ) -> SSHProfileResponse:
        """Create a new SSH profile."""
        try:
            # Check if profile name already exists for user
            existing_profile = await self.profile_repo.get_profile_by_name(
                user.id, profile_data.name
            )
            if existing_profile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Profile with name '{profile_data.name}' already exists",
                )

            # Create the profile
            profile = await self.profile_repo.create_profile(
                user_id=user.id,
                name=profile_data.name,
                host=profile_data.host,
                port=profile_data.port,
                username=profile_data.username,
                description=profile_data.description,
                connect_timeout=profile_data.connect_timeout,
                keepalive_interval=profile_data.keepalive_interval,
                max_retries=profile_data.max_retries,
                terminal_type=profile_data.terminal_type,
                environment=profile_data.environment or {},
                compression=profile_data.compression,
                forward_agent=profile_data.forward_agent,
                forward_x11=profile_data.forward_x11,
            )

            await self.session.commit()

            logger.info(f"SSH profile created: {profile.name} by user {user.username}")
            return SSHProfileResponse.model_validate(profile)

        except HTTPException:
            raise
        except IntegrityError as e:
            await self.session.rollback()
            logger.warning(f"Integrity error creating SSH profile: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile with this name already exists",
            )
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating SSH profile: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create SSH profile",
            )

    async def get_user_profiles(
        self, user: User, active_only: bool = True, offset: int = 0, limit: int = 50
    ) -> Tuple[List[SSHProfileResponse], int]:
        """Get SSH profiles for a user with pagination."""
        try:
            profiles = await self.profile_repo.get_user_profiles(
                user.id, active_only=active_only, offset=offset, limit=limit
            )

            # Get total count for pagination
            # Note: This is a simplified count - in production, you'd want a more efficient method
            all_profiles = await self.profile_repo.get_user_profiles(
                user.id, active_only=active_only, offset=0, limit=1000
            )
            total = len(all_profiles)

            profile_responses = [
                SSHProfileResponse.model_validate(profile) for profile in profiles
            ]

            return profile_responses, total

        except Exception as e:
            logger.error(f"Error fetching user SSH profiles: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch SSH profiles",
            )

    async def get_profile(self, user: User, profile_id: str) -> SSHProfileResponse:
        """Get a specific SSH profile."""
        profile = await self.profile_repo.get_by_id(profile_id)

        if not profile or profile.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="SSH profile not found"
            )

        return SSHProfileResponse.model_validate(profile)

    async def update_profile(
        self, user: User, profile_id: str, update_data: SSHProfileUpdate
    ) -> SSHProfileResponse:
        """Update an SSH profile."""
        try:
            profile = await self.profile_repo.get_by_id(profile_id)

            if not profile or profile.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="SSH profile not found",
                )

            # Check if name is being changed and if new name already exists
            if update_data.name and update_data.name != profile.name:
                existing_profile = await self.profile_repo.get_profile_by_name(
                    user.id, update_data.name
                )
                if existing_profile and existing_profile.id != profile_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Profile with name '{update_data.name}' already exists",
                    )

            # Update the profile
            update_dict = update_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(profile, field, value)

            profile.updated_at = datetime.utcnow()
            updated_profile = await self.profile_repo.update(profile)
            await self.session.commit()

            logger.info(f"SSH profile updated: {profile.name} by user {user.username}")
            return SSHProfileResponse.model_validate(updated_profile)

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating SSH profile: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update SSH profile",
            )

    async def delete_profile(self, user: User, profile_id: str) -> bool:
        """Delete an SSH profile."""
        try:
            profile = await self.profile_repo.get_by_id(profile_id)

            if not profile or profile.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="SSH profile not found",
                )

            await self.profile_repo.delete(profile_id)
            await self.session.commit()

            logger.info(f"SSH profile deleted: {profile.name} by user {user.username}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting SSH profile: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete SSH profile",
            )

    async def test_connection(
        self, user: User, test_request: SSHConnectionTestRequest
    ) -> SSHConnectionTestResponse:
        """Test SSH connection."""
        start_time = time.time()

        try:
            # Prepare connection parameters
            if test_request.profile_id:
                profile = await self.profile_repo.get_by_id(test_request.profile_id)
                if not profile or profile.user_id != user.id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="SSH profile not found",
                    )

                host = profile.host
                port = profile.port
                username = profile.username
                timeout = test_request.connect_timeout

            else:
                if not all([test_request.host, test_request.username]):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Host and username are required when not using a profile",
                    )

                host = test_request.host
                port = test_request.port or 22
                username = test_request.username
                timeout = test_request.connect_timeout

            # Get SSH key if specified
            ssh_key = None
            if test_request.ssh_key_id:
                ssh_key = await self.key_repo.get_by_id(test_request.ssh_key_id)
                if not ssh_key or ssh_key.user_id != user.id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="SSH key not found",
                    )

            # Perform connection test
            test_result = await self.ssh_client.test_connection(
                host=host,
                port=port,
                username=username,
                ssh_key=ssh_key,
                password=test_request.password
                if test_request.auth_method == "password"
                else None,
                timeout=timeout,
            )

            # Record connection attempt if using a profile
            if test_request.profile_id:
                await self.profile_repo.record_connection_attempt(
                    test_request.profile_id, test_result["success"]
                )
                if test_result["success"]:
                    profile.last_connection_status = "connected"
                    profile.last_successful_connection_at = datetime.utcnow()
                else:
                    profile.last_connection_status = "connection_failed"
                    profile.last_error_message = test_result.get("error_message")

                profile.last_connection_at = datetime.utcnow()
                await self.session.commit()

            duration_ms = int((time.time() - start_time) * 1000)

            return SSHConnectionTestResponse(
                success=test_result["success"],
                message=test_result["message"],
                details=test_result.get("details"),
                duration_ms=duration_ms,
                server_info=test_result.get("server_info"),
                timestamp=datetime.utcnow(),
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error testing SSH connection: {e}")
            duration_ms = int((time.time() - start_time) * 1000)

            return SSHConnectionTestResponse(
                success=False,
                message=f"Connection test failed: {str(e)}",
                details={"error": str(e)},
                duration_ms=duration_ms,
                server_info=None,
                timestamp=datetime.utcnow(),
            )

    async def search_profiles(
        self, user: User, search_request: SSHProfileSearchRequest
    ) -> Tuple[List[SSHProfileResponse], int]:
        """Search SSH profiles with filters."""
        try:
            if search_request.search_term:
                profiles = await self.profile_repo.search_profiles(
                    user.id,
                    search_request.search_term,
                    offset=search_request.offset,
                    limit=search_request.limit,
                )
            else:
                profiles = await self.profile_repo.get_user_profiles(
                    user.id,
                    active_only=search_request.active_only,
                    offset=search_request.offset,
                    limit=search_request.limit,
                )

            # Apply additional filters
            if search_request.host_filter:
                profiles = [
                    p
                    for p in profiles
                    if search_request.host_filter.lower() in p.host.lower()
                ]

            # TODO: Implement sorting logic based on search_request.sort_by and sort_order

            profile_responses = [
                SSHProfileResponse.model_validate(profile) for profile in profiles
            ]

            # Get total count (simplified)
            total = len(profile_responses)

            return profile_responses, total

        except Exception as e:
            logger.error(f"Error searching SSH profiles: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to search SSH profiles",
            )

    async def get_profile_stats(self, user: User) -> SSHProfileStats:
        """Get SSH profile statistics for user."""
        try:
            all_profiles = await self.profile_repo.get_user_profiles(
                user.id, active_only=False, offset=0, limit=1000
            )

            active_profiles = [p for p in all_profiles if p.is_active]

            # Count profiles by status
            status_counts = {}
            for profile in all_profiles:
                status = profile.last_connection_status or "never_connected"
                status_counts[status] = status_counts.get(status, 0) + 1

            # Get most used profiles
            most_used = await self.profile_repo.get_most_used_profiles(user.id, limit=5)
            most_used_responses = [
                SSHProfileResponse.model_validate(profile) for profile in most_used
            ]

            # Get recent connections (simplified)
            recent_connections = []
            for profile in all_profiles[:10]:
                if profile.last_connection_at:
                    recent_connections.append(
                        {
                            "profile_id": profile.id,
                            "profile_name": profile.name,
                            "host": profile.host,
                            "status": profile.last_connection_status,
                            "timestamp": profile.last_connection_at.isoformat(),
                            "success": profile.last_connection_status == "connected",
                        }
                    )

            return SSHProfileStats(
                total_profiles=len(all_profiles),
                active_profiles=len(active_profiles),
                profiles_by_status=status_counts,
                most_used_profiles=most_used_responses,
                recent_connections=recent_connections,
            )

        except Exception as e:
            logger.error(f"Error getting SSH profile stats: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get SSH profile statistics",
            )


class SSHKeyService:
    """Service class for SSH key management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.key_repo = SSHKeyRepository(session)

    async def create_key(self, user: User, key_data: SSHKeyCreate) -> SSHKeyResponse:
        """Create a new SSH key."""
        try:
            # Check if key name already exists for user
            existing_key = await self.key_repo.get_key_by_name(user.id, key_data.name)
            if existing_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"SSH key with name '{key_data.name}' already exists",
                )

            # Encrypt the private key (simplified - use proper encryption in production)
            encrypted_private_key = key_data.private_key.encode("utf-8")

            # Create the SSH key
            ssh_key = await self.key_repo.create_key(
                user_id=user.id,
                name=key_data.name,
                key_type=key_data.key_type.value,
                encrypted_private_key=encrypted_private_key,
                public_key=key_data.public_key,
                comment=key_data.comment,
                passphrase_protected=key_data.passphrase_protected,
            )

            await self.session.commit()

            logger.info(f"SSH key created: {ssh_key.name} by user {user.username}")
            return SSHKeyResponse.model_validate(ssh_key)

        except HTTPException:
            raise
        except IntegrityError as e:
            await self.session.rollback()
            logger.warning(f"Integrity error creating SSH key: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SSH key with this name or fingerprint already exists",
            )
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating SSH key: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create SSH key",
            )

    async def get_user_keys(
        self, user: User, active_only: bool = True, offset: int = 0, limit: int = 50
    ) -> Tuple[List[SSHKeyResponse], int]:
        """Get SSH keys for a user with pagination."""
        try:
            keys = await self.key_repo.get_user_keys(
                user.id, active_only=active_only, offset=offset, limit=limit
            )

            # Get total count (simplified)
            all_keys = await self.key_repo.get_user_keys(
                user.id, active_only=active_only, offset=0, limit=1000
            )
            total = len(all_keys)

            key_responses = [SSHKeyResponse.model_validate(key) for key in keys]

            return key_responses, total

        except Exception as e:
            logger.error(f"Error fetching user SSH keys: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch SSH keys",
            )

    async def get_key(self, user: User, key_id: str) -> SSHKeyResponse:
        """Get a specific SSH key."""
        key = await self.key_repo.get_by_id(key_id)

        if not key or key.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="SSH key not found"
            )

        return SSHKeyResponse.model_validate(key)

    async def update_key(
        self, user: User, key_id: str, update_data: SSHKeyUpdate
    ) -> SSHKeyResponse:
        """Update an SSH key."""
        try:
            key = await self.key_repo.get_by_id(key_id)

            if not key or key.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="SSH key not found"
                )

            # Check if name is being changed and if new name already exists
            if update_data.name and update_data.name != key.name:
                existing_key = await self.key_repo.get_key_by_name(
                    user.id, update_data.name
                )
                if existing_key and existing_key.id != key_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"SSH key with name '{update_data.name}' already exists",
                    )

            # Update the key
            update_dict = update_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(key, field, value)

            key.updated_at = datetime.utcnow()
            updated_key = await self.key_repo.update(key)
            await self.session.commit()

            logger.info(f"SSH key updated: {key.name} by user {user.username}")
            return SSHKeyResponse.model_validate(updated_key)

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating SSH key: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update SSH key",
            )

    async def delete_key(self, user: User, key_id: str) -> bool:
        """Delete an SSH key."""
        try:
            key = await self.key_repo.get_by_id(key_id)

            if not key or key.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="SSH key not found"
                )

            await self.key_repo.delete(key_id)
            await self.session.commit()

            logger.info(f"SSH key deleted: {key.name} by user {user.username}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting SSH key: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete SSH key",
            )

    async def search_keys(
        self, user: User, search_request: SSHKeySearchRequest
    ) -> Tuple[List[SSHKeyResponse], int]:
        """Search SSH keys with filters."""
        try:
            if search_request.search_term:
                keys = await self.key_repo.search_keys(
                    user.id,
                    search_request.search_term,
                    offset=search_request.offset,
                    limit=search_request.limit,
                )
            else:
                keys = await self.key_repo.get_user_keys(
                    user.id,
                    active_only=search_request.active_only,
                    offset=search_request.offset,
                    limit=search_request.limit,
                )

            # Apply additional filters
            if search_request.key_type_filter:
                keys = [
                    k
                    for k in keys
                    if k.key_type == search_request.key_type_filter.value
                ]

            # TODO: Implement sorting logic

            key_responses = [SSHKeyResponse.model_validate(key) for key in keys]

            total = len(key_responses)

            return key_responses, total

        except Exception as e:
            logger.error(f"Error searching SSH keys: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to search SSH keys",
            )

    async def get_key_stats(self, user: User) -> SSHKeyStats:
        """Get SSH key statistics for user."""
        try:
            # Get key statistics from repository
            stats = await self.key_repo.get_key_stats(user.id)

            # Get most used keys
            most_used = await self.key_repo.get_most_used_keys(user.id, limit=5)
            most_used_responses = [
                SSHKeyResponse.model_validate(key) for key in most_used
            ]

            return SSHKeyStats(
                total_keys=stats["total_keys"],
                active_keys=stats["active_keys"],
                keys_by_type=stats["type_breakdown"],
                most_used_keys=most_used_responses,
            )

        except Exception as e:
            logger.error(f"Error getting SSH key stats: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get SSH key statistics",
            )
