"""
Command repository for DevPocket API.
"""

from typing import Optional, List, Any, Dict, Union
from datetime import datetime, timedelta
from uuid import UUID as PyUUID
from sqlalchemy import select, and_, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
        status_filter: Optional[str] = None,
    ) -> List[Command]:
        """Get commands for a specific session."""
        query = select(Command).where(Command.session_id == session_id)

        if status_filter:
            query = query.where(Command.status == status_filter)

        query = query.order_by(desc(Command.created_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_user_command_history(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 100,
        search_term: Optional[str] = None,
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
        return list(result.scalars().all())

    async def get_commands_by_status(
        self,
        status: str,
        user_id: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
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
        return list(result.scalars().all())

    async def get_running_commands(
        self, user_id: Optional[str] = None, session_id: Optional[str] = None
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
        return list(result.scalars().all())

    async def create_command(
        self, session_id: str, command: str, **kwargs: Any
    ) -> Command:
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
        output: Optional[str] = None,
        error_output: Optional[str] = None,
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
        criteria: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None,
        executed_after: Optional[datetime] = None,
        executed_before: Optional[datetime] = None,
        min_duration_ms: Optional[int] = None,
        max_duration_ms: Optional[int] = None,
        has_output: Optional[bool] = None,
        has_error: Optional[bool] = None,
        output_contains: Optional[str] = None,
        working_directory: Optional[str] = None,
        include_dangerous: bool = True,
        only_dangerous: bool = False,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        offset: int = 0,
        limit: int = 100,
    ) -> List[Command]:
        """Search commands with comprehensive criteria."""
        from app.models.session import Session

        cmd_query = select(Command)
        needs_session_join = False

        # Apply basic criteria
        if criteria:
            for key, value in criteria.items():
                if key == "user_id":
                    needs_session_join = True
                elif hasattr(Command, key):
                    cmd_query = cmd_query.where(getattr(Command, key) == value)

        # Join with session if needed
        if needs_session_join:
            cmd_query = cmd_query.join(Session, Command.session_id == Session.id)
            if criteria and "user_id" in criteria:
                cmd_query = cmd_query.where(Session.user_id == criteria["user_id"])

        # Apply search query
        if query:
            cmd_query = cmd_query.where(Command.command.ilike(f"%{query}%"))

        # Apply date filters
        if executed_after:
            cmd_query = cmd_query.where(Command.executed_at >= executed_after)
        if executed_before:
            cmd_query = cmd_query.where(Command.executed_at <= executed_before)

        # Apply duration filters
        if min_duration_ms:
            cmd_query = cmd_query.where(
                Command.execution_time >= min_duration_ms / 1000
            )
        if max_duration_ms:
            cmd_query = cmd_query.where(
                Command.execution_time <= max_duration_ms / 1000
            )

        # Apply output filters
        if has_output is not None:
            if has_output:
                cmd_query = cmd_query.where(Command.output.isnot(None))
            else:
                cmd_query = cmd_query.where(Command.output.is_(None))

        if has_error is not None:
            if has_error:
                cmd_query = cmd_query.where(Command.exit_code != 0)
            else:
                cmd_query = cmd_query.where(Command.exit_code == 0)

        if output_contains:
            cmd_query = cmd_query.where(
                or_(
                    Command.output.ilike(f"%{output_contains}%"),
                    Command.error_output.ilike(f"%{output_contains}%"),
                )
            )

        if working_directory:
            cmd_query = cmd_query.where(Command.working_directory == working_directory)

        # Apply dangerous command filters
        if only_dangerous:
            cmd_query = cmd_query.where(Command.is_dangerous == True)
        elif not include_dangerous:
            cmd_query = cmd_query.where(Command.is_dangerous == False)

        # Apply sorting
        if sort_order.lower() == "desc":
            cmd_query = cmd_query.order_by(desc(getattr(Command, sort_by)))
        else:
            cmd_query = cmd_query.order_by(getattr(Command, sort_by))

        cmd_query = cmd_query.offset(offset).limit(limit)

        result = await self.session.execute(cmd_query)
        return list(result.scalars().all())

    async def get_user_commands_with_session(
        self,
        user_id: Union[str, PyUUID],
        offset: int = 0,
        limit: int = 100,
        include_session_info: bool = True,
    ) -> List[Command]:
        """Get user commands with session information."""
        from app.models.session import Session

        query = (
            select(Command)
            .join(Session, Command.session_id == Session.id)
            .where(Session.user_id == user_id)
        )

        if include_session_info:
            query = query.options(selectinload(Command.session))

        query = query.order_by(desc(Command.created_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_user_commands(self, user_id: Union[str, PyUUID]) -> int:
        """Count total commands for a user."""
        from app.models.session import Session

        query = (
            select(func.count(Command.id))
            .join(Session, Command.session_id == Session.id)
            .where(Session.user_id == user_id)
        )

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def count_commands_with_criteria(self, criteria: Dict[str, Any]) -> int:
        """Count commands matching criteria."""
        from app.models.session import Session

        query = select(func.count(Command.id))

        # Join with session if needed for user filtering
        needs_session_join = "user_id" in criteria
        if needs_session_join:
            query = query.join(Session, Command.session_id == Session.id)

        # Apply criteria filters
        for key, value in criteria.items():
            if key == "user_id" and needs_session_join:
                query = query.where(Session.user_id == value)
            elif hasattr(Command, key):
                query = query.where(getattr(Command, key) == value)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_user_commands(
        self,
        user_id: Union[str, PyUUID],
        offset: int = 0,
        limit: int = 100,
    ) -> List[Command]:
        """Get all commands for a user."""
        from app.models.session import Session

        query = (
            select(Command)
            .join(Session, Command.session_id == Session.id)
            .where(Session.user_id == user_id)
            .order_by(desc(Command.created_at))
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_session_command_stats(
        self, user_id: Union[str, PyUUID]
    ) -> List[Dict[str, Any]]:
        """Get command statistics by session."""
        from app.models.session import Session

        query = (
            select(
                Session.id,
                Session.session_name,
                func.count(Command.id).label("command_count"),
                func.avg(Command.execution_time).label("avg_duration"),
            )
            .join(Command, Session.id == Command.session_id)
            .where(Session.user_id == user_id)
            .group_by(Session.id, Session.session_name)
        )

        result = await self.session.execute(query)
        return [
            {
                "session_id": row.id,
                "session_name": row.session_name,
                "command_count": row.command_count,
                "avg_duration": row.avg_duration,
            }
            for row in result
        ]

    async def get_user_commands_since(
        self,
        user_id: Union[str, PyUUID],
        since: datetime,
        limit: int = 100,
    ) -> List[Command]:
        """Get user commands since a specific date."""
        from app.models.session import Session

        query = (
            select(Command)
            .join(Session, Command.session_id == Session.id)
            .where(and_(Session.user_id == user_id, Command.created_at >= since))
            .order_by(desc(Command.created_at))
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_user_recent_commands(
        self,
        user_id: Union[str, PyUUID],
        limit: int = 10,
    ) -> List[Command]:
        """Get recent commands for a user."""
        return await self.get_user_commands_since(
            user_id, datetime.now() - timedelta(days=7), limit
        )

    async def get_commands_by_type(
        self,
        command_type: str,
        user_id: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
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
        return list(result.scalars().all())

    async def get_ai_suggested_commands(
        self, user_id: Optional[str] = None, offset: int = 0, limit: int = 100
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
        return list(result.scalars().all())

    async def get_failed_commands(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
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
        return list(result.scalars().all())

    async def get_command_stats(self, user_id: Optional[str] = None) -> dict:
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
            "status_breakdown": {row[0]: row[1] for row in status_stats.fetchall()},
            "type_breakdown": {row[0]: row[1] for row in type_stats.fetchall()},
            "ai_suggested_count": ai_commands.scalar(),
            "average_execution_time": float(avg_execution_time.scalar() or 0),
        }

    async def get_top_commands(
        self, user_id: Optional[str] = None, limit: int = 10
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

        old_commands = list(result.scalars().all())

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
            .where(
                and_(
                    Session.user_id == user_id,
                    Command.created_at >= since_time,
                )
            )
            .order_by(desc(Command.created_at))
            .limit(limit)
        )

        return list(result.scalars().all())
