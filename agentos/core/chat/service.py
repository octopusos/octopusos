"""Chat service for managing chat sessions and messages"""

import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import logging

from agentos.core.chat.models import ChatSession, ChatMessage
from agentos.store import get_db_path

logger = logging.getLogger(__name__)


def _generate_ulid() -> str:
    """Generate a ULID (Universally Unique Lexicographically Sortable Identifier)"""
    from ulid import ULID
    return str(ULID())


class ChatService:
    """Service for managing chat sessions and messages"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize ChatService
        
        Args:
            db_path: Path to database file (defaults to AgentOS registry DB)
        """
        self.db_path = db_path or get_db_path()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    # ============================================
    # Session Management
    # ============================================
    
    def create_session(
        self,
        title: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> ChatSession:
        """Create a new chat session

        Args:
            title: Session title (defaults to "New Chat")
            task_id: Optional Task ID to associate with
            metadata: Session metadata (model, provider, context_budget, etc.)
            session_id: Optional session ID (auto-generated if not provided)

        Returns:
            Created ChatSession
        """
        session_id = session_id or _generate_ulid()
        title = title or "New Chat"
        metadata = metadata or {}
        
        # Set default metadata
        if "model" not in metadata:
            metadata["model"] = "local"
        if "provider" not in metadata:
            metadata["provider"] = "ollama"
        if "context_budget" not in metadata:
            metadata["context_budget"] = 8000
        if "rag_enabled" not in metadata:
            metadata["rag_enabled"] = True
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                INSERT INTO chat_sessions (session_id, title, task_id, metadata)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, title, task_id, json.dumps(metadata))
            )
            conn.commit()
            
            logger.info(f"Created chat session: {session_id} - {title}")
            
            # Fetch and return the created session
            return self.get_session(session_id)
        
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create chat session: {e}")
            raise
        finally:
            conn.close()
    
    def get_session(self, session_id: str) -> ChatSession:
        """Get chat session by ID
        
        Args:
            session_id: Session ID
        
        Returns:
            ChatSession
        
        Raises:
            ValueError: If session not found
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            row = cursor.execute(
                "SELECT * FROM chat_sessions WHERE session_id = ?",
                (session_id,)
            ).fetchone()
            
            if not row:
                raise ValueError(f"Chat session not found: {session_id}")
            
            return ChatSession.from_db_row(row)
        
        finally:
            conn.close()
    
    def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        task_id: Optional[str] = None
    ) -> List[ChatSession]:
        """List chat sessions
        
        Args:
            limit: Maximum number of sessions to return
            offset: Offset for pagination
            task_id: Filter by task ID
        
        Returns:
            List of ChatSession objects
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            if task_id:
                rows = cursor.execute(
                    """
                    SELECT * FROM chat_sessions
                    WHERE task_id = ?
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (task_id, limit, offset)
                ).fetchall()
            else:
                rows = cursor.execute(
                    """
                    SELECT * FROM chat_sessions
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset)
                ).fetchall()
            
            return [ChatSession.from_db_row(row) for row in rows]
        
        finally:
            conn.close()
    
    def update_session_metadata(
        self,
        session_id: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Update session metadata
        
        Args:
            session_id: Session ID
            metadata: New metadata (merges with existing)
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # Get current metadata
            session = self.get_session(session_id)
            current_metadata = session.metadata
            
            # Merge with new metadata
            current_metadata.update(metadata)
            
            # Update in database
            cursor.execute(
                """
                UPDATE chat_sessions
                SET metadata = ?, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
                """,
                (json.dumps(current_metadata), session_id)
            )
            conn.commit()
            
            logger.info(f"Updated metadata for session: {session_id}")
        
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update session metadata: {e}")
            raise
        finally:
            conn.close()
    
    def update_session_title(
        self,
        session_id: str,
        title: str
    ) -> None:
        """Update session title
        
        Args:
            session_id: Session ID
            title: New title
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                UPDATE chat_sessions
                SET title = ?, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
                """,
                (title, session_id)
            )
            conn.commit()
            
            logger.info(f"Updated title for session {session_id}: {title}")
        
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update session title: {e}")
            raise
        finally:
            conn.close()
    
    def delete_session(self, session_id: str) -> None:
        """Delete chat session (and all its messages via CASCADE)
        
        Args:
            session_id: Session ID
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "DELETE FROM chat_sessions WHERE session_id = ?",
                (session_id,)
            )
            conn.commit()
            
            logger.info(f"Deleted chat session: {session_id}")
        
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete session: {e}")
            raise
        finally:
            conn.close()
    
    # ============================================
    # Message Management
    # ============================================
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessage:
        """Add a message to a chat session
        
        Args:
            session_id: Session ID
            role: Message role (system/user/assistant/tool)
            content: Message content
            metadata: Message metadata (tokens_est, source, citations, etc.)
        
        Returns:
            Created ChatMessage
        """
        message_id = _generate_ulid()
        metadata = metadata or {}
        
        # Auto-estimate tokens if not provided
        if "tokens_est" not in metadata:
            metadata["tokens_est"] = int(len(content) * 1.3)
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                INSERT INTO chat_messages (message_id, session_id, role, content, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (message_id, session_id, role, content, json.dumps(metadata))
            )
            
            # Update session updated_at
            cursor.execute(
                """
                UPDATE chat_sessions
                SET updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
                """,
                (session_id,)
            )
            
            conn.commit()
            
            logger.debug(f"Added {role} message to session {session_id}: {message_id}")
            
            # Fetch and return the created message
            return self.get_message(message_id)
        
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add message: {e}")
            raise
        finally:
            conn.close()
    
    def get_message(self, message_id: str) -> ChatMessage:
        """Get message by ID
        
        Args:
            message_id: Message ID
        
        Returns:
            ChatMessage
        
        Raises:
            ValueError: If message not found
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            row = cursor.execute(
                "SELECT * FROM chat_messages WHERE message_id = ?",
                (message_id,)
            ).fetchone()
            
            if not row:
                raise ValueError(f"Chat message not found: {message_id}")
            
            return ChatMessage.from_db_row(row)
        
        finally:
            conn.close()
    
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[ChatMessage]:
        """Get messages for a chat session
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages (None = all)
            offset: Offset for pagination
        
        Returns:
            List of ChatMessage objects (ordered by created_at ASC)
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            if limit:
                rows = cursor.execute(
                    """
                    SELECT * FROM chat_messages
                    WHERE session_id = ?
                    ORDER BY created_at ASC
                    LIMIT ? OFFSET ?
                    """,
                    (session_id, limit, offset)
                ).fetchall()
            else:
                rows = cursor.execute(
                    """
                    SELECT * FROM chat_messages
                    WHERE session_id = ?
                    ORDER BY created_at ASC
                    """,
                    (session_id,)
                ).fetchall()
            
            return [ChatMessage.from_db_row(row) for row in rows]
        
        finally:
            conn.close()
    
    def get_recent_messages(
        self,
        session_id: str,
        count: int = 10
    ) -> List[ChatMessage]:
        """Get recent messages for a session (for context window)
        
        Args:
            session_id: Session ID
            count: Number of recent messages to get
        
        Returns:
            List of ChatMessage objects (ordered by created_at DESC, then reversed)
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            rows = cursor.execute(
                """
                SELECT * FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, count)
            ).fetchall()
            
            # Reverse to get chronological order
            messages = [ChatMessage.from_db_row(row) for row in rows]
            messages.reverse()
            return messages
        
        finally:
            conn.close()
    
    def count_messages(self, session_id: str) -> int:
        """Count messages in a session
        
        Args:
            session_id: Session ID
        
        Returns:
            Number of messages
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            result = cursor.execute(
                "SELECT COUNT(*) FROM chat_messages WHERE session_id = ?",
                (session_id,)
            ).fetchone()
            
            return result[0]
        
        finally:
            conn.close()
