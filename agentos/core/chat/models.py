"""Data models for Chat Mode"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, Dict, Any
import json


@dataclass
class ChatSession:
    """Represents a chat conversation session"""
    session_id: str
    title: str
    task_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
    
    @classmethod
    def from_db_row(cls, row) -> "ChatSession":
        """Create ChatSession from database row"""
        return cls(
            session_id=row["session_id"],
            title=row["title"] or "Untitled Chat",
            task_id=row["task_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "session_id": self.session_id,
            "title": self.title,
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ChatMessage:
    """Represents a single message in a chat session"""
    message_id: str
    session_id: str
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    created_at: datetime
    metadata: Dict[str, Any]
    
    @classmethod
    def from_db_row(cls, row) -> "ChatMessage":
        """Create ChatMessage from database row"""
        return cls(
            message_id=row["message_id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            created_at=datetime.fromisoformat(row["created_at"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for API/logging)"""
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }
    
    def to_openai_format(self) -> Dict[str, str]:
        """Convert to OpenAI chat format"""
        return {
            "role": self.role,
            "content": self.content
        }
    
    def estimate_tokens(self) -> int:
        """Estimate token count (rough heuristic)"""
        # Simple heuristic: length * 1.3
        return int(len(self.content) * 1.3)
