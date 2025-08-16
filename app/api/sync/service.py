"""
Multi-device synchronization service for DevPocket API.
"""

from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.logging import logger
from app.models.user import User
from app.models.sync import SyncData
from app.repositories.sync import SyncDataRepository
from .schemas import SyncDataRequest, SyncDataResponse, SyncStats


class SyncService:
    """Service class for multi-device synchronization."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sync_repo = SyncDataRepository(session)

    async def sync_data(self, user: User, request: SyncDataRequest) -> SyncDataResponse:
        """Synchronize data across devices."""
        try:
            # Get data based on last sync timestamp
            sync_data = await self.sync_repo.get_sync_changes_since(
                user.id, request.last_sync_timestamp
            )

            # Organize data by type
            organized_data: Dict[str, Any] = {}
            for data_type in request.data_types:
                organized_data[data_type.value] = []

            total_items = len(sync_data)
            conflicts = []  # Would detect conflicts here

            # Get device count
            device_count = await self.sync_repo.count_user_devices(user.id)

            return SyncDataResponse(
                data=organized_data,
                sync_timestamp=datetime.now(timezone.utc),
                total_items=total_items,
                conflicts=conflicts,
                device_count=device_count,
            )

        except Exception as e:
            logger.error(f"Error syncing data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to synchronize data",
            )

    async def upload_sync_data(self, user: User, data: Dict[str, Any]) -> bool:
        """Upload synchronization data from device."""
        try:
            # Process and store sync data
            sync_record = SyncData(
                user_id=user.id,
                data_type="upload",
                data_content=data,
                sync_timestamp=datetime.now(timezone.utc),
            )

            await self.sync_repo.create(sync_record)
            await self.session.commit()

            return True

        except Exception as e:
            logger.error(f"Error uploading sync data: {e}")
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload sync data",
            )

    async def get_sync_stats(self, user: User) -> SyncStats:
        """Get synchronization statistics."""
        try:
            stats = await self.sync_repo.get_sync_stats(user.id)

            return SyncStats(
                total_syncs=stats.get("total_syncs", 0),
                successful_syncs=stats.get("successful_syncs", 0),
                failed_syncs=stats.get("failed_syncs", 0),
                last_sync=stats.get("last_sync"),
                active_devices=stats.get("active_devices", 0),
                total_conflicts=stats.get("total_conflicts", 0),
                resolved_conflicts=stats.get("resolved_conflicts", 0),
            )

        except Exception as e:
            logger.error(f"Error getting sync stats: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get sync statistics",
            )
