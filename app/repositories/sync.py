"""
Sync data repository for DevPocket API.
"""

from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync import SyncData
from .base import BaseRepository


class SyncDataRepository(BaseRepository[SyncData]):
    """Repository for SyncData model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(SyncData, session)

    async def get_user_sync_data(
        self,
        user_id: str,
        sync_type: str = None,
        include_deleted: bool = False,
        offset: int = 0,
        limit: int = 100,
    ) -> List[SyncData]:
        """Get sync data for a user."""
        query = select(SyncData).where(SyncData.user_id == user_id)

        if sync_type:
            query = query.where(SyncData.sync_type == sync_type)

        if not include_deleted:
            query = query.where(SyncData.is_deleted == False)

        query = (
            query.order_by(desc(SyncData.last_modified_at)).offset(offset).limit(limit)
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_sync_item(
        self, user_id: str, sync_type: str, sync_key: str
    ) -> Optional[SyncData]:
        """Get a specific sync item."""
        result = await self.session.execute(
            select(SyncData).where(
                and_(
                    SyncData.user_id == user_id,
                    SyncData.sync_type == sync_type,
                    SyncData.sync_key == sync_key,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_or_update_sync_item(
        self,
        user_id: str,
        sync_type: str,
        sync_key: str,
        data: dict,
        device_id: str,
        device_type: str,
    ) -> SyncData:
        """Create or update a sync item."""
        existing_item = await self.get_sync_item(user_id, sync_type, sync_key)

        if existing_item:
            # Check for conflicts
            if (
                existing_item.last_modified_at > datetime.now() - timedelta(seconds=1)
                and existing_item.source_device_id != device_id
                and existing_item.data != data
            ):
                # Potential conflict
                existing_item.create_conflict(data)
            else:
                # No conflict, update normally
                existing_item.update_data(data, device_id, device_type)

            await self.session.flush()
            await self.session.refresh(existing_item)
            return existing_item
        else:
            # Create new item
            new_item = SyncData.create_sync_item(
                user_id, sync_type, sync_key, data, device_id, device_type
            )
            self.session.add(new_item)
            await self.session.flush()
            await self.session.refresh(new_item)
            return new_item

    async def delete_sync_item(
        self,
        user_id: str,
        sync_type: str,
        sync_key: str,
        device_id: str,
        device_type: str,
        hard_delete: bool = False,
    ) -> bool:
        """Delete or mark as deleted a sync item."""
        sync_item = await self.get_sync_item(user_id, sync_type, sync_key)

        if not sync_item:
            return False

        if hard_delete:
            await self.session.delete(sync_item)
        else:
            sync_item.mark_as_deleted(device_id, device_type)

        await self.session.flush()
        return True

    async def get_conflicted_items(
        self, user_id: str, sync_type: str = None
    ) -> List[SyncData]:
        """Get sync items with unresolved conflicts."""
        query = select(SyncData).where(
            and_(
                SyncData.user_id == user_id,
                SyncData.conflict_data.is_not(None),
                SyncData.resolved_at.is_(None),
            )
        )

        if sync_type:
            query = query.where(SyncData.sync_type == sync_type)

        query = query.order_by(desc(SyncData.last_modified_at))

        result = await self.session.execute(query)
        return result.scalars().all()

    async def resolve_conflict(
        self, sync_id: str, chosen_data: dict, device_id: str, device_type: str
    ) -> Optional[SyncData]:
        """Resolve a sync conflict."""
        sync_item = await self.get_by_id(sync_id)

        if sync_item and sync_item.has_conflict:
            sync_item.resolve_conflict(chosen_data, device_id, device_type)
            await self.session.flush()
            await self.session.refresh(sync_item)

        return sync_item

    async def get_sync_changes_since(
        self,
        user_id: str,
        since: datetime,
        sync_type: str = None,
        device_id: str = None,
    ) -> List[SyncData]:
        """Get sync changes since a specific timestamp."""
        query = select(SyncData).where(
            and_(SyncData.user_id == user_id, SyncData.last_modified_at > since)
        )

        if sync_type:
            query = query.where(SyncData.sync_type == sync_type)

        if device_id:
            # Exclude changes from the requesting device to avoid loops
            query = query.where(SyncData.source_device_id != device_id)

        query = query.order_by(SyncData.last_modified_at)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_device_sync_data(
        self,
        user_id: str,
        device_id: str,
        sync_type: str = None,
        limit_hours: int = 24,
    ) -> List[SyncData]:
        """Get sync data from a specific device."""
        since_time = datetime.now() - timedelta(hours=limit_hours)

        query = select(SyncData).where(
            and_(
                SyncData.user_id == user_id,
                SyncData.source_device_id == device_id,
                SyncData.last_modified_at >= since_time,
            )
        )

        if sync_type:
            query = query.where(SyncData.sync_type == sync_type)

        query = query.order_by(desc(SyncData.last_modified_at))

        result = await self.session.execute(query)
        return result.scalars().all()

    async def bulk_sync_create(
        self,
        user_id: str,
        sync_items: List[dict],
        device_id: str,
        device_type: str,
    ) -> List[SyncData]:
        """Bulk create/update sync items."""
        created_items = []

        for item_data in sync_items:
            sync_item = await self.create_or_update_sync_item(
                user_id=user_id,
                sync_type=item_data["sync_type"],
                sync_key=item_data["sync_key"],
                data=item_data["data"],
                device_id=device_id,
                device_type=device_type,
            )
            created_items.append(sync_item)

        return created_items

    async def get_sync_stats(self, user_id: str) -> dict:
        """Get sync statistics for a user."""
        # Total items
        total_items = await self.session.execute(
            select(func.count(SyncData.id)).where(SyncData.user_id == user_id)
        )

        # Items by type
        type_breakdown = await self.session.execute(
            select(SyncData.sync_type, func.count(SyncData.id))
            .where(SyncData.user_id == user_id)
            .group_by(SyncData.sync_type)
        )

        # Conflicted items
        conflicted_items = await self.session.execute(
            select(func.count(SyncData.id)).where(
                and_(
                    SyncData.user_id == user_id,
                    SyncData.conflict_data.is_not(None),
                    SyncData.resolved_at.is_(None),
                )
            )
        )

        # Deleted items
        deleted_items = await self.session.execute(
            select(func.count(SyncData.id)).where(
                and_(SyncData.user_id == user_id, SyncData.is_deleted == True)
            )
        )

        # Device breakdown
        device_breakdown = await self.session.execute(
            select(SyncData.source_device_type, func.count(SyncData.id))
            .where(SyncData.user_id == user_id)
            .group_by(SyncData.source_device_type)
        )

        return {
            "total_items": total_items.scalar(),
            "type_breakdown": dict(type_breakdown.fetchall()),
            "conflicted_items": conflicted_items.scalar(),
            "deleted_items": deleted_items.scalar(),
            "device_breakdown": dict(device_breakdown.fetchall()),
        }

    async def cleanup_old_sync_data(
        self, user_id: str = None, days_old: int = 90, sync_type: str = None
    ) -> int:
        """Clean up old sync data."""
        cutoff_date = datetime.now() - timedelta(days=days_old)

        conditions = [
            SyncData.last_modified_at < cutoff_date,
            SyncData.is_deleted == True,
        ]

        if user_id:
            conditions.append(SyncData.user_id == user_id)

        if sync_type:
            conditions.append(SyncData.sync_type == sync_type)

        result = await self.session.execute(select(SyncData).where(and_(*conditions)))

        old_items = result.scalars().all()

        for item in old_items:
            await self.session.delete(item)

        return len(old_items)

    async def get_recent_activity(
        self, user_id: str, hours: int = 24, limit: int = 50
    ) -> List[SyncData]:
        """Get recent sync activity for a user."""
        since_time = datetime.now() - timedelta(hours=hours)

        result = await self.session.execute(
            select(SyncData)
            .where(
                and_(
                    SyncData.user_id == user_id,
                    SyncData.last_modified_at >= since_time,
                )
            )
            .order_by(desc(SyncData.last_modified_at))
            .limit(limit)
        )

        return result.scalars().all()

    async def export_user_sync_data(self, user_id: str, sync_type: str = None) -> dict:
        """Export all sync data for a user."""
        query = select(SyncData).where(
            and_(SyncData.user_id == user_id, SyncData.is_deleted == False)
        )

        if sync_type:
            query = query.where(SyncData.sync_type == sync_type)

        result = await self.session.execute(query)
        items = result.scalars().all()

        export_data = {}
        for item in items:
            if item.sync_type not in export_data:
                export_data[item.sync_type] = {}
            export_data[item.sync_type][item.sync_key] = {
                "data": item.data,
                "version": item.version,
                "last_modified": item.last_modified_at.isoformat(),
                "source_device": {
                    "device_id": item.source_device_id,
                    "device_type": item.source_device_type,
                },
            }

        return export_data
