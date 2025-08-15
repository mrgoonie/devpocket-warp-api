"""
WebSocket router for DevPocket API.

Handles WebSocket endpoint setup, authentication, and message routing.
"""

import json
from typing import Optional
from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Query,
    HTTPException,
    status,
)
from jose import jwt

from app.core.config import settings
from app.core.logging import logger
from app.auth.security import decode_token
from .manager import connection_manager
from .protocols import create_error_message


websocket_router = APIRouter(prefix="/ws", tags=["websocket"])


async def authenticate_websocket(
    websocket: WebSocket, token: Optional[str] = None
) -> Optional[dict]:
    """
    Authenticate WebSocket connection using JWT token.

    Args:
        websocket: WebSocket connection
        token: JWT token for authentication

    Returns:
        User payload if authenticated, None otherwise
    """
    if not token:
        return None

    try:
        # Decode JWT token
        payload = decode_token(token)

        if not payload:
            return None

        return payload

    except jwt.JWTError:
        return None
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        return None


@websocket_router.websocket("/terminal")
async def terminal_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT authentication token"),
    device_id: Optional[str] = Query(None, description="Device identifier"),
):
    """
    WebSocket endpoint for real-time terminal communication.

    This endpoint handles:
    - JWT authentication via query parameter
    - Real-time terminal I/O streaming
    - SSH session management with PTY support
    - Terminal resizing and signal handling
    - Connection lifecycle management

    Query Parameters:
        token: JWT authentication token (required)
        device_id: Device identifier for session tracking (optional)

    WebSocket Protocol:
        The WebSocket uses JSON messages with the following structure:

        Input Message (Client -> Server):
        ```json
        {
            "type": "input",
            "session_id": "uuid",
            "data": "command text",
            "timestamp": "2023-01-01T12:00:00Z"
        }
        ```

        Output Message (Server -> Client):
        ```json
        {
            "type": "output",
            "session_id": "uuid",
            "data": "terminal output",
            "timestamp": "2023-01-01T12:00:00Z"
        }
        ```

        Connect Message (Client -> Server):
        ```json
        {
            "type": "connect",
            "data": {
                "session_type": "ssh",
                "ssh_profile_id": "uuid",
                "terminal_size": {"rows": 24, "cols": 80}
            }
        }
        ```

        Control Messages:
        ```json
        {
            "type": "resize",
            "session_id": "uuid",
            "data": {"rows": 30, "cols": 120}
        }
        ```

        ```json
        {
            "type": "signal",
            "session_id": "uuid",
            "data": {"signal": "SIGINT", "key": "ctrl+c"}
        }
        ```
    """
    connection_id = None

    try:
        # Authenticate connection
        if not token:
            logger.warning("WebSocket connection rejected: missing token")
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required"
            )
            return

        user_payload = await authenticate_websocket(websocket, token)
        if not user_payload:
            logger.warning("WebSocket connection rejected: invalid token")
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token"
            )
            return

        user_id = user_payload["sub"]
        device_id = device_id or "unknown_device"

        # Establish connection
        connection_id = await connection_manager.connect(websocket, user_id, device_id)

        logger.info(
            f"WebSocket terminal connection established: user_id={user_id}, connection_id={connection_id}"
        )

        # Main message loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()

                # Handle message through connection manager
                await connection_manager.handle_message(connection_id, data)

            except WebSocketDisconnect:
                logger.info(
                    f"WebSocket client disconnected: connection_id={connection_id}"
                )
                break
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Invalid JSON from WebSocket client {connection_id}: {e}"
                )
                # Send error message for invalid JSON
                try:
                    error_msg = create_error_message(
                        "invalid_json", "Invalid JSON message format"
                    )
                    await websocket.send_json(error_msg.model_dump(mode="json"))
                except Exception:
                    break  # Connection likely broken
            except Exception as e:
                logger.error(f"Error in WebSocket message loop {connection_id}: {e}")
                # Try to send error message
                try:
                    error_msg = create_error_message(
                        "message_processing_error", "Error processing message"
                    )
                    await websocket.send_json(error_msg.model_dump(mode="json"))
                except Exception:
                    break  # Connection likely broken

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(
                code=status.WS_1011_INTERNAL_ERROR, reason="Internal server error"
            )
        except Exception:
            pass  # Connection might already be closed

    finally:
        # Clean up connection
        if connection_id:
            await connection_manager.disconnect(connection_id)


@websocket_router.get("/stats")
async def websocket_stats():
    """
    Get WebSocket connection statistics.

    Returns:
        Statistics about active WebSocket connections and sessions
    """
    try:
        stats = {
            "active_connections": connection_manager.get_connection_count(),
            "active_sessions": connection_manager.get_session_count(),
            "uptime": "active",  # Could be enhanced with actual uptime tracking
        }

        return {"status": "success", "data": stats}

    except Exception as e:
        logger.error(f"Failed to get WebSocket stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get WebSocket statistics",
        )
