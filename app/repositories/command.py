"""
Command repository for DevPocket API.
"""

from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func, desc, asc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.command import Command
from .base import BaseRepository


class CommandRepository(BaseRepository[Command]):
    """Repository for Command model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Command, session)

    async def get_session_commands(
        self,
        session_id: str,
        offset: int = 0,
        limit: int = 100,
        status_filter: str = None,
    ) -> List[Command]:
        """Get commands for a specific session."""
        query = select(Command).where(Command.session_id == session_id)

        if status_filter:
            query = query.where(Command.status == status_filter)

        query = query.order_by(desc(Command.created_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_user_command_history(
        self, user_id: str, offset: int = 0, limit: int = 100, search_term: str = None
    ) -> List[Command]:
        """Get command history for a user across all sessions."""
        # This requires a join with Session table
        from app.models.session import Session

        query = (
            select(Command)
            .join(Session, Command.session_id == Session.id)
            .where(Session.user_id == user_id)
        )

        if search_term:
            query = query.where(Command.command.ilike(f"%{search_term}%"))

        query = query.order_by(desc(Command.created_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_commands_by_status(
        self, status: str, user_id: str = None, offset: int = 0, limit: int = 100
    ) -> List[Command]:
        """Get commands by status."""
        query = select(Command).where(Command.status == status)

        if user_id:
            from app.models.session import Session

            query = query.join(Session, Command.session_id == Session.id).where(
                Session.user_id == user_id
            )

        query = query.order_by(desc(Command.created_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_running_commands(
        self, user_id: str = None, session_id: str = None
    ) -> List[Command]:
        """Get currently running commands."""
        query = select(Command).where(Command.status == "running")

        if session_id:
            query = query.where(Command.session_id == session_id)
        elif user_id:
            from app.models.session import Session

            query = query.join(Session, Command.session_id == Session.id).where(
                Session.user_id == user_id
            )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def create_command(self, session_id: str, command: str, **kwargs) -> Command:
        """Create a new command."""
        cmd = Command(session_id=session_id, command=command, **kwargs)

        # Classify the command and check for sensitive content
        cmd.command_type = cmd.classify_command()
        cmd.is_sensitive = cmd.check_sensitive_content()

        self.session.add(cmd)
        await self.session.flush()
        await self.session.refresh(cmd)

        return cmd

    async def start_command_execution(self, command_id: str) -> Optional[Command]:
        """Mark command as started."""
        command = await self.get_by_id(command_id)
        if command:
            command.start_execution()
            await self.session.flush()
            await self.session.refresh(command)
        return command

    async def complete_command_execution(
        self,
        command_id: str,
        exit_code: int,
        output: str = None,
        error_output: str = None,
    ) -> Optional[Command]:
        """Complete command execution with results."""
        command = await self.get_by_id(command_id)
        if command:
            command.complete_execution(exit_code, output, error_output)
            await self.session.flush()
            await self.session.refresh(command)
        return command

    async def cancel_command(self, command_id: str) -> Optional[Command]:
        """Cancel a command."""
        command = await self.get_by_id(command_id)
        if command:
            command.cancel_execution()
            await self.session.flush()
            await self.session.refresh(command)
        return command

    async def timeout_command(self, command_id: str) -> Optional[Command]:
        """Mark command as timed out."""
        command = await self.get_by_id(command_id)
        if command:
            command.timeout_execution()
            await self.session.flush()
            await self.session.refresh(command)
        return command

    async def search_commands(
        self,
        search_term: str,
        user_id: str = None,
        session_id: str = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Command]:
        """Search commands by command text."""
        query = select(Command).where(Command.command.ilike(f"%{search_term}%"))

        if session_id:
            query = query.where(Command.session_id == session_id)
        elif user_id:
            from app.models.session import Session

            query = query.join(Session, Command.session_id == Session.id).where(
                Session.user_id == user_id
            )

        query = query.order_by(desc(Command.created_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_commands_by_type(
        self, command_type: str, user_id: str = None, offset: int = 0, limit: int = 100
    ) -> List[Command]:
        """Get commands by type."""
        query = select(Command).where(Command.command_type == command_type)

        if user_id:
            from app.models.session import Session

            query = query.join(Session, Command.session_id == Session.id).where(
                Session.user_id == user_id
            )

        query = query.order_by(desc(Command.created_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_ai_suggested_commands(
        self, user_id: str = None, offset: int = 0, limit: int = 100
    ) -> List[Command]:
        """Get commands that were AI-suggested."""
        query = select(Command).where(Command.was_ai_suggested == True)

        if user_id:
            from app.models.session import Session

            query = query.join(Session, Command.session_id == Session.id).where(
                Session.user_id == user_id
            )

        query = query.order_by(desc(Command.created_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_failed_commands(
        self,
        user_id: str = None,
        session_id: str = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Command]:
        """Get commands that failed (non-zero exit code or error status)."""
        query = select(Command).where(
            or_(Command.exit_code != 0, Command.status == "error")
        )

        if session_id:
            query = query.where(Command.session_id == session_id)
        elif user_id:
            from app.models.session import Session

            query = query.join(Session, Command.session_id == Session.id).where(
                Session.user_id == user_id
            )

        query = query.order_by(desc(Command.created_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_command_stats(self, user_id: str = None) -> dict:
        """Get command execution statistics."""
        from app.models.session import Session

        base_query = select(Command)

        if user_id:
            base_query = base_query.join(
                Session, Command.session_id == Session.id
            ).where(Session.user_id == user_id)

        # Total commands
        total_commands = await self.session.execute(
            select(func.count(Command.id)).select_from(base_query.subquery())
        )

        # Commands by status
        status_stats = await self.session.execute(
            select(Command.status, func.count(Command.id))
            .select_from(base_query.subquery())
            .group_by(Command.status)
        )

        # Commands by type
        type_stats = await self.session.execute(
            select(Command.command_type, func.count(Command.id))
            .select_from(base_query.subquery())
            .group_by(Command.command_type)
        )

        # AI suggested commands
        ai_commands = await self.session.execute(
            select(func.count(Command.id))
            .select_from(base_query.subquery())
            .where(Command.was_ai_suggested == True)
        )

        # Average execution time
        avg_execution_time = await self.session.execute(
            select(func.avg(Command.execution_time))
            .select_from(base_query.subquery())
            .where(Command.execution_time.is_not(None))
        )

        return {
            "total_commands": total_commands.scalar(),
            "status_breakdown": dict(status_stats.fetchall()),
            "type_breakdown": dict(type_stats.fetchall()),
            "ai_suggested_count": ai_commands.scalar(),
            "average_execution_time": float(avg_execution_time.scalar() or 0),
        }

    async def get_top_commands(
        self, user_id: str = None, limit: int = 10
    ) -> List[dict]:
        """Get most frequently used commands."""
        from app.models.session import Session

        query = select(
            Command.command, func.count(Command.id).label("usage_count")
        ).group_by(Command.command)

        if user_id:
            query = query.join(Session, Command.session_id == Session.id).where(
                Session.user_id == user_id
            )

        query = query.order_by(desc("usage_count")).limit(limit)

        result = await self.session.execute(query)

        return [{"command": row[0], "usage_count": row[1]} for row in result.fetchall()]

    async def cleanup_old_commands(
        self, days_old: int = 90, keep_successful: bool = True
    ) -> int:
        """Delete old commands to save space."""
        cutoff_date = datetime.now() - timedelta(days=days_old)

        conditions = [Command.created_at < cutoff_date]

        if keep_successful:
            conditions.extend([Command.status != "success", Command.exit_code != 0])

        result = await self.session.execute(select(Command).where(and_(*conditions)))

        old_commands = result.scalars().all()

        for command in old_commands:
            await self.session.delete(command)

        return len(old_commands)

    async def get_recent_commands(
        self, user_id: str, hours: int = 24, limit: int = 50
    ) -> List[Command]:
        """Get recent commands for a user."""
        from app.models.session import Session

        since_time = datetime.now() - timedelta(hours=hours)

        result = await self.session.execute(
            select(Command)
            .join(Session, Command.session_id == Session.id)
            .where(and_(Session.user_id == user_id, Command.created_at >= since_time))
            .order_by(desc(Command.created_at))
            .limit(limit)
        )

        return result.scalars().all()
