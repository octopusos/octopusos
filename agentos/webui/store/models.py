"""
WebUI Data Models

Defines data structures for WebUI session and message management.
These models are independent of Core task/run models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json


@dataclass
class Session:
    """
    WebUI Session (chat conversation container)

    Lifecycle: Created when user starts chat, persists across restarts.
    Cleanup: Configurable retention (e.g., 30 days inactive).
    """
    session_id: str
    user_id: str = "default"  # Future: multi-user support
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_db_row(cls, row: tuple) -> "Session":
        """
        Parse from SQLite row:
        (session_id, user_id, created_at, updated_at, metadata_json)
        """
        return cls(
            session_id=row[0],
            user_id=row[1],
            created_at=datetime.fromisoformat(row[2]),
            updated_at=datetime.fromisoformat(row[3]),
            metadata=json.loads(row[4]) if row[4] else {}
        )

    def to_dict(self) -> dict:
        """Serialize for API response"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class Message:
    """
    WebUI Message (single chat message)

    Lifecycle: Created per user/assistant turn, immutable after creation.
    Cleanup: Cascaded when parent session deleted.
    """
    message_id: str
    session_id: str
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_db_row(cls, row: tuple) -> "Message":
        """
        Parse from SQLite row:
        (message_id, session_id, role, content, created_at, metadata_json)
        """
        return cls(
            message_id=row[0],
            session_id=row[1],
            role=row[2],
            content=row[3],
            created_at=datetime.fromisoformat(row[4]),
            metadata=json.loads(row[5]) if row[5] else {}
        )

    def to_dict(self) -> dict:
        """Serialize for API response"""
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate message data

        Returns: (is_valid, error_message)
        """
        if self.role not in ("user", "assistant", "system"):
            return False, f"Invalid role: {self.role}"

        if not self.content or not self.content.strip():
            return False, "Message content cannot be empty"

        if len(self.content) > 100_000:  # 100KB limit
            return False, "Message content too large (>100KB)"

        return True, None
