"""
Logging configuration for DevPocket API.
"""

import logging
import sys
from datetime import datetime
from typing import Any

from app.core.config import settings


def setup_logging() -> logging.Logger:
    """
    Set up logging configuration for the application.

    Returns:
        logging.Logger: Configured logger instance
    """

    # Create logger
    logger = logging.getLogger("devpocket")
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, settings.log_level.upper()))

    # Create formatter
    if settings.log_format == "json":
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent duplicate logs
    logger.propagate = False

    return logger


def log_request(
    method: str,
    url: str,
    status_code: int,
    duration: float,
    user_id: str | None = None,
) -> None:
    """
    Log HTTP request information.

    Args:
        method: HTTP method
        url: Request URL
        status_code: HTTP status code
        duration: Request duration in seconds
        user_id: Optional user ID
    """
    logger = logging.getLogger("devpocket.requests")

    log_data = {
        "method": method,
        "url": url,
        "status_code": status_code,
        "duration": duration,
    }

    if user_id:
        log_data["user_id"] = user_id

    if settings.log_format == "json":
        import json

        logger.info(json.dumps(log_data))
    else:
        logger.info(
            f"{method} {url} - {status_code} - {duration:.3f}s"
            + (f" - User: {user_id}" if user_id else "")
        )


def log_websocket_event(
    event_type: str, session_id: str, user_id: str | None = None, **kwargs: Any
) -> None:
    """
    Log WebSocket event information.

    Args:
        event_type: Type of WebSocket event
        session_id: WebSocket session ID
        user_id: Optional user ID
        **kwargs: Additional event data
    """
    logger = logging.getLogger("devpocket.websocket")

    log_data = {"event_type": event_type, "session_id": session_id, **kwargs}

    if user_id:
        log_data["user_id"] = user_id

    if settings.log_format == "json":
        import json

        logger.info(json.dumps(log_data))
    else:
        logger.info(
            f"WebSocket {event_type} - Session: {session_id}"
            + (f" - User: {user_id}" if user_id else "")
        )


def log_error(
    error: Exception,
    context: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> None:
    """
    Log error information with context.

    Args:
        error: Exception instance
        context: Additional context information
        user_id: Optional user ID
    """
    logger = logging.getLogger("devpocket.errors")

    log_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        **(context or {}),
    }

    if user_id:
        log_data["user_id"] = user_id

    if settings.log_format == "json":
        import json

        logger.error(json.dumps(log_data))
    else:
        logger.error(
            f"Error: {type(error).__name__} - {error!s}"
            + (f" - User: {user_id}" if user_id else "")
        )


def log_ssh_event(
    event_type: str,
    session_id: str,
    host: str,
    user_id: str | None = None,
    **kwargs: Any,
) -> None:
    """
    Log SSH connection event.

    Args:
        event_type: Type of SSH event (connect, disconnect, command, etc.)
        session_id: SSH session ID
        host: SSH host
        user_id: Optional user ID
        **kwargs: Additional event data
    """
    logger = logging.getLogger("devpocket.ssh")

    log_data = {
        "event_type": event_type,
        "session_id": session_id,
        "host": host,
        **kwargs,
    }

    if user_id:
        log_data["user_id"] = user_id

    if settings.log_format == "json":
        import json

        logger.info(json.dumps(log_data))
    else:
        logger.info(
            f"SSH {event_type} - Session: {session_id} - Host: {host}"
            + (f" - User: {user_id}" if user_id else "")
        )


def log_ai_event(
    event_type: str,
    model: str,
    prompt_length: int,
    response_length: int | None = None,
    user_id: str | None = None,
    **kwargs: Any,
) -> None:
    """
    Log AI service event.

    Args:
        event_type: Type of AI event (suggestion, explanation, etc.)
        model: AI model used
        prompt_length: Length of the prompt
        response_length: Optional length of the response
        user_id: Optional user ID
        **kwargs: Additional event data
    """
    logger = logging.getLogger("devpocket.ai")

    log_data = {
        "event_type": event_type,
        "model": model,
        "prompt_length": prompt_length,
        **kwargs,
    }

    if response_length:
        log_data["response_length"] = response_length

    if user_id:
        log_data["user_id"] = user_id

    if settings.log_format == "json":
        import json

        logger.info(json.dumps(log_data))
    else:
        logger.info(
            f"AI {event_type} - Model: {model} - Prompt: {prompt_length} chars"
            + (f" - User: {user_id}" if user_id else "")
        )


def get_current_time() -> datetime:
    """
    Get current timestamp for logging purposes.

    Returns:
        datetime: Current datetime
    """
    return datetime.now()


# Custom logger class with additional methods
class DevPocketLogger:
    def __init__(self, base_logger: Any) -> None:
        self._logger = base_logger

    def __getattr__(self, name: str) -> Any:
        # Delegate all unknown attributes to the base logger
        return getattr(self._logger, name)

    def get_current_time(self) -> datetime:
        """Get current timestamp for logging purposes."""
        return datetime.now()


# Initialize logger
base_logger = setup_logging()
logger = DevPocketLogger(base_logger)
