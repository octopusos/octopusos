"""WebUI WebSocket handlers (minimal required interfaces)."""

from .chat import ConnectionManager, manager
from . import chat, coding, governance

__all__ = ["chat", "coding", "governance", "ConnectionManager", "manager"]
