"""
Command management service layer for DevPocket API.

Contains business logic for command history, analytics, search, and related operations.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from collections import Counter, defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.core.logging import logger
from app.models.user import User
from app.models.command import Command
from app.models.session import Session
from app.repositories.command import CommandRepository
from app.repositories.session import SessionRepository
from .schemas import (
    CommandResponse,
    CommandSearchRequest,
    CommandHistoryResponse,
    CommandHistoryEntry,
    CommandUsageStats,
    SessionCommandStats,
    CommandTypeStats,
    FrequentCommand,
    FrequentCommandsResponse,
    CommandSuggestion,
    CommandSuggestionRequest,
    CommandMetrics,
    CommandType,
    CommandStatus,
)


class CommandService:
    """Service class for command management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.command_repo = CommandRepository(session)
        self.session_repo = SessionRepository(session)

        # Command classification patterns
        self.command_patterns = {
            CommandType.SYSTEM: [
                r"^(ps|top|htop|kill|killall|jobs|bg|fg|nohup)",
                r"^(uptime|who|w|last|history)",
                r"^(uname|hostname|whoami|id|groups)",
            ],
            CommandType.FILE: [
                r"^(ls|ll|la|dir)",
                r"^(cp|mv|rm|mkdir|rmdir|touch)",
                r"^(cat|less|more|head|tail|grep|find|locate)",
                r"^(chmod|chown|chgrp|stat|file)",
            ],
            CommandType.NETWORK: [
                r"^(ping|curl|wget|ssh|scp|rsync)",
                r"^(netstat|ss|lsof|nmap|telnet)",
                r"^(ifconfig|ip|route|traceroute|dig|nslookup)",
            ],
            CommandType.GIT: [
                r"^git\s+(clone|pull|push|commit|add|status|log|diff|branch|checkout|merge|rebase)"
            ],
            CommandType.PACKAGE: [
                r"^(apt|yum|dnf|pip|npm|yarn|brew|pacman)",
                r"^(dpkg|rpm|snap|flatpak)",
            ],
            CommandType.DATABASE: [
                r"^(mysql|psql|sqlite|mongo|redis-cli)",
                r"^(pg_dump|mysqldump|mongodump)",
            ],
        }

        # Dangerous command patterns
        self.dangerous_patterns = [
            r"^(sudo\s+)?rm\s+.*(-rf|--recursive.*--force)",
            r"^(sudo\s+)?dd\s+.*of=/dev/",
            r"^(sudo\s+)?(mkfs|fdisk|parted)",
            r"^(sudo\s+)?chmod\s+777",
            r"^(sudo\s+)?chown.*-R.*/",
            r":(){ :|:& };:",  # Fork bomb
            r"^(sudo\s+)?mv\s+.*\s+/dev/null",
            r"^(sudo\s+)?>\s*/dev/sda",
            r"^(sudo\s+)?shutdown|reboot|halt",
        ]

    async def get_command_history(
        self,
        user: User,
        session_id: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> CommandHistoryResponse:
        """Get command history with session context."""
        try:
            # Get commands with session information
            commands = await self.command_repo.get_user_commands_with_session(
                user.id, session_id=session_id, offset=offset, limit=limit
            )

            # Convert to history entries
            entries = []
            for cmd in commands:
                entry = CommandHistoryEntry(
                    id=cmd.id,
                    command=cmd.command,
                    working_directory=cmd.working_directory or "/",
                    status=CommandStatus(cmd.status),
                    exit_code=cmd.exit_code,
                    executed_at=cmd.executed_at,
                    duration_ms=cmd.duration_ms,
                    session_id=cmd.session_id,
                    session_name=cmd.session.name if cmd.session else "Unknown",
                    session_type=cmd.session.session_type if cmd.session else "unknown",
                    command_type=CommandType(cmd.command_type or "unknown"),
                    is_dangerous=cmd.is_dangerous or False,
                    output_size=len(cmd.stdout) + len(cmd.stderr)
                    if cmd.stdout and cmd.stderr
                    else 0,
                    has_output=bool(cmd.stdout),
                    has_error=bool(cmd.stderr),
                )
                entries.append(entry)

            # Get total count
            total = await self.command_repo.count_user_commands(
                user.id, session_id=session_id
            )

            return CommandHistoryResponse(
                entries=entries,
                total=total,
                offset=offset,
                limit=limit,
                filters_applied={"session_id": session_id} if session_id else None,
            )

        except Exception as e:
            logger.error(f"Error getting command history: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve command history",
            )

    async def search_commands(
        self, user: User, search_request: CommandSearchRequest
    ) -> Tuple[List[CommandResponse], int]:
        """Search commands with advanced filters."""
        try:
            # Build search criteria
            criteria = {"user_id": user.id}

            if search_request.session_id:
                criteria["session_id"] = search_request.session_id

            if search_request.command_type:
                criteria["command_type"] = search_request.command_type.value

            if search_request.status:
                criteria["status"] = search_request.status.value

            if search_request.exit_code is not None:
                criteria["exit_code"] = search_request.exit_code

            # Execute search
            commands = await self.command_repo.search_commands(
                criteria=criteria,
                query=search_request.query,
                executed_after=search_request.executed_after,
                executed_before=search_request.executed_before,
                min_duration_ms=search_request.min_duration_ms,
                max_duration_ms=search_request.max_duration_ms,
                has_output=search_request.has_output,
                has_error=search_request.has_error,
                output_contains=search_request.output_contains,
                working_directory=search_request.working_directory,
                include_dangerous=search_request.include_dangerous,
                only_dangerous=search_request.only_dangerous,
                sort_by=search_request.sort_by,
                sort_order=search_request.sort_order,
                offset=search_request.offset,
                limit=search_request.limit,
            )

            # Get total count
            total = await self.command_repo.count_commands_with_criteria(criteria)

            # Convert to response objects
            command_responses = []
            for cmd in commands:
                response = CommandResponse(
                    id=cmd.id,
                    user_id=cmd.user_id,
                    session_id=cmd.session_id,
                    command=cmd.command,
                    working_directory=cmd.working_directory,
                    environment=cmd.environment or {},
                    timeout_seconds=cmd.timeout_seconds or 30,
                    capture_output=cmd.capture_output,
                    status=CommandStatus(cmd.status),
                    exit_code=cmd.exit_code,
                    stdout=cmd.stdout or "",
                    stderr=cmd.stderr or "",
                    output_truncated=cmd.output_truncated or False,
                    output_size=len(cmd.stdout or "") + len(cmd.stderr or ""),
                    executed_at=cmd.executed_at,
                    started_at=cmd.started_at,
                    completed_at=cmd.completed_at,
                    duration_ms=cmd.duration_ms,
                    command_type=CommandType(cmd.command_type or "unknown"),
                    is_dangerous=cmd.is_dangerous or False,
                    pid=cmd.pid,
                    signal=cmd.signal,
                    sequence_number=cmd.sequence_number or 0,
                    parent_command_id=cmd.parent_command_id,
                )
                command_responses.append(response)

            return command_responses, total

        except Exception as e:
            logger.error(f"Error searching commands: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to search commands",
            )

    async def get_command_details(self, user: User, command_id: str) -> CommandResponse:
        """Get detailed command information."""
        try:
            command = await self.command_repo.get_by_id(command_id)

            if not command or command.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Command not found"
                )

            return CommandResponse(
                id=command.id,
                user_id=command.user_id,
                session_id=command.session_id,
                command=command.command,
                working_directory=command.working_directory,
                environment=command.environment or {},
                timeout_seconds=command.timeout_seconds or 30,
                capture_output=command.capture_output,
                status=CommandStatus(command.status),
                exit_code=command.exit_code,
                stdout=command.stdout or "",
                stderr=command.stderr or "",
                output_truncated=command.output_truncated or False,
                output_size=len(command.stdout or "") + len(command.stderr or ""),
                executed_at=command.executed_at,
                started_at=command.started_at,
                completed_at=command.completed_at,
                duration_ms=command.duration_ms,
                command_type=CommandType(command.command_type or "unknown"),
                is_dangerous=command.is_dangerous or False,
                pid=command.pid,
                signal=command.signal,
                sequence_number=command.sequence_number or 0,
                parent_command_id=command.parent_command_id,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting command details: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get command details",
            )

    async def delete_command(self, user: User, command_id: str) -> bool:
        """Delete a command from history."""
        try:
            command = await self.command_repo.get_by_id(command_id)

            if not command or command.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Command not found"
                )

            await self.command_repo.delete(command_id)
            await self.session.commit()

            logger.info(f"Command deleted: {command_id} by user {user.username}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting command: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete command",
            )

    async def get_usage_stats(self, user: User) -> CommandUsageStats:
        """Get comprehensive command usage statistics."""
        try:
            # Get all user commands for analysis
            all_commands = await self.command_repo.get_user_commands(
                user.id, offset=0, limit=10000  # Reasonable limit for stats
            )

            if not all_commands:
                return CommandUsageStats(
                    total_commands=0,
                    unique_commands=0,
                    successful_commands=0,
                    failed_commands=0,
                    average_duration_ms=0,
                    median_duration_ms=0,
                    total_execution_time_ms=0,
                    commands_by_type={},
                    commands_by_status={},
                    commands_today=0,
                    commands_this_week=0,
                    commands_this_month=0,
                    most_used_commands=[],
                    longest_running_commands=[],
                )

            # Basic counts
            total_commands = len(all_commands)
            unique_commands = len(set(cmd.command for cmd in all_commands))
            successful_commands = len(
                [cmd for cmd in all_commands if cmd.exit_code == 0]
            )
            failed_commands = len([cmd for cmd in all_commands if cmd.exit_code != 0])

            # Duration statistics
            durations = [cmd.duration_ms for cmd in all_commands if cmd.duration_ms]
            avg_duration = sum(durations) / len(durations) if durations else 0
            median_duration = sorted(durations)[len(durations) // 2] if durations else 0
            total_execution_time = sum(durations)

            # Breakdown by type and status
            type_counter = Counter(
                cmd.command_type or "unknown" for cmd in all_commands
            )
            status_counter = Counter(cmd.status for cmd in all_commands)

            # Time-based counts
            now = datetime.now(timezone.utc)
            today = now.date()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)

            commands_today = len(
                [cmd for cmd in all_commands if cmd.executed_at.date() == today]
            )
            commands_this_week = len(
                [cmd for cmd in all_commands if cmd.executed_at >= week_ago]
            )
            commands_this_month = len(
                [cmd for cmd in all_commands if cmd.executed_at >= month_ago]
            )

            # Most used commands
            command_counter = Counter(cmd.command for cmd in all_commands)
            most_used = [
                {
                    "command": cmd,
                    "count": count,
                    "percentage": round((count / total_commands) * 100, 2),
                }
                for cmd, count in command_counter.most_common(10)
            ]

            # Longest running commands
            sorted_by_duration = sorted(
                all_commands, key=lambda x: x.duration_ms or 0, reverse=True
            )
            longest_running = [
                {
                    "command": cmd.command,
                    "duration_ms": cmd.duration_ms,
                    "duration_seconds": round((cmd.duration_ms or 0) / 1000, 2),
                    "executed_at": cmd.executed_at.isoformat(),
                }
                for cmd in sorted_by_duration[:10]
            ]

            return CommandUsageStats(
                total_commands=total_commands,
                unique_commands=unique_commands,
                successful_commands=successful_commands,
                failed_commands=failed_commands,
                average_duration_ms=round(avg_duration, 2),
                median_duration_ms=median_duration,
                total_execution_time_ms=total_execution_time,
                commands_by_type=dict(type_counter),
                commands_by_status=dict(status_counter),
                commands_today=commands_today,
                commands_this_week=commands_this_week,
                commands_this_month=commands_this_month,
                most_used_commands=most_used,
                longest_running_commands=longest_running,
            )

        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get command usage statistics",
            )

    async def get_session_command_stats(
        self, user: User, session_id: Optional[str] = None
    ) -> List[SessionCommandStats]:
        """Get command statistics grouped by session."""
        try:
            # Get sessions with command counts
            sessions_data = await self.command_repo.get_session_command_stats(user.id)

            stats = []
            for session_data in sessions_data:
                session_stats = SessionCommandStats(
                    session_id=session_data["session_id"],
                    session_name=session_data["session_name"],
                    total_commands=session_data["total_commands"],
                    successful_commands=session_data["successful_commands"],
                    failed_commands=session_data["failed_commands"],
                    average_duration_ms=session_data["average_duration_ms"],
                    last_command_at=session_data["last_command_at"],
                    most_used_command=session_data["most_used_command"],
                )
                stats.append(session_stats)

            return stats

        except Exception as e:
            logger.error(f"Error getting session command stats: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get session command statistics",
            )

    async def get_frequent_commands(
        self, user: User, days: int = 30, min_usage: int = 3
    ) -> FrequentCommandsResponse:
        """Get frequently used commands with analysis."""
        try:
            # Get commands from the specified time period
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            commands = await self.command_repo.get_user_commands_since(
                user.id, since=cutoff_date
            )

            if not commands:
                return FrequentCommandsResponse(
                    commands=[],
                    total_analyzed=0,
                    analysis_period_days=days,
                    generated_at=datetime.now(timezone.utc),
                )

            # Analyze command patterns
            command_analysis = self._analyze_command_patterns(commands, min_usage)

            frequent_commands = []
            for pattern, data in command_analysis.items():
                if data["count"] >= min_usage:
                    # Calculate sessions used
                    sessions_used = len(
                        set(
                            cmd.session_id
                            for cmd in commands
                            if self._matches_pattern(cmd.command, pattern)
                        )
                    )

                    frequent_cmd = FrequentCommand(
                        command_template=pattern,
                        usage_count=data["count"],
                        last_used=data["last_used"],
                        success_rate=data["success_rate"],
                        average_duration_ms=data["average_duration"],
                        variations=data["variations"][:10],  # Limit variations
                        sessions_used=sessions_used,
                        command_type=self._classify_command(pattern),
                    )
                    frequent_commands.append(frequent_cmd)

            # Sort by usage count
            frequent_commands.sort(key=lambda x: x.usage_count, reverse=True)

            return FrequentCommandsResponse(
                commands=frequent_commands[:50],  # Limit to top 50
                total_analyzed=len(commands),
                analysis_period_days=days,
                generated_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Error getting frequent commands: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to analyze frequent commands",
            )

    async def get_command_suggestions(
        self, user: User, request: CommandSuggestionRequest
    ) -> List[CommandSuggestion]:
        """Get command suggestions based on context."""
        try:
            suggestions = []

            # Get user's command history for context
            recent_commands = await self.command_repo.get_user_recent_commands(
                user.id, limit=100
            )

            # Analyze context and generate suggestions
            context_lower = request.context.lower()

            # File operations suggestions
            if any(
                word in context_lower for word in ["list", "show", "files", "directory"]
            ):
                suggestions.extend(self._get_file_operation_suggestions(context_lower))

            # System monitoring suggestions
            if any(
                word in context_lower
                for word in ["process", "memory", "cpu", "monitor"]
            ):
                suggestions.extend(
                    self._get_system_monitoring_suggestions(context_lower)
                )

            # Network suggestions
            if any(
                word in context_lower
                for word in ["network", "connection", "ping", "download"]
            ):
                suggestions.extend(self._get_network_suggestions(context_lower))

            # Git suggestions
            if any(
                word in context_lower
                for word in ["git", "repository", "commit", "branch"]
            ):
                suggestions.extend(self._get_git_suggestions(context_lower))

            # Based on user's command history patterns
            if recent_commands:
                suggestions.extend(
                    self._get_personalized_suggestions(recent_commands, context_lower)
                )

            # Sort by confidence and limit results
            suggestions.sort(key=lambda x: x.confidence, reverse=True)
            return suggestions[: request.max_suggestions]

        except Exception as e:
            logger.error(f"Error getting command suggestions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate command suggestions",
            )

    async def get_command_metrics(self, user: User) -> CommandMetrics:
        """Get real-time command execution metrics."""
        try:
            now = datetime.now(timezone.utc)
            today = now.date()
            yesterday = now - timedelta(days=1)

            # Get recent commands for analysis
            recent_commands = await self.command_repo.get_user_commands_since(
                user.id, since=yesterday
            )

            # Calculate metrics
            active_commands = len(
                [cmd for cmd in recent_commands if cmd.status in ["pending", "running"]]
            )

            completed_today = len(
                [
                    cmd
                    for cmd in recent_commands
                    if cmd.executed_at.date() == today and cmd.status == "completed"
                ]
            )

            failed_today = len(
                [
                    cmd
                    for cmd in recent_commands
                    if cmd.executed_at.date() == today and cmd.status == "failed"
                ]
            )

            # Response time calculation
            completed_commands = [
                cmd
                for cmd in recent_commands
                if cmd.status == "completed" and cmd.duration_ms
            ]
            avg_response_time = (
                sum(cmd.duration_ms for cmd in completed_commands)
                / len(completed_commands)
                if completed_commands
                else 0
            )

            # Success rate for last 24 hours
            total_24h = len(
                [cmd for cmd in recent_commands if cmd.executed_at >= yesterday]
            )
            successful_24h = len(
                [
                    cmd
                    for cmd in recent_commands
                    if cmd.executed_at >= yesterday and cmd.exit_code == 0
                ]
            )
            success_rate_24h = (
                (successful_24h / total_24h * 100) if total_24h > 0 else 100
            )

            # Error analysis
            error_commands = [
                cmd for cmd in recent_commands if cmd.exit_code != 0 and cmd.stderr
            ]
            error_counter = Counter()
            for cmd in error_commands:
                # Simple error classification
                if "permission denied" in cmd.stderr.lower():
                    error_counter["permission_denied"] += 1
                elif "not found" in cmd.stderr.lower():
                    error_counter["not_found"] += 1
                elif "timeout" in cmd.stderr.lower():
                    error_counter["timeout"] += 1
                else:
                    error_counter["other"] += 1

            top_errors = [
                {"error_type": error_type, "count": count}
                for error_type, count in error_counter.most_common(5)
            ]

            return CommandMetrics(
                active_commands=active_commands,
                queued_commands=0,  # Would be from queue system
                completed_today=completed_today,
                failed_today=failed_today,
                avg_response_time_ms=round(avg_response_time, 2),
                success_rate_24h=round(success_rate_24h, 2),
                total_cpu_time_ms=sum(cmd.duration_ms or 0 for cmd in recent_commands),
                peak_memory_usage_mb=None,  # Would need system monitoring
                top_error_types=top_errors,
                timestamp=now,
            )

        except Exception as e:
            logger.error(f"Error getting command metrics: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get command metrics",
            )

    # Private helper methods

    def _classify_command(self, command: str) -> CommandType:
        """Classify command based on patterns."""
        for cmd_type, patterns in self.command_patterns.items():
            for pattern in patterns:
                if re.match(pattern, command.strip(), re.IGNORECASE):
                    return cmd_type
        return CommandType.UNKNOWN

    def _is_dangerous_command(self, command: str) -> bool:
        """Check if command is potentially dangerous."""
        for pattern in self.dangerous_patterns:
            if re.search(pattern, command.strip(), re.IGNORECASE):
                return True
        return False

    def _analyze_command_patterns(
        self, commands: List[Command], min_usage: int
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze commands to find patterns and templates."""
        pattern_data = defaultdict(
            lambda: {
                "count": 0,
                "variations": [],
                "success_count": 0,
                "durations": [],
                "last_used": None,
            }
        )

        for cmd in commands:
            # Create a pattern by replacing variable parts
            pattern = self._create_command_pattern(cmd.command)

            data = pattern_data[pattern]
            data["count"] += 1
            data["variations"].append(cmd.command)

            if cmd.exit_code == 0:
                data["success_count"] += 1

            if cmd.duration_ms:
                data["durations"].append(cmd.duration_ms)

            if not data["last_used"] or cmd.executed_at > data["last_used"]:
                data["last_used"] = cmd.executed_at

        # Calculate derived metrics
        result = {}
        for pattern, data in pattern_data.items():
            if data["count"] >= min_usage:
                result[pattern] = {
                    "count": data["count"],
                    "variations": list(set(data["variations"])),
                    "success_rate": (data["success_count"] / data["count"]) * 100,
                    "average_duration": (
                        sum(data["durations"]) / len(data["durations"])
                        if data["durations"]
                        else 0
                    ),
                    "last_used": data["last_used"],
                }

        return result

    def _create_command_pattern(self, command: str) -> str:
        """Create a command pattern by replacing variable parts."""
        # Simple pattern creation - replace paths, numbers, and common variables
        pattern = command

        # Replace file paths
        pattern = re.sub(r"/[/\w.-]*", "/path", pattern)

        # Replace numbers
        pattern = re.sub(r"\b\d+\b", "N", pattern)

        # Replace IP addresses
        pattern = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "IP", pattern)

        # Replace URLs
        pattern = re.sub(r"https?://[^\s]+", "URL", pattern)

        return pattern

    def _matches_pattern(self, command: str, pattern: str) -> bool:
        """Check if command matches the given pattern."""
        cmd_pattern = self._create_command_pattern(command)
        return cmd_pattern == pattern

    def _get_file_operation_suggestions(self, context: str) -> List[CommandSuggestion]:
        """Generate file operation command suggestions."""
        suggestions = []

        if "list" in context or "show" in context:
            suggestions.append(
                CommandSuggestion(
                    command="ls -la",
                    description="List files and directories with detailed information",
                    confidence=0.9,
                    category=CommandType.FILE,
                    examples=["ls -la", "ls -lah", "ll"],
                    is_safe=True,
                )
            )

        if "directory" in context:
            suggestions.append(
                CommandSuggestion(
                    command="pwd",
                    description="Show current working directory",
                    confidence=0.8,
                    category=CommandType.FILE,
                    is_safe=True,
                )
            )

        return suggestions

    def _get_system_monitoring_suggestions(
        self, context: str
    ) -> List[CommandSuggestion]:
        """Generate system monitoring suggestions."""
        suggestions = []

        if "process" in context:
            suggestions.append(
                CommandSuggestion(
                    command="ps aux",
                    description="Show all running processes",
                    confidence=0.9,
                    category=CommandType.SYSTEM,
                    examples=["ps aux", "ps -ef"],
                    is_safe=True,
                )
            )

        if "memory" in context or "cpu" in context:
            suggestions.append(
                CommandSuggestion(
                    command="top",
                    description="Display system resource usage in real-time",
                    confidence=0.8,
                    category=CommandType.SYSTEM,
                    examples=["top", "htop"],
                    is_safe=True,
                )
            )

        return suggestions

    def _get_network_suggestions(self, context: str) -> List[CommandSuggestion]:
        """Generate network-related suggestions."""
        suggestions = []

        if "ping" in context:
            suggestions.append(
                CommandSuggestion(
                    command="ping google.com",
                    description="Test network connectivity to a host",
                    confidence=0.9,
                    category=CommandType.NETWORK,
                    examples=["ping google.com", "ping -c 4 example.com"],
                    is_safe=True,
                )
            )

        return suggestions

    def _get_git_suggestions(self, context: str) -> List[CommandSuggestion]:
        """Generate git-related suggestions."""
        suggestions = []

        if "status" in context:
            suggestions.append(
                CommandSuggestion(
                    command="git status",
                    description="Show the working tree status",
                    confidence=0.9,
                    category=CommandType.GIT,
                    is_safe=True,
                )
            )

        return suggestions

    def _get_personalized_suggestions(
        self, recent_commands: List[Command], context: str
    ) -> List[CommandSuggestion]:
        """Generate personalized suggestions based on user history."""
        suggestions = []

        # Analyze user's most common commands
        command_counter = Counter(cmd.command for cmd in recent_commands)

        for command, count in command_counter.most_common(5):
            if any(word in command.lower() for word in context.split()):
                suggestions.append(
                    CommandSuggestion(
                        command=command,
                        description=f"Frequently used command (used {count} times recently)",
                        confidence=0.7,
                        category=self._classify_command(command),
                        is_safe=not self._is_dangerous_command(command),
                    )
                )

        return suggestions
