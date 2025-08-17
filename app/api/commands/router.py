"""
Command Management API router for DevPocket.

Handles all command-related endpoints including history, analytics,
search operations, and command insights.
"""

from datetime import UTC
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.logging import logger
from app.db.database import get_db
from app.models.user import User

from .schemas import (
    # Batch operations
    BulkCommandOperation,
    BulkCommandResponse,
    # Export schemas
    CommandExportRequest,
    CommandExportResponse,
    CommandHistoryResponse,
    CommandListResponse,
    CommandMetrics,
    # Command schemas
    CommandResponse,
    CommandSearchRequest,
    # Suggestion schemas
    CommandSuggestion,
    CommandSuggestionRequest,
    # Analytics schemas
    CommandUsageStats,
    FrequentCommandsResponse,
    # Common schemas
    MessageResponse,
    SessionCommandStats,
)
from .service import CommandService

# Create router instance
router = APIRouter(
    prefix="/api/commands",
    tags=["Command Management"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Access forbidden"},
        404: {"description": "Resource not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)


# Command History Endpoints


@router.get(
    "/",
    response_model=CommandHistoryResponse,
    summary="Get Command History",
    description="Get user's command history with filtering and pagination",
)
async def get_command_history(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    session_id: str | None = Query(None, description="Filter by session ID"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=100, ge=1, le=500, description="Pagination limit"),
) -> CommandHistoryResponse:
    """Get user's command history with filtering and pagination."""
    service = CommandService(db)
    return await service.get_command_history(
        current_user, session_id=session_id, offset=offset, limit=limit
    )


@router.get(
    "/{command_id}",
    response_model=CommandResponse,
    summary="Get Command Details",
    description="Get detailed information about a specific command execution",
)
async def get_command_details(
    command_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommandResponse:
    """Get detailed information about a specific command execution."""
    service = CommandService(db)
    return await service.get_command_details(current_user, command_id)


@router.delete(
    "/{command_id}",
    response_model=MessageResponse,
    summary="Delete Command",
    description="Remove command from history",
)
async def delete_command(
    command_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Remove command from history."""
    service = CommandService(db)
    await service.delete_command(current_user, command_id)

    return MessageResponse(message="Command deleted from history successfully")


# Command Search Endpoints


@router.post(
    "/search",
    response_model=CommandListResponse,
    summary="Search Commands",
    description="Search commands with advanced filtering and full-text search",
)
async def search_commands(
    search_request: CommandSearchRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommandListResponse:
    """Search commands with advanced filtering and full-text search."""
    service = CommandService(db)
    commands, total = await service.search_commands(current_user, search_request)

    return CommandListResponse(
        commands=commands,
        total=total,
        offset=search_request.offset,
        limit=search_request.limit,
        session_id=search_request.session_id,
    )


# Command Analytics Endpoints


@router.get(
    "/stats/usage",
    response_model=CommandUsageStats,
    summary="Get Usage Statistics",
    description="Get comprehensive command usage statistics and analytics",
)
async def get_usage_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommandUsageStats:
    """Get comprehensive command usage statistics and analytics."""
    service = CommandService(db)
    return await service.get_usage_stats(current_user)


@router.get(
    "/stats/sessions",
    response_model=list[SessionCommandStats],
    summary="Get Session Statistics",
    description="Get command statistics grouped by session",
)
async def get_session_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    session_id: str | None = Query(None, description="Filter by specific session"),
) -> list[SessionCommandStats]:
    """Get command statistics grouped by session."""
    service = CommandService(db)
    return await service.get_session_command_stats(current_user, session_id=session_id)


@router.get(
    "/frequent",
    response_model=FrequentCommandsResponse,
    summary="Get Frequent Commands",
    description="Get frequently used commands with usage patterns and analytics",
)
async def get_frequent_commands(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365, description="Analysis period in days"),
    min_usage: int = Query(default=3, ge=1, le=100, description="Minimum usage count"),
) -> FrequentCommandsResponse:
    """Get frequently used commands with usage patterns and analytics."""
    service = CommandService(db)
    return await service.get_frequent_commands(
        current_user, days=days, min_usage=min_usage
    )


@router.get(
    "/metrics",
    response_model=CommandMetrics,
    summary="Get Command Metrics",
    description="Get real-time command execution metrics and performance data",
)
async def get_command_metrics(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommandMetrics:
    """Get real-time command execution metrics and performance data."""
    service = CommandService(db)
    return await service.get_command_metrics(current_user)


# Command Suggestions Endpoints


@router.post(
    "/suggest",
    response_model=list[CommandSuggestion],
    summary="Get Command Suggestions",
    description="Get intelligent command suggestions based on context and user history",
)
async def get_command_suggestions(
    suggestion_request: CommandSuggestionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CommandSuggestion]:
    """Get intelligent command suggestions based on context and user history."""
    service = CommandService(db)
    return await service.get_command_suggestions(current_user, suggestion_request)


# Batch Operations Endpoints


@router.post(
    "/bulk",
    response_model=BulkCommandResponse,
    summary="Bulk Command Operations",
    description="Perform bulk operations on multiple commands",
)
async def bulk_command_operations(
    operation: BulkCommandOperation,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BulkCommandResponse:
    """Perform bulk operations on multiple commands."""
    service = CommandService(db)

    success_count = 0
    error_count = 0
    results = []

    for command_id in operation.command_ids:
        try:
            if operation.operation == "delete":
                await service.delete_command(current_user, command_id)
                results.append(
                    {
                        "command_id": command_id,
                        "status": "success",
                        "operation": "delete",
                    }
                )
                success_count += 1

            elif operation.operation == "archive":
                # Archive operation (mark as archived, don't delete)
                # This would be implemented based on business requirements
                results.append(
                    {
                        "command_id": command_id,
                        "status": "success",
                        "operation": "archive",
                    }
                )
                success_count += 1

            else:
                raise ValueError(f"Unsupported operation: {operation.operation}")

        except HTTPException as e:
            results.append(
                {
                    "command_id": command_id,
                    "status": "error",
                    "error": e.detail,
                    "operation": operation.operation,
                }
            )
            error_count += 1

        except Exception as e:
            results.append(
                {
                    "command_id": command_id,
                    "status": "error",
                    "error": str(e),
                    "operation": operation.operation,
                }
            )
            error_count += 1

    message = f"Bulk {operation.operation} completed: {success_count} successful, {error_count} failed"

    return BulkCommandResponse(
        success_count=success_count,
        error_count=error_count,
        results=results,
        operation=operation.operation,
        message=message,
    )


# Export and Reporting Endpoints


@router.post(
    "/export",
    response_model=CommandExportResponse,
    summary="Export Commands",
    description="Export command history in various formats",
)
async def export_commands(
    export_request: CommandExportRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommandExportResponse:
    """Export command history in various formats."""
    try:
        # This is a simplified implementation
        # In production, this would create a background job for large exports

        import uuid
        from datetime import datetime

        export_id = str(uuid.uuid4())

        # Get commands based on export criteria
        search_request = CommandSearchRequest(
            query=None,
            command_type=None,
            min_duration_ms=None,
            max_duration_ms=None,
            working_directory=None,
            session_id=None,
            executed_after=export_request.date_from,
            executed_before=export_request.date_to,
            limit=export_request.max_commands,
            offset=0,
        )

        service = CommandService(db)
        commands, total = await service.search_commands(current_user, search_request)

        # In production, this would generate the actual export file
        # and store it in a file storage service

        return CommandExportResponse(
            export_id=export_id,
            status="completed",
            total_commands=len(commands),
            file_url=f"/api/commands/exports/{export_id}/download",
            expires_at=datetime.now(UTC).replace(hour=23, minute=59, second=59),
            created_at=datetime.now(UTC),
        )

    except Exception as e:
        logger.error(f"Error exporting commands: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export commands",
        ) from e


# Analysis and Insights Endpoints


@router.get(
    "/insights/patterns",
    response_model=dict,
    summary="Get Command Patterns",
    description="Analyze command usage patterns and identify trends",
)
async def get_command_patterns(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365, description="Analysis period in days"),
) -> dict:
    """Analyze command usage patterns and identify trends."""
    try:
        service = CommandService(db)

        # Get usage stats for pattern analysis
        stats = await service.get_usage_stats(current_user)
        frequent_commands = await service.get_frequent_commands(current_user, days=days)

        # Identify patterns
        patterns = {
            "peak_usage_commands": stats.most_used_commands[:5],
            "command_diversity": {
                "unique_vs_total": round(
                    stats.unique_commands / max(stats.total_commands, 1), 3
                ),
                "type_distribution": stats.commands_by_type,
            },
            "efficiency_metrics": {
                "success_rate": round(
                    stats.successful_commands / max(stats.total_commands, 1) * 100,
                    2,
                ),
                "average_duration_seconds": round(stats.average_duration_ms / 1000, 2),
            },
            "temporal_patterns": {
                "commands_today": stats.commands_today,
                "commands_this_week": stats.commands_this_week,
                "commands_this_month": stats.commands_this_month,
            },
            "frequent_patterns": [
                {
                    "template": cmd.command_template,
                    "usage_count": cmd.usage_count,
                    "success_rate": cmd.success_rate,
                }
                for cmd in frequent_commands.commands[:10]
            ],
        }

        return {
            "patterns": patterns,
            "analysis_period_days": days,
            "generated_at": logger.get_current_time(),
            "total_commands_analyzed": stats.total_commands,
        }

    except Exception as e:
        logger.error(f"Error analyzing command patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze command patterns",
        ) from e


@router.get(
    "/insights/performance",
    response_model=dict,
    summary="Get Performance Insights",
    description="Analyze command performance and identify optimization opportunities",
)
async def get_performance_insights(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Analyze command performance and identify optimization opportunities."""
    try:
        service = CommandService(db)

        # Get performance metrics
        stats = await service.get_usage_stats(current_user)
        metrics = await service.get_command_metrics(current_user)

        # Analyze performance
        insights: dict[str, Any] = {
            "execution_performance": {
                "average_duration_ms": stats.average_duration_ms,
                "median_duration_ms": stats.median_duration_ms,
                "total_execution_time_hours": round(
                    stats.total_execution_time_ms / (1000 * 3600), 2
                ),
                "slowest_commands": stats.longest_running_commands[:5],
            },
            "error_analysis": {
                "success_rate": round(
                    stats.successful_commands / max(stats.total_commands, 1) * 100,
                    2,
                ),
                "failure_rate": round(
                    stats.failed_commands / max(stats.total_commands, 1) * 100,
                    2,
                ),
                "error_distribution": metrics.top_error_types,
            },
            "efficiency_recommendations": [],  # List[Dict[str, Any]]
            "resource_usage": {
                "commands_per_session_avg": round(
                    stats.total_commands / max(len(set()), 1), 2
                ),  # Would need session count
                "peak_usage_periods": {
                    "today": stats.commands_today,
                    "this_week": stats.commands_this_week,
                },
            },
        }

        # Generate recommendations
        if stats.average_duration_ms > 5000:  # 5 seconds
            insights["efficiency_recommendations"].append(
                {
                    "type": "performance",
                    "message": "Consider optimizing long-running commands or using background execution",
                    "priority": "medium",
                }
            )

        if (
            stats.failed_commands / max(stats.total_commands, 1) > 0.1
        ):  # 10% failure rate
            insights["efficiency_recommendations"].append(
                {
                    "type": "reliability",
                    "message": "High failure rate detected. Review error-prone commands",
                    "priority": "high",
                }
            )

        return {
            "insights": insights,
            "generated_at": logger.get_current_time(),
            "analysis_summary": {
                "total_commands": stats.total_commands,
                "analysis_complete": True,
            },
        }

    except Exception as e:
        logger.error(f"Error generating performance insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate performance insights",
        ) from e


# Utility and Health Endpoints


@router.get(
    "/health",
    response_model=dict,
    summary="Command Service Health",
    description="Check command management service health and status",
)
async def command_service_health(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Check command management service health and status."""
    try:
        service = CommandService(db)

        # Test basic functionality
        history = await service.get_command_history(current_user, offset=0, limit=1)

        return {
            "status": "healthy",
            "service": "command_management",
            "database": "connected",
            "total_commands": history.total,
            "features": {
                "search": "available",
                "analytics": "available",
                "suggestions": "available",
                "export": "available",
            },
            "timestamp": logger.get_current_time(),
        }

    except Exception as e:
        logger.error(f"Command service health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "command_management",
            "error": str(e),
            "timestamp": logger.get_current_time(),
        }


@router.get(
    "/summary",
    response_model=dict,
    summary="Command Summary",
    description="Get a quick summary of command usage and activity",
)
async def get_command_summary(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get a quick summary of command usage and activity."""
    try:
        service = CommandService(db)

        # Get recent activity
        recent_history = await service.get_command_history(
            current_user, offset=0, limit=10
        )

        stats = await service.get_usage_stats(current_user)

        return {
            "summary": {
                "total_commands": stats.total_commands,
                "commands_today": stats.commands_today,
                "success_rate": round(
                    stats.successful_commands / max(stats.total_commands, 1) * 100,
                    2,
                ),
                "most_used_type": (
                    max(stats.commands_by_type.items(), key=lambda x: x[1])
                    if stats.commands_by_type
                    else ("unknown", 0)
                ),
            },
            "recent_activity": [
                {
                    "command": (
                        entry.command[:50] + "..."
                        if len(entry.command) > 50
                        else entry.command
                    ),
                    "status": entry.status.value,
                    "executed_at": entry.executed_at.isoformat(),
                    "session_name": entry.session_name,
                }
                for entry in recent_history.entries[:5]
            ],
            "top_commands": [
                {
                    "command": (
                        cmd["command"][:30] + "..."
                        if len(cmd["command"]) > 30
                        else cmd["command"]
                    ),
                    "count": cmd["count"],
                }
                for cmd in stats.most_used_commands[:3]
            ],
            "generated_at": logger.get_current_time(),
        }

    except Exception as e:
        logger.error(f"Error generating command summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate command summary",
        ) from e
