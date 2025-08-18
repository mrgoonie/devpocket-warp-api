"""
Terminal session service layer for DevPocket API.

Contains business logic for terminal session management, lifecycle operations,
and session monitoring.
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.session import Session
from app.models.user import User
from app.repositories.session import SessionRepository
from app.repositories.ssh_profile import SSHProfileRepository

from .schemas import (
    SessionCommand,
    SessionCommandResponse,
    SessionCreate,
    SessionHealthCheck,
    SessionHistoryEntry,
    SessionHistoryResponse,
    SessionResponse,
    SessionSearchRequest,
    SessionStats,
    SessionStatus,
    SessionUpdate,
)


class SessionService:
    """Service class for terminal session management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.session_repo = SessionRepository(session)
        self.ssh_profile_repo = SSHProfileRepository(session)
        self._active_sessions: dict[str, dict[str, Any]] = {}
        self._background_tasks: set = set()

    async def create_session(
        self, user: User, session_data: SessionCreate
    ) -> SessionResponse:
        """Create a new terminal session."""
        try:
            # Validate SSH profile if provided
            ssh_profile = None
            if session_data.ssh_profile_id:
                ssh_profile = await self.ssh_profile_repo.get_by_id(
                    session_data.ssh_profile_id
                )
                if not ssh_profile or ssh_profile.user_id != user.id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="SSH profile not found",
                    )

            # Check if session name already exists for user
            existing_session = await self.session_repo.get_user_session_by_name(
                user.id, session_data.name
            )
            if existing_session and existing_session.status in [
                "active",
                "connecting",
            ]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Active session with name '{session_data.name}' already exists",
                )

            # Prepare connection info
            connection_info = {}
            if ssh_profile:
                connection_info = {
                    "host": ssh_profile.host,
                    "port": ssh_profile.port,
                    "username": ssh_profile.username,
                    "profile_name": ssh_profile.name,
                }

            if session_data.connection_params:
                connection_info.update(session_data.connection_params)

            # Create the session - only include fields that exist in the Session model
            session_obj = Session(
                id=str(uuid.uuid4()),
                user_id=user.id,
                device_id="test_device",  # Required field  
                device_type="web",  # Required field
                device_name=None,
                session_name=session_data.name,  # Use session_name not name
                session_type=session_data.session_type.value,
                # Note: Session model doesn't have these fields:
                # description, ssh_profile_id, status, mode, working_directory,
                # idle_timeout, max_duration, enable_logging, enable_recording,
                # auto_reconnect, connection_info
                terminal_cols=(
                    session_data.terminal_size.get("cols", 80)
                    if session_data.terminal_size
                    else 80
                ),
                terminal_rows=(
                    session_data.terminal_size.get("rows", 24)
                    if session_data.terminal_size
                    else 24
                ),
                environment=str(session_data.environment or "{}"),  # Convert dict to string
                is_active=True,
            )

            created_session = await self.session_repo.create(session_obj)
            
            # Set status using the property setter
            created_session.status = "pending"  # This will update is_active appropriately
            
            await self.session.commit()

            # Initialize session in memory
            await self._initialize_session(created_session)

            logger.info(
                f"Terminal session created: {created_session.name} by user {user.username}"
            )
            
            # Convert to dict and handle problematic fields manually
            session_dict = {
                "id": str(created_session.id),
                "user_id": str(created_session.user_id),
                "name": created_session.name or created_session.session_name,
                "session_type": created_session.session_type,
                "description": session_data.description,
                "status": created_session.status,
                "ssh_profile_id": str(session_data.ssh_profile_id) if session_data.ssh_profile_id else None,
                "connection_info": connection_info,
                "start_time": getattr(created_session, "start_time", None),
                "end_time": getattr(created_session, "end_time", None),
                "last_activity": getattr(created_session, "last_activity", None),
                "duration_seconds": getattr(created_session, "duration_seconds", None),
                "command_count": 0,  # Default to 0 for new session
                "error_message": getattr(created_session, "error_message", None),
                "exit_code": None,
                "pid": None,
                "created_at": created_session.created_at,
                "updated_at": created_session.updated_at,
                "is_active": created_session.is_active,
                "mode": session_data.mode.value,
                "terminal_size": session_data.terminal_size or {"cols": 80, "rows": 24},
                "environment": session_data.environment or {},
                "working_directory": session_data.working_directory,
                "idle_timeout": session_data.idle_timeout,
                "max_duration": session_data.max_duration,
                "enable_logging": session_data.enable_logging,
                "enable_recording": session_data.enable_recording,
                "auto_reconnect": session_data.auto_reconnect,
            }
            
            return SessionResponse(**session_dict)

        except HTTPException:
            raise
        except IntegrityError as e:
            await self.session.rollback()
            logger.warning(f"Integrity error creating session: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session with this name already exists",
            ) from e
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create terminal session",
            ) from e

    async def get_user_sessions(
        self,
        user: User,
        active_only: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[SessionResponse], int]:
        """Get terminal sessions for a user with pagination."""
        try:
            sessions = await self.session_repo.get_user_sessions(
                user.id, active_only=active_only, offset=offset, limit=limit
            )

            # Get total count
            total = await self.session_repo.count_user_sessions(user.id)

            # Update session status from memory
            session_responses = []
            for session_obj in sessions:
                # Update with real-time status if available
                if str(session_obj.id) in self._active_sessions:
                    memory_session = self._active_sessions[str(session_obj.id)]
                    session_obj.status = memory_session.get(
                        "status", session_obj.status
                    )
                    session_obj.last_activity = memory_session.get(
                        "last_activity", session_obj.last_activity
                    )

                # Convert to dict and handle problematic fields manually
                session_dict = {
                    "id": str(session_obj.id),
                    "user_id": str(session_obj.user_id),
                    "name": session_obj.name or session_obj.session_name,
                    "session_type": session_obj.session_type,
                    "description": getattr(session_obj, "description", None),
                    "status": session_obj.status,
                    "ssh_profile_id": str(getattr(session_obj, "ssh_profile_id", None)) if getattr(session_obj, "ssh_profile_id", None) else None,
                    "connection_info": getattr(session_obj, "connection_info", None),
                    "start_time": getattr(session_obj, "start_time", None),
                    "end_time": getattr(session_obj, "end_time", None),
                    "last_activity": getattr(session_obj, "last_activity", None),
                    "duration_seconds": getattr(session_obj, "duration_seconds", None),
                    "command_count": 0,  # Default to 0 to avoid async issues
                    "error_message": getattr(session_obj, "error_message", None),
                    "exit_code": getattr(session_obj, "exit_code", None),
                    "pid": getattr(session_obj, "pid", None),
                    "created_at": session_obj.created_at,
                    "updated_at": session_obj.updated_at,
                    "is_active": session_obj.is_active,
                    "mode": getattr(session_obj, "mode", "interactive"),
                    "terminal_size": {"cols": getattr(session_obj, "terminal_cols", 80), "rows": getattr(session_obj, "terminal_rows", 24)},
                    "environment": getattr(session_obj, "environment", {}),
                    "working_directory": getattr(session_obj, "working_directory", None),
                    # Set default values for nullable fields instead of None
                    "idle_timeout": getattr(session_obj, "idle_timeout", 1800),  
                    "max_duration": getattr(session_obj, "max_duration", 14400),  
                    "enable_logging": getattr(session_obj, "enable_logging", True),  
                    "enable_recording": getattr(session_obj, "enable_recording", False),  
                    "auto_reconnect": getattr(session_obj, "auto_reconnect", True),  
                }

                session_responses.append(SessionResponse(**session_dict))

            return session_responses, total

        except Exception as e:
            logger.error(f"Error fetching user sessions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch terminal sessions",
            ) from e

    async def get_session(self, user: User, session_id: str) -> SessionResponse:
        """Get a specific terminal session."""
        session_obj = await self.session_repo.get_by_id(session_id)

        if not session_obj or session_obj.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Terminal session not found",
            )

        # Update with real-time status if available
        if session_id in self._active_sessions:
            memory_session = self._active_sessions[session_id]
            session_obj.status = memory_session.get("status", session_obj.status)
            session_obj.last_activity = memory_session.get(
                "last_activity", session_obj.last_activity
            )
            # command_count is computed from the commands relationship

        # Convert to dict and handle problematic fields manually 
        session_dict = {
            "id": str(session_obj.id),
            "user_id": str(session_obj.user_id),
            "name": session_obj.name or session_obj.session_name,
            "session_type": session_obj.session_type,
            "description": getattr(session_obj, "description", None),
            "status": session_obj.status,
            "ssh_profile_id": None,  # Session model doesn't have this field
            "connection_info": None,  # Session model doesn't have this field
            "start_time": getattr(session_obj, "start_time", None),
            "end_time": getattr(session_obj, "end_time", None),
            "last_activity": getattr(session_obj, "last_activity", None),
            "duration_seconds": getattr(session_obj, "duration_seconds", None),
            "command_count": 0,  # Default to 0 to avoid async issues
            "error_message": getattr(session_obj, "error_message", None),
            "exit_code": None,  # Session model doesn't have this field
            "pid": None,  # Session model doesn't have this field
            "created_at": session_obj.created_at,
            "updated_at": session_obj.updated_at,
            "is_active": session_obj.is_active,
            "mode": "interactive",  # Session model doesn't have this field, default value
            "terminal_size": {"cols": getattr(session_obj, "terminal_cols", 80), "rows": getattr(session_obj, "terminal_rows", 24)},
            "environment": getattr(session_obj, "environment", {}),
            "working_directory": None,  # Session model doesn't have this field
            # Set default values for nullable fields instead of None
            "idle_timeout": 1800,  # Default value
            "max_duration": 14400,  # Default value
            "enable_logging": True,  # Default value
            "enable_recording": False,  # Default value
            "auto_reconnect": True,  # Default value
        }
        
        return SessionResponse(**session_dict)

    async def update_session(
        self, user: User, session_id: str, update_data: SessionUpdate
    ) -> SessionResponse:
        """Update terminal session configuration."""
        try:
            session_obj = await self.session_repo.get_by_id(session_id)

            if not session_obj or session_obj.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Terminal session not found",
                )

            # Update session configuration
            update_dict = update_data.model_dump(exclude_unset=True)

            # Handle terminal size update
            if "terminal_size" in update_dict:
                terminal_size = update_dict.pop("terminal_size")
                if terminal_size:
                    update_dict["terminal_cols"] = terminal_size.get(
                        "cols", session_obj.terminal_cols
                    )
                    update_dict["terminal_rows"] = terminal_size.get(
                        "rows", session_obj.terminal_rows
                    )

            # Apply updates
            for field, value in update_dict.items():
                setattr(session_obj, field, value)

            session_obj.updated_at = datetime.now(UTC)
            updated_session = await self.session_repo.update(session_obj)
            await self.session.commit()

            if updated_session is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update session",
                )

            # Update active session in memory if it exists
            if str(session_id) in self._active_sessions:
                self._active_sessions[str(session_id)].update(
                    {
                        "terminal_cols": updated_session.terminal_cols,
                        "terminal_rows": updated_session.terminal_rows,
                        "environment": updated_session.environment,
                        "updated_at": updated_session.updated_at,
                    }
                )

            logger.info(
                f"Terminal session updated: {session_obj.name} by user {user.username}"
            )
            
            # Convert to dict and handle problematic fields manually
            session_dict = {
                "id": str(updated_session.id),
                "user_id": str(updated_session.user_id),
                "name": updated_session.name or updated_session.session_name,
                "session_type": updated_session.session_type,
                "description": getattr(updated_session, "description", None),
                "status": updated_session.status,
                "ssh_profile_id": None,  # Session model doesn't have this field
                "connection_info": None,  # Session model doesn't have this field
                "start_time": getattr(updated_session, "start_time", None),
                "end_time": getattr(updated_session, "end_time", None),
                "last_activity": getattr(updated_session, "last_activity", None),
                "duration_seconds": getattr(updated_session, "duration_seconds", None),
                "command_count": 0,  # Default to 0 to avoid async issues
                "error_message": getattr(updated_session, "error_message", None),
                "exit_code": None,  # Session model doesn't have this field
                "pid": None,  # Session model doesn't have this field
                "created_at": updated_session.created_at,
                "updated_at": updated_session.updated_at,
                "is_active": updated_session.is_active,
                "mode": "interactive",  # Default value
                "terminal_size": {"cols": getattr(updated_session, "terminal_cols", 80), "rows": getattr(updated_session, "terminal_rows", 24)},
                "environment": getattr(updated_session, "environment", {}),
                "working_directory": None,  # Session model doesn't have this field
                # Use update_data values or defaults
                "idle_timeout": getattr(update_data, "idle_timeout", None) or 1800,
                "max_duration": getattr(update_data, "max_duration", None) or 14400,
                "enable_logging": getattr(update_data, "enable_logging", None) if getattr(update_data, "enable_logging", None) is not None else True,
                "enable_recording": getattr(update_data, "enable_recording", None) if getattr(update_data, "enable_recording", None) is not None else False,
                "auto_reconnect": getattr(update_data, "auto_reconnect", None) if getattr(update_data, "auto_reconnect", None) is not None else True,
            }
            
            return SessionResponse(**session_dict)

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update terminal session",
            ) from e

    async def terminate_session(
        self, user: User, session_id: str, force: bool = False
    ) -> bool:
        """Terminate a terminal session."""
        try:
            session_obj = await self.session_repo.get_by_id(session_id)

            if not session_obj or session_obj.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Terminal session not found",
                )

            # Check if session can be terminated
            if session_obj.status in ["terminated", "failed"] and not force:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Session is already terminated",
                )

            # Terminate the session
            await self._terminate_session_process(session_id)

            # Update database
            session_obj.status = "terminated"
            session_obj.end_time = datetime.now(UTC)
            session_obj.is_active = False

            if session_obj.start_time:
                duration = session_obj.end_time - session_obj.start_time
                session_obj.duration_seconds = int(duration.total_seconds())

            await self.session_repo.update(session_obj)
            await self.session.commit()

            logger.info(
                f"Terminal session terminated: {session_obj.name} by user {user.username}"
            )
            return True

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error terminating session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to terminate terminal session",
            ) from e

    async def delete_session(self, user: User, session_id: str) -> bool:
        """Delete a terminal session."""
        try:
            session_obj = await self.session_repo.get_by_id(session_id)

            if not session_obj or session_obj.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Terminal session not found",
                )

            # Terminate session if still active
            if session_obj.status in ["active", "connecting"]:
                await self._terminate_session_process(session_id)

            # Clean up session data
            await self._cleanup_session_data(session_id)

            # Delete from database
            await self.session_repo.delete(session_id)
            await self.session.commit()

            logger.info(
                f"Terminal session deleted: {session_obj.name} by user {user.username}"
            )
            return True

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete terminal session",
            ) from e

    async def execute_command(
        self, user: User, session_id: str, command: SessionCommand
    ) -> SessionCommandResponse:
        """Execute command in terminal session."""
        try:
            session_obj = await self.session_repo.get_by_id(session_id)

            if not session_obj or session_obj.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Terminal session not found",
                )

            if session_obj.status != "active":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Session is not active",
                )

            # Execute command
            command_result = await self._execute_session_command(session_id, command)

            # Update session statistics
            await self._update_session_activity(session_id)

            return command_result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error executing command in session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to execute command",
            ) from e

    async def get_session_history(
        self, user: User, session_id: str, limit: int = 100, offset: int = 0
    ) -> SessionHistoryResponse:
        """Get session command history."""
        try:
            session_obj = await self.session_repo.get_by_id(session_id)

            if not session_obj or session_obj.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Terminal session not found",
                )

            # Get history from database (commands)
            commands = await self.session_repo.get_session_commands(
                session_id, limit=limit, offset=offset
            )

            # Convert to history entries
            entries = [
                SessionHistoryEntry(
                    id=cmd.id,
                    timestamp=cmd.executed_at,
                    entry_type="command",
                    content=cmd.command,
                    metadata={
                        "exit_code": cmd.exit_code,
                        "duration_ms": cmd.duration_ms,
                        "working_directory": cmd.working_directory,
                    },
                )
                for cmd in commands
            ]

            total_entries = await self.session_repo.count_session_commands(session_id)

            return SessionHistoryResponse(
                session_id=session_id,
                entries=entries,
                total_entries=total_entries,
                start_time=session_obj.start_time,
                end_time=session_obj.end_time,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching session history: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch session history",
            ) from e

    async def search_sessions(
        self, user: User, search_request: SessionSearchRequest
    ) -> tuple[list[SessionResponse], int]:
        """Search terminal sessions with filters."""
        try:
            # Build search criteria
            criteria: dict[str, Any] = {"user_id": user.id}

            if search_request.session_type:
                criteria["session_type"] = search_request.session_type.value

            # Note: status is a computed property, we'll filter by is_active instead
            if search_request.status:
                if search_request.status.value == "active":
                    criteria["is_active"] = True
                elif search_request.status.value == "terminated":
                    criteria["is_active"] = False

            if search_request.ssh_profile_id:
                criteria["ssh_profile_id"] = search_request.ssh_profile_id

            sessions = await self.session_repo.search_sessions(
                criteria=criteria,
                search_term=search_request.search_term,
                created_after=search_request.created_after,
                created_before=search_request.created_before,
                sort_by=search_request.sort_by,
                sort_order=search_request.sort_order,
                offset=search_request.offset,
                limit=search_request.limit,
            )

            # Get total count
            total = await self.session_repo.count_sessions_with_criteria(criteria)

            session_responses = []
            for session_obj in sessions:
                # Convert to dict and handle problematic fields manually
                session_dict = {
                    "id": str(session_obj.id),
                    "user_id": str(session_obj.user_id),
                    "name": session_obj.name or session_obj.session_name,
                    "session_type": session_obj.session_type,
                    "description": getattr(session_obj, "description", None),
                    "status": session_obj.status,
                    "ssh_profile_id": None,  # Session model doesn't have this field
                    "connection_info": None,  # Session model doesn't have this field
                    "start_time": getattr(session_obj, "start_time", None),
                    "end_time": getattr(session_obj, "end_time", None),
                    "last_activity": getattr(session_obj, "last_activity", None),
                    "duration_seconds": getattr(session_obj, "duration_seconds", None),
                    "command_count": 0,  # Default to 0 to avoid async issues
                    "error_message": getattr(session_obj, "error_message", None),
                    "exit_code": None,  # Session model doesn't have this field
                    "pid": None,  # Session model doesn't have this field
                    "created_at": session_obj.created_at,
                    "updated_at": session_obj.updated_at,
                    "is_active": session_obj.is_active,
                    "mode": "interactive",  # Default value
                    "terminal_size": {"cols": getattr(session_obj, "terminal_cols", 80), "rows": getattr(session_obj, "terminal_rows", 24)},
                    "environment": getattr(session_obj, "environment", {}),
                    "working_directory": None,  # Session model doesn't have this field
                    # Set default values for nullable fields
                    "idle_timeout": 1800,  # Default value
                    "max_duration": 14400,  # Default value
                    "enable_logging": True,  # Default value
                    "enable_recording": False,  # Default value
                    "auto_reconnect": True,  # Default value
                }
                
                session_responses.append(SessionResponse(**session_dict))

            return session_responses, total

        except Exception as e:
            logger.error(f"Error searching sessions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to search terminal sessions",
            ) from e

    async def get_session_stats(self, user: User) -> SessionStats:
        """Get terminal session statistics for user."""
        try:
            # Get basic counts
            stats_data = await self.session_repo.get_user_session_stats(user.id)

            # Calculate additional metrics
            total_duration = sum(
                (s.duration_seconds or 0) for s in stats_data["sessions"]
            )
            total_commands = sum((s.command_count or 0) for s in stats_data["sessions"])

            avg_duration = (
                total_duration / len(stats_data["sessions"])
                if stats_data["sessions"]
                else 0
            ) / 60  # Convert to minutes

            avg_commands = (
                total_commands / len(stats_data["sessions"])
                if stats_data["sessions"]
                else 0
            )

            # Get sessions created today and this week
            today = datetime.now(UTC).date()
            week_ago = today - timedelta(days=7)

            sessions_today = len(
                [s for s in stats_data["sessions"] if s.created_at.date() == today]
            )

            sessions_this_week = len(
                [s for s in stats_data["sessions"] if s.created_at.date() >= week_ago]
            )

            return SessionStats(
                total_sessions=stats_data["total_sessions"],
                active_sessions=stats_data["active_sessions"],
                sessions_by_type=stats_data["by_type"],
                sessions_by_status=stats_data["by_status"],
                total_duration_hours=total_duration / 3600,
                average_session_duration_minutes=avg_duration,
                total_commands=total_commands,
                average_commands_per_session=avg_commands,
                sessions_today=sessions_today,
                sessions_this_week=sessions_this_week,
                most_used_profiles=stats_data["most_used_profiles"],
            )

        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get session statistics",
            ) from e

    async def check_session_health(
        self, user: User, session_id: str
    ) -> SessionHealthCheck:
        """Check session health and connectivity."""
        try:
            session_obj = await self.session_repo.get_by_id(session_id)

            if not session_obj or session_obj.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Terminal session not found",
                )

            # Check session health
            is_healthy = await self._check_session_health(session_id)

            uptime = 0
            if session_obj.start_time:
                uptime = int(
                    (datetime.now(UTC) - session_obj.start_time).total_seconds()
                )

            # Convert string status to SessionStatus enum
            try:
                status_enum = SessionStatus(session_obj.status)
            except ValueError:
                status_enum = SessionStatus.PENDING

            return SessionHealthCheck(
                session_id=session_id,
                is_healthy=is_healthy,
                status=status_enum,
                last_activity=session_obj.last_activity,
                uptime_seconds=uptime,
                connection_stable=session_obj.status == "active",
                response_time_ms=None,  # Would be set by actual health check
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking session health: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to check session health",
            ) from e

    # Private helper methods

    async def _initialize_session(self, session: Session) -> None:
        """Initialize session in memory."""
        self._active_sessions[str(session.id)] = {
            "status": "connecting",
            "created_at": session.created_at,
            "last_activity": datetime.now(UTC),
            "command_count": 0,
            "terminal_cols": session.terminal_cols,
            "terminal_rows": session.terminal_rows,
            "environment": session.environment,
        }

        # Start session initialization task
        task = asyncio.create_task(self._start_session_process(session))
        # Store task reference to prevent garbage collection
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _start_session_process(self, session: Session) -> None:
        """Start the actual terminal session process."""
        try:
            # Simulate session startup (in real implementation, this would
            # start SSH connection or local shell)
            await asyncio.sleep(1)  # Simulate connection time

            # Update session status
            session.status = "active"
            session.last_activity = datetime.now(UTC)

            await self.session_repo.update(session)
            await self.session.commit()

            # Update memory
            if str(session.id) in self._active_sessions:
                self._active_sessions[str(session.id)].update(
                    {
                        "status": "active",
                        "start_time": session.start_time,
                        "last_activity": session.last_activity,
                    }
                )

            logger.info(f"Session process started: {session.id}")

        except Exception as e:
            logger.error(f"Failed to start session process: {e}")
            # Update status to failed
            session.status = "failed"
            session.error_message = str(e)
            await self.session_repo.update(session)
            await self.session.commit()

    async def _terminate_session_process(self, session_id: str) -> None:
        """Terminate session process."""
        if session_id in self._active_sessions:
            # Clean up active session
            del self._active_sessions[session_id]

        # In real implementation, this would terminate the actual process
        logger.info(f"Session process terminated: {session_id}")

    async def _cleanup_session_data(self, session_id: str) -> None:
        """Clean up session-related data."""
        # Clean up any session files, logs, recordings, etc.
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]

        logger.info(f"Session data cleaned up: {session_id}")

    async def _execute_session_command(
        self, session_id: str, command: SessionCommand
    ) -> SessionCommandResponse:
        """Execute command in session."""
        # This is a simplified implementation
        # In production, this would interact with the actual terminal process

        command_id = str(uuid.uuid4())
        start_time = datetime.now(UTC)

        try:
            # Simulate command execution
            await asyncio.sleep(0.1)  # Simulate execution time

            # Mock successful execution
            stdout = f"Command '{command.command}' executed successfully"
            stderr = ""
            exit_code = 0

        except Exception as e:
            stdout = ""
            stderr = str(e)
            exit_code = 1

        end_time = datetime.now(UTC)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        return SessionCommandResponse(
            command_id=command_id,
            command=command.command,
            status="completed",
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            session_id=session_id,
            working_directory=command.working_directory or "/tmp",
        )

    async def _update_session_activity(self, session_id: str) -> None:
        """Update session activity timestamp."""
        if session_id in self._active_sessions:
            self._active_sessions[session_id]["last_activity"] = datetime.now(UTC)
            self._active_sessions[session_id]["command_count"] += 1

    async def _check_session_health(self, session_id: str) -> bool:
        """Check if session is healthy."""
        if session_id not in self._active_sessions:
            return False

        memory_session = self._active_sessions[session_id]

        # Check if session is recent enough
        last_activity = memory_session.get("last_activity")
        if last_activity:
            time_since_activity = datetime.now(UTC) - last_activity
            return bool(time_since_activity.total_seconds() < 3600)  # 1 hour threshold

        return memory_session.get("status") == "active"
