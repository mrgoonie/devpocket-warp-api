"""
Terminal Session Management API router for DevPocket.

Handles all terminal session endpoints including lifecycle management,
command execution, and session monitoring.
"""

from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.logging import logger
from app.db.database import get_db
from app.models.user import User
from .schemas import (
    # Session schemas
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    SessionListResponse,
    SessionSearchRequest,
    SessionStats,
    SessionHealthCheck,
    # Command schemas
    SessionCommand,
    SessionCommandResponse,
    # History schemas
    SessionHistoryResponse,
    # WebSocket schemas
    WSMessage,
    # Batch operations
    BatchSessionOperation,
    BatchSessionResponse,
    # Common schemas
    MessageResponse,
)
from .service import SessionService


# Create router instance
router = APIRouter(
    prefix="/api/sessions",
    tags=["Terminal Sessions"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Access forbidden"},
        404: {"description": "Resource not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)


# Session Lifecycle Endpoints


@router.post(
    "/",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Terminal Session",
    description="Create a new terminal session (SSH or local)",
)
async def create_session(
    session_data: SessionCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionResponse:
    """Create a new terminal session."""
    service = SessionService(db)
    return await service.create_session(current_user, session_data)


@router.get(
    "/",
    response_model=SessionListResponse,
    summary="List Terminal Sessions",
    description="Get user's terminal sessions with pagination",
)
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    active_only: bool = Query(default=False, description="Show only active sessions"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=50, ge=1, le=100, description="Pagination limit"),
) -> SessionListResponse:
    """Get user's terminal sessions with pagination."""
    service = SessionService(db)
    sessions, total = await service.get_user_sessions(
        current_user, active_only=active_only, offset=offset, limit=limit
    )

    return SessionListResponse(
        sessions=sessions, total=total, offset=offset, limit=limit
    )


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get Terminal Session",
    description="Get specific terminal session details and status",
)
async def get_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionResponse:
    """Get specific terminal session details and status."""
    service = SessionService(db)
    return await service.get_session(current_user, session_id)


@router.put(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Update Terminal Session",
    description="Update terminal session configuration",
)
async def update_session(
    session_id: str,
    update_data: SessionUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionResponse:
    """Update terminal session configuration."""
    service = SessionService(db)
    return await service.update_session(current_user, session_id, update_data)


@router.delete(
    "/{session_id}",
    response_model=MessageResponse,
    summary="Delete Terminal Session",
    description="Terminate and delete terminal session",
)
async def delete_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Terminate and delete terminal session."""
    service = SessionService(db)
    await service.delete_session(current_user, session_id)

    return MessageResponse(
        message="Terminal session deleted successfully", session_id=session_id
    )


@router.post(
    "/{session_id}/terminate",
    response_model=MessageResponse,
    summary="Terminate Terminal Session",
    description="Gracefully terminate terminal session",
)
async def terminate_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    force: bool = Query(default=False, description="Force termination"),
) -> MessageResponse:
    """Gracefully terminate terminal session."""
    service = SessionService(db)
    await service.terminate_session(current_user, session_id, force=force)

    return MessageResponse(
        message="Terminal session terminated successfully",
        session_id=session_id,
    )


# Session Operations Endpoints


@router.post(
    "/{session_id}/commands",
    response_model=SessionCommandResponse,
    summary="Execute Command",
    description="Execute command in terminal session (non-WebSocket fallback)",
)
async def execute_command(
    session_id: str,
    command: SessionCommand,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionCommandResponse:
    """Execute command in terminal session (non-WebSocket fallback)."""
    service = SessionService(db)
    return await service.execute_command(current_user, session_id, command)


@router.get(
    "/{session_id}/history",
    response_model=SessionHistoryResponse,
    summary="Get Session History",
    description="Get session command history and activity log",
)
async def get_session_history(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=1000, description="History entries limit"),
    offset: int = Query(default=0, ge=0, description="History offset"),
) -> SessionHistoryResponse:
    """Get session command history and activity log."""
    service = SessionService(db)
    return await service.get_session_history(
        current_user, session_id, limit=limit, offset=offset
    )


@router.get(
    "/{session_id}/health",
    response_model=SessionHealthCheck,
    summary="Check Session Health",
    description="Check session health and connectivity status",
)
async def check_session_health(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionHealthCheck:
    """Check session health and connectivity status."""
    service = SessionService(db)
    return await service.check_session_health(current_user, session_id)


# Search and Filter Endpoints


@router.post(
    "/search",
    response_model=SessionListResponse,
    summary="Search Terminal Sessions",
    description="Search terminal sessions with advanced filters",
)
async def search_sessions(
    search_request: SessionSearchRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionListResponse:
    """Search terminal sessions with advanced filters."""
    service = SessionService(db)
    sessions, total = await service.search_sessions(current_user, search_request)

    return SessionListResponse(
        sessions=sessions,
        total=total,
        offset=search_request.offset,
        limit=search_request.limit,
    )


@router.get(
    "/stats/overview",
    response_model=SessionStats,
    summary="Get Session Statistics",
    description="Get comprehensive terminal session usage statistics",
)
async def get_session_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionStats:
    """Get comprehensive terminal session usage statistics."""
    service = SessionService(db)
    return await service.get_session_stats(current_user)


# Batch Operations Endpoints


@router.post(
    "/batch",
    response_model=BatchSessionResponse,
    summary="Batch Session Operations",
    description="Perform batch operations on multiple sessions",
)
async def batch_session_operations(
    operation: BatchSessionOperation,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BatchSessionResponse:
    """Perform batch operations on multiple sessions."""
    service = SessionService(db)

    success_count = 0
    error_count = 0
    results = []

    for session_id in operation.session_ids:
        try:
            if operation.operation == "terminate":
                await service.terminate_session(
                    current_user, session_id, force=operation.force
                )
                results.append(
                    {
                        "session_id": session_id,
                        "status": "success",
                        "operation": "terminate",
                    }
                )
                success_count += 1

            elif operation.operation == "delete":
                await service.delete_session(current_user, session_id)
                results.append(
                    {
                        "session_id": session_id,
                        "status": "success",
                        "operation": "delete",
                    }
                )
                success_count += 1

            else:
                raise ValueError(f"Unsupported operation: {operation.operation}")

        except HTTPException as e:
            results.append(
                {
                    "session_id": session_id,
                    "status": "error",
                    "error": e.detail,
                    "operation": operation.operation,
                }
            )
            error_count += 1

        except Exception as e:
            results.append(
                {
                    "session_id": session_id,
                    "status": "error",
                    "error": str(e),
                    "operation": operation.operation,
                }
            )
            error_count += 1

    message = f"Batch {operation.operation} completed: {success_count} successful, {error_count} failed"

    return BatchSessionResponse(
        success_count=success_count,
        error_count=error_count,
        results=results,
        message=message,
    )


# Session Management Utilities


@router.get(
    "/active/count",
    response_model=dict,
    summary="Get Active Session Count",
    description="Get count of currently active sessions",
)
async def get_active_session_count(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get count of currently active sessions."""
    service = SessionService(db)
    sessions, total = await service.get_user_sessions(
        current_user, active_only=True, offset=0, limit=1000
    )

    # Count by type
    ssh_count = len([s for s in sessions if s.session_type == "ssh"])
    local_count = len([s for s in sessions if s.session_type == "local"])

    return {
        "total_active": total,
        "ssh_sessions": ssh_count,
        "local_sessions": local_count,
        "timestamp": logger.get_current_time(),
    }


@router.post(
    "/cleanup/inactive",
    response_model=dict,
    summary="Cleanup Inactive Sessions",
    description="Clean up inactive or stale sessions",
)
async def cleanup_inactive_sessions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    max_idle_hours: int = Query(
        default=24, ge=1, le=168, description="Max idle time in hours"
    ),
) -> dict:
    """Clean up inactive or stale sessions."""
    service = SessionService(db)

    # Get all user sessions
    all_sessions, _ = await service.get_user_sessions(
        current_user, active_only=False, offset=0, limit=1000
    )

    # Find stale sessions
    from datetime import timedelta

    cutoff_time = logger.get_current_time() - timedelta(hours=max_idle_hours)

    cleanup_count = 0
    errors = []

    for session in all_sessions:
        try:
            # Check if session is stale
            last_activity = session.last_activity or session.created_at
            if (
                session.status in ["active", "connecting"]
                and last_activity < cutoff_time
            ):
                await service.terminate_session(current_user, session.id, force=True)
                cleanup_count += 1

        except Exception as e:
            errors.append({"session_id": session.id, "error": str(e)})

    return {
        "cleaned_up": cleanup_count,
        "errors": len(errors),
        "error_details": errors if errors else None,
        "cutoff_time": cutoff_time.isoformat(),
        "message": f"Cleaned up {cleanup_count} inactive sessions",
    }


# Health and Monitoring Endpoints


@router.get(
    "/health",
    response_model=dict,
    summary="Session Service Health",
    description="Check session management service health",
)
async def session_service_health(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Check session management service health."""
    try:
        service = SessionService(db)

        # Test basic service functionality
        sessions, total = await service.get_user_sessions(
            current_user, active_only=False, offset=0, limit=1
        )

        # Get active session count
        active_sessions, active_total = await service.get_user_sessions(
            current_user, active_only=True, offset=0, limit=1000
        )

        return {
            "status": "healthy",
            "service": "session_management",
            "database": "connected",
            "total_sessions": total,
            "active_sessions": active_total,
            "memory_sessions": len(service._active_sessions),
            "timestamp": logger.get_current_time(),
        }

    except Exception as e:
        logger.error(f"Session service health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "session_management",
            "error": str(e),
            "timestamp": logger.get_current_time(),
        }


@router.get(
    "/metrics/summary",
    response_model=dict,
    summary="Session Metrics Summary",
    description="Get session usage metrics summary",
)
async def get_session_metrics(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get session usage metrics summary."""
    try:
        service = SessionService(db)
        stats = await service.get_session_stats(current_user)

        return {
            "summary": {
                "total_sessions": stats.total_sessions,
                "active_sessions": stats.active_sessions,
                "sessions_today": stats.sessions_today,
                "total_duration_hours": round(stats.total_duration_hours, 2),
                "total_commands": stats.total_commands,
            },
            "breakdown": {
                "by_type": stats.sessions_by_type,
                "by_status": stats.sessions_by_status,
            },
            "averages": {
                "session_duration_minutes": round(
                    stats.average_session_duration_minutes, 2
                ),
                "commands_per_session": round(stats.average_commands_per_session, 2),
            },
            "timestamp": logger.get_current_time(),
        }

    except Exception as e:
        logger.error(f"Failed to get session metrics: {e}")
        return {"error": str(e), "timestamp": logger.get_current_time()}
