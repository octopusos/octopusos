"""
WebUI Storage Layer

This module provides storage abstractions for WebUI data (sessions, messages, events).
These are kept separate from Core tables (tasks, runs, artifacts) due to different
lifecycle, concurrency patterns, and cleanup strategies.

Architecture:
- SessionStore: Abstract interface
- MemorySessionStore: In-memory implementation (testing, fallback)
- SQLiteSessionStore: Production implementation (persistent)
"""

from .session_store import SessionStore, MemorySessionStore, SQLiteSessionStore
from .models import Session, Message

__all__ = [
    "SessionStore",
    "MemorySessionStore",
    "SQLiteSessionStore",
    "Session",
    "Message",
]
