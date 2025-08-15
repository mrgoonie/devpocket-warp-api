"""
WebSocket module for DevPocket API.

This module handles real-time terminal communication through WebSockets,
including PTY support, SSH integration, and terminal emulation.
"""

from .manager import ConnectionManager
from .terminal import TerminalSession
from .protocols import TerminalMessage, MessageType
from .router import websocket_router

__all__ = [
    "ConnectionManager",
    "TerminalSession",
    "TerminalMessage",
    "MessageType",
    "websocket_router",
]
