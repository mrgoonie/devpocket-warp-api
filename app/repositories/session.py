"""
Session repository for DevPocket API.
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID as PyUUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.session import Session

from .base import BaseRepository

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import BinaryExpression


class SessionRepository(BaseRepository[Session]):
    """Repository for Session model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Session, session)

    async def get_user_sessions(
        self,
        user_id: str | PyUUID,
        active_only: bool = False,
        offset: int = 0,
        limit: int = 100,
        session_type: str | None = None,
        include_inactive: bool = False,
    ) -> list[Session]:
        """Get all sessions for a user."""
        query = select(Session).where(Session.user_id == user_id)

        if active_only and not include_inactive:
            query = query.where(Session.is_active is True)

        if session_type:
            query = query.where(Session.session_type == session_type)

        query = query.order_by(desc(Session.created_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_user_active_sessions(self, user_id: str | PyUUID) -> list[Session]:
        """Get all active sessions for a user."""
        return await self.get_user_sessions(user_id, active_only=True)

    async def get_user_session_count(
        self, user_id: str | PyUUID, session_type: str | None = None
    ) -> int:
        """Get total session count for a user."""
        query = select(func.count(Session.id)).where(Session.user_id == user_id)

        if session_type:
            query = query.where(Session.session_type == session_type)

        result = await self.session.execute(query)
        count = result.scalar()
        return count or 0

    async def get_active_sessions(
        self,
        user_id: str | PyUUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Session]:
        """Get all active sessions, optionally filtered by user."""
        query = select(Session).where(Session.is_active is True)

        if user_id:
            query = query.where(Session.user_id == user_id)

        query = (
            query.order_by(desc(Session.last_activity_at)).offset(offset).limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search_sessions(
        self,
        criteria: dict[str, Any],
        search_term: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        offset: int = 0,
        limit: int = 100,
    ) -> list[Session]:
        """Search sessions with criteria."""
        query = select(Session)

        # Apply basic criteria filters
        for key, value in criteria.items():
            if hasattr(Session, key):
                query = query.where(getattr(Session, key) == value)

        # Apply search term (if provided)
        if search_term:
            search_filter = Session.session_name.ilike(f"%{search_term}%")
            query = query.where(search_filter)

        # Apply date filters
        if created_after:
            query = query.where(Session.created_at >= created_after)
        if created_before:
            query = query.where(Session.created_at <= created_before)

        # Apply sorting
        if sort_order.lower() == "desc":
            query = query.order_by(desc(getattr(Session, sort_by)))
        else:
            query = query.order_by(getattr(Session, sort_by))

        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_sessions_with_criteria(self, criteria: dict[str, Any]) -> int:
        """Count sessions matching criteria."""
        query = select(func.count(Session.id))

        # Apply criteria filters
        for key, value in criteria.items():
            if hasattr(Session, key):
                query = query.where(getattr(Session, key) == value)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_user_session_stats(self, user_id: str | PyUUID) -> dict[str, Any]:
        """Get session statistics for a user."""
        total_query = select(func.count(Session.id)).where(Session.user_id == user_id)
        active_query = select(func.count(Session.id)).where(
            and_(Session.user_id == user_id, Session.is_active is True)
        )

        total_result = await self.session.execute(total_query)
        active_result = await self.session.execute(active_query)

        return {
            "total_sessions": total_result.scalar() or 0,
            "active_sessions": active_result.scalar() or 0,
        }

    async def get_session_with_commands(
        self, session_id: str, command_limit: int = 50
    ) -> Session | None:
        """Get session with its commands loaded."""
        result = await self.session.execute(
            select(Session)
            .where(Session.id == session_id)
            .options(selectinload(Session.commands))
        )
        return result.scalar_one_or_none()

    async def get_sessions_by_device(
        self,
        user_id: str | PyUUID,
        device_id: str,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Session]:
        """Get sessions for a specific device."""
        result = await self.session.execute(
            select(Session)
            .where(and_(Session.user_id == user_id, Session.device_id == device_id))
            .order_by(desc(Session.created_at))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_sessions_by_type(
        self,
        user_id: str | PyUUID,
        session_type: str,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Session]:
        """Get sessions by type (terminal, ssh, pty)."""
        result = await self.session.execute(
            select(Session)
            .where(
                and_(
                    Session.user_id == user_id,
                    Session.session_type == session_type,
                )
            )
            .order_by(desc(Session.created_at))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_ssh_sessions(
        self,
        user_id: str | PyUUID | None = None,
        host: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Session]:
        """Get SSH sessions, optionally filtered by user or host."""

        conditions: list[BinaryExpression[bool]] = [Session.ssh_host.is_not(None)]

        if user_id:
            conditions.append(Session.user_id == user_id)  # type: ignore

        if host:
            conditions.append(Session.ssh_host == host)  # type: ignore

        result = await self.session.execute(
            select(Session)
            .where(and_(*conditions))
            .order_by(desc(Session.created_at))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_session(
        self,
        user_id: str | PyUUID,
        device_id: str,
        device_type: str,
        **kwargs: Any,
    ) -> Session:
        """Create a new session."""
        session = Session(
            user_id=user_id,
            device_id=device_id,
            device_type=device_type,
            last_activity_at=datetime.now(),
            **kwargs,
        )

        self.session.add(session)
        await self.session.flush()
        await self.session.refresh(session)

        return session

    async def create_ssh_session(
        self,
        user_id: str | PyUUID,
        device_id: str,
        device_type: str,
        ssh_host: str,
        ssh_port: int,
        ssh_username: str,
        **kwargs: Any,
    ) -> Session:
        """Create a new SSH session."""
        return await self.create_session(
            user_id=user_id,
            device_id=device_id,
            device_type=device_type,
            session_type="ssh",
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            ssh_username=ssh_username,
            **kwargs,
        )

    async def update_activity(self, session_id: str) -> Session | None:
        """Update session's last activity timestamp."""
        return await self.update(session_id, last_activity_at=datetime.now())

    async def end_session(self, session_id: str) -> Session | None:
        """End a session."""
        return await self.update(session_id, is_active=False, ended_at=datetime.now())

    async def resize_terminal(
        self, session_id: str, cols: int, rows: int
    ) -> Session | None:
        """Update terminal dimensions."""
        return await self.update(
            session_id,
            terminal_cols=cols,
            terminal_rows=rows,
            last_activity_at=datetime.now(),
        )

    async def end_inactive_sessions(self, inactive_threshold_minutes: int = 30) -> int:
        """End sessions that have been inactive for too long."""
        threshold_time = datetime.now() - timedelta(minutes=inactive_threshold_minutes)

        result = await self.session.execute(
            select(Session).where(
                and_(
                    Session.is_active is True,
                    Session.last_activity_at < threshold_time,
                )
            )
        )

        inactive_sessions = list(result.scalars().all())

        for session in inactive_sessions:
            session.is_active = False
            session.ended_at = datetime.now()

        return len(inactive_sessions)

    async def get_session_stats(self, user_id: str | PyUUID | None = None) -> dict:
        """Get session statistics."""
        base_query = select(Session)

        if user_id:
            base_query = base_query.where(Session.user_id == user_id)

        # Total sessions
        total_sessions = await self.session.execute(
            select(func.count(Session.id)).select_from(base_query.subquery())
        )

        # Active sessions
        active_sessions = await self.session.execute(
            select(func.count(Session.id)).where(
                and_(
                    Session.is_active is True,
                    Session.user_id == user_id
                    if user_id
                    else Session.user_id.is_not(None),
                )
            )
        )

        # SSH sessions
        ssh_sessions = await self.session.execute(
            select(func.count(Session.id)).where(
                and_(
                    Session.ssh_host.is_not(None),
                    Session.user_id == user_id
                    if user_id
                    else Session.user_id.is_not(None),
                )
            )
        )

        # Device types breakdown
        device_breakdown = await self.session.execute(
            select(Session.device_type, func.count(Session.id))
            .where(
                Session.user_id == user_id if user_id else Session.user_id.is_not(None)
            )
            .group_by(Session.device_type)
        )

        return {
            "total_sessions": total_sessions.scalar(),
            "active_sessions": active_sessions.scalar(),
            "ssh_sessions": ssh_sessions.scalar(),
            "device_breakdown": {row[0]: row[1] for row in device_breakdown.fetchall()},
        }

    async def get_user_device_sessions(
        self, user_id: str | PyUUID, device_type: str | None = None
    ) -> dict:
        """Get user sessions grouped by device."""
        query = select(Session).where(Session.user_id == user_id)

        if device_type:
            query = query.where(Session.device_type == device_type)

        result = await self.session.execute(query.order_by(desc(Session.created_at)))
        sessions = list(result.scalars().all())

        # Group by device_id
        devices: dict[str, dict[str, Any]] = {}
        for session in sessions:
            device_key = f"{session.device_id}_{session.device_type}"
            if device_key not in devices:
                devices[device_key] = {
                    "device_id": session.device_id,
                    "device_type": session.device_type,
                    "device_name": session.device_name,
                    "sessions": [],
                    "active_count": 0,
                    "total_count": 0,
                }

            devices[device_key]["sessions"].append(
                {
                    "id": session.id,
                    "session_type": session.session_type,
                    "is_active": session.is_active,
                    "created_at": session.created_at,
                    "last_activity_at": session.last_activity_at,
                    "ssh_host": session.ssh_host,
                }
            )

            devices[device_key]["total_count"] += 1
            if session.is_active:
                devices[device_key]["active_count"] += 1

        return devices

    async def get_user_session_by_name(
        self, user_id: str | PyUUID, session_name: str
    ) -> Session | None:
        """Get session by name for a user."""
        result = await self.session.execute(
            select(Session).where(
                and_(Session.user_id == user_id, Session.session_name == session_name)
            )
        )
        return result.scalar_one_or_none()

    async def count_user_sessions(
        self, user_id: str | PyUUID, session_type: str | None = None
    ) -> int:
        """Count total sessions for a user."""
        return await self.get_user_session_count(user_id, session_type)

    async def get_session_commands(
        self, session_id: str | PyUUID, offset: int = 0, limit: int = 100
    ) -> list[Any]:
        """Get commands for a session."""
        # This would need the Command model imported, for now return empty list
        # as the actual implementation would depend on the Command model
        return []

    async def count_session_commands(self, session_id: str | PyUUID) -> int:
        """Count commands for a session."""
        # This would need the Command model imported, for now return 0
        # as the actual implementation would depend on the Command model
        return 0

    async def cleanup_old_sessions(
        self, days_old: int = 90, keep_active: bool = True
    ) -> int:
        """Delete old sessions to save space."""
        cutoff_date = datetime.now() - timedelta(days=days_old)

        conditions: list[BinaryExpression[bool]] = [Session.created_at < cutoff_date]  # type: ignore

        if keep_active:
            conditions.append(Session.is_active is False)  # type: ignore

        result = await self.session.execute(select(Session).where(and_(*conditions)))

        old_sessions = list(result.scalars().all())

        for session in old_sessions:
            await self.session.delete(session)

        return len(old_sessions)
