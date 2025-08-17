"""
WebSocket module for DevPocket API.

This module handles real-time terminal communication through WebSockets,
including PTY support, SSH integration, and terminal emulation.
"""

from .manager import ConnectionManager
from .protocols import MessageType, TerminalMessage
from .router import websocket_router
from .terminal import TerminalSession

__all__ = [
    "ConnectionManager",
    "TerminalSession",
    "TerminalMessage",
    "MessageType",
    "websocket_router",
]
