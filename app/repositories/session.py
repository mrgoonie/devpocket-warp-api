"""
Session repository for DevPocket API.
"""

from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.session import Session
from .base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    """Repository for Session model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Session, session)

    async def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = False,
        offset: int = 0,
        limit: int = 100,
        session_type: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[Session]:
        """Get all sessions for a user."""
        query = select(Session).where(Session.user_id == user_id)

        if active_only and not include_inactive:
            query = query.where(Session.is_active == True)

        if session_type:
            query = query.where(Session.session_type == session_type)

        query = query.order_by(desc(Session.created_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_user_active_sessions(self, user_id: str) -> List[Session]:
        """Get all active sessions for a user."""
        return await self.get_user_sessions(user_id, active_only=True)

    async def get_user_session_count(
        self, user_id: str, session_type: Optional[str] = None
    ) -> int:
        """Get total session count for a user."""
        query = select(func.count(Session.id)).where(Session.user_id == user_id)

        if session_type:
            query = query.where(Session.session_type == session_type)

        result = await self.session.execute(query)
        return result.scalar()

    async def get_active_sessions(
        self, user_id: str = None, offset: int = 0, limit: int = 100
    ) -> List[Session]:
        """Get all active sessions, optionally filtered by user."""
        query = select(Session).where(Session.is_active == True)

        if user_id:
            query = query.where(Session.user_id == user_id)

        query = (
            query.order_by(desc(Session.last_activity_at)).offset(offset).limit(limit)
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_session_with_commands(
        self, session_id: str, command_limit: int = 50
    ) -> Optional[Session]:
        """Get session with its commands loaded."""
        result = await self.session.execute(
            select(Session)
            .where(Session.id == session_id)
            .options(selectinload(Session.commands).limit(command_limit))
        )
        return result.scalar_one_or_none()

    async def get_sessions_by_device(
        self, user_id: str, device_id: str, offset: int = 0, limit: int = 100
    ) -> List[Session]:
        """Get sessions for a specific device."""
        result = await self.session.execute(
            select(Session)
            .where(and_(Session.user_id == user_id, Session.device_id == device_id))
            .order_by(desc(Session.created_at))
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_sessions_by_type(
        self, user_id: str, session_type: str, offset: int = 0, limit: int = 100
    ) -> List[Session]:
        """Get sessions by type (terminal, ssh, pty)."""
        result = await self.session.execute(
            select(Session)
            .where(
                and_(Session.user_id == user_id, Session.session_type == session_type)
            )
            .order_by(desc(Session.created_at))
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_ssh_sessions(
        self, user_id: str = None, host: str = None, offset: int = 0, limit: int = 100
    ) -> List[Session]:
        """Get SSH sessions, optionally filtered by user or host."""
        conditions = [Session.ssh_host.is_not(None)]

        if user_id:
            conditions.append(Session.user_id == user_id)

        if host:
            conditions.append(Session.ssh_host == host)

        result = await self.session.execute(
            select(Session)
            .where(and_(*conditions))
            .order_by(desc(Session.created_at))
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def create_session(
        self, user_id: str, device_id: str, device_type: str, **kwargs
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
        user_id: str,
        device_id: str,
        device_type: str,
        ssh_host: str,
        ssh_port: int,
        ssh_username: str,
        **kwargs,
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

    async def update_activity(self, session_id: str) -> Optional[Session]:
        """Update session's last activity timestamp."""
        return await self.update(session_id, last_activity_at=datetime.now())

    async def end_session(self, session_id: str) -> Optional[Session]:
        """End a session."""
        return await self.update(session_id, is_active=False, ended_at=datetime.now())

    async def resize_terminal(
        self, session_id: str, cols: int, rows: int
    ) -> Optional[Session]:
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
                    Session.is_active == True, Session.last_activity_at < threshold_time
                )
            )
        )

        inactive_sessions = result.scalars().all()

        for session in inactive_sessions:
            session.is_active = False
            session.ended_at = datetime.now()

        return len(inactive_sessions)

    async def get_session_stats(self, user_id: str = None) -> dict:
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
                    Session.is_active == True,
                    Session.user_id == user_id if user_id else True,
                )
            )
        )

        # SSH sessions
        ssh_sessions = await self.session.execute(
            select(func.count(Session.id)).where(
                and_(
                    Session.ssh_host.is_not(None),
                    Session.user_id == user_id if user_id else True,
                )
            )
        )

        # Device types breakdown
        device_breakdown = await self.session.execute(
            select(Session.device_type, func.count(Session.id))
            .where(Session.user_id == user_id if user_id else True)
            .group_by(Session.device_type)
        )

        return {
            "total_sessions": total_sessions.scalar(),
            "active_sessions": active_sessions.scalar(),
            "ssh_sessions": ssh_sessions.scalar(),
            "device_breakdown": dict(device_breakdown.fetchall()),
        }

    async def get_user_device_sessions(
        self, user_id: str, device_type: str = None
    ) -> dict:
        """Get user sessions grouped by device."""
        query = select(Session).where(Session.user_id == user_id)

        if device_type:
            query = query.where(Session.device_type == device_type)

        result = await self.session.execute(query.order_by(desc(Session.created_at)))
        sessions = result.scalars().all()

        # Group by device_id
        devices = {}
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

    async def cleanup_old_sessions(
        self, days_old: int = 90, keep_active: bool = True
    ) -> int:
        """Delete old sessions to save space."""
        cutoff_date = datetime.now() - timedelta(days=days_old)

        conditions = [Session.created_at < cutoff_date]

        if keep_active:
            conditions.append(Session.is_active == False)

        result = await self.session.execute(select(Session).where(and_(*conditions)))

        old_sessions = result.scalars().all()

        for session in old_sessions:
            await self.session.delete(session)

        return len(old_sessions)
