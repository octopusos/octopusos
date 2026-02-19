"""Session storage for CommunicationOS.

This module provides persistent storage for session management, tracking
the mapping between channels/users/conversations and OctopusOS sessions.

Design Principles:
- Separation of concerns: Session routing vs session storage
- Audit trail: All session operations are logged
- Flexibility: Support both scope modes (USER and USER_CONVERSATION)
- Thread-safe: SQLite with WAL mode for concurrent access
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import tempfile
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone

from octopusos.core.storage.paths import component_db_path
from octopusos.core.time import utc_now
from octopusos.communicationos.manifest import SessionScope

logger = logging.getLogger(__name__)


class SessionStatus(str):
    """Session status values."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    CLOSED = "closed"


@dataclass
class SessionRecord:
    """Lightweight session record for command responses."""
    session_id: str
    channel_id: str
    user_key: str
    conversation_key: str
    scope: str
    created_at: datetime
    updated_at: datetime
    status: str = SessionStatus.ACTIVE
    title: Optional[str] = None
    message_count: int = 0
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "channel_id": self.channel_id,
            "user_key": self.user_key,
            "conversation_key": self.conversation_key,
            "scope": self.scope,
            "title": self.title,
            "status": self.status,
            "message_count": self.message_count,
            "metadata": self.metadata,
            "created_at": int(self.created_at.timestamp() * 1000),
            "updated_at": int(self.updated_at.timestamp() * 1000),
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)

    def keys(self) -> List[str]:
        return list(self.to_dict().keys())

    def items(self):
        return self.to_dict().items()


class SessionStore:
    """SQLite-based storage for session management.

    The SessionStore manages the mapping between communication channels
    and OctopusOS sessions. It tracks:
    - Which session is currently active for a given user/conversation
    - Session metadata (title, creation time, message count)
    - Session history and switching

    Database schema:
    - channel_sessions: Tracks active session for each channel/user/conversation
    - sessions: Stores session metadata and history

    Example:
        >>> store = SessionStore()
        >>> session_id = store.create_session(
        ...     channel_id="whatsapp_business",
        ...     user_key="+1234567890",
        ...     conversation_key="+1234567890",
        ...     scope=SessionScope.USER,
        ...     title="Customer Support"
        ... )
        >>> active = store.get_active_session(
        ...     channel_id="whatsapp_business",
        ...     user_key="+1234567890"
        ... )
        >>> print(active['session_id'])
        abc123...
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the session store.

        Args:
            db_path: Path to SQLite database. If None, uses default location.
        """
        if db_path is None and os.getenv("PYTEST_CURRENT_TEST"):
            fd, path = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            self.db_path = path
        else:
            self.db_path = db_path or str(component_db_path("communicationos"))
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")

            # Channel sessions tracking table
            # This tracks the currently active session for each channel/user/conversation
            conn.execute("""
                CREATE TABLE IF NOT EXISTS channel_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    user_key TEXT NOT NULL,
                    conversation_key TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    active_session_id TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    UNIQUE(channel_id, user_key, conversation_key)
                )
            """)

            # Sessions metadata table
            # This stores information about each session
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    user_key TEXT NOT NULL,
                    conversation_key TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    title TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    message_count INTEGER NOT NULL DEFAULT 0,
                    metadata TEXT,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)

            # Session history table
            # Tracks when sessions are created, switched, archived
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            # Create indexes for efficient lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_channel_sessions_lookup
                ON channel_sessions(channel_id, user_key, conversation_key)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_channel_user
                ON sessions(channel_id, user_key, status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_history_session_id
                ON session_history(session_id)
            """)

            conn.commit()

    def create_session(
        self,
        channel_id: str,
        user_key: str,
        conversation_key: Optional[str] = None,
        scope: Optional[SessionScope] = None,
        title: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Create a new session and set it as active.

        Args:
            channel_id: Channel identifier
            user_key: User identifier
            conversation_key: Conversation identifier
            scope: Session scope
            title: Optional session title
            session_id: Optional session ID (if None, generates one)
            metadata: Optional metadata dictionary

        Returns:
            Session ID
        """
        import uuid

        legacy_mode = conversation_key is None and scope is None
        if conversation_key is None:
            conversation_key = user_key
        if scope is None:
            scope = SessionScope.USER

        now_dt = utc_now()
        now = int(now_dt.timestamp() * 1000)

        if session_id is None:
            if legacy_mode:
                session_id = f"S-{now_dt.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4]}"
            else:
                session_id = f"cs_{uuid.uuid4().hex[:16]}"
        metadata_json = json.dumps(metadata) if metadata else None

        with sqlite3.connect(self.db_path) as conn:
            if legacy_mode and session_id is not None:
                while True:
                    exists = conn.execute(
                        "SELECT 1 FROM sessions WHERE session_id = ?",
                        (session_id,)
                    ).fetchone()
                    if not exists:
                        break
                    session_id = f"S-{now_dt.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4]}"
            # Create session record
            conn.execute("""
                INSERT INTO sessions
                (session_id, channel_id, user_key, conversation_key, scope,
                 title, status, message_count, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            """, (
                session_id, channel_id, user_key, conversation_key,
                scope.value, title, SessionStatus.ACTIVE,
                metadata_json, now, now
            ))

            # Set as active session
            self._set_active_session_internal(
                conn, channel_id, user_key, conversation_key,
                scope, session_id, now
            )

            # Log to history
            self._log_history(conn, session_id, "created", "Session created", now)

            conn.commit()

        logger.info(
            f"Created session {session_id} for {channel_id}:{user_key} "
            f"(scope={scope.value})"
        )
        if legacy_mode:
            return SessionRecord(
                session_id=session_id,
                channel_id=channel_id,
                user_key=user_key,
                conversation_key=conversation_key,
                scope=scope.value,
                created_at=now_dt,
                updated_at=now_dt,
                status=SessionStatus.ACTIVE,
                title=title,
                message_count=0,
                metadata=metadata
            )
        return session_id

    def get_active_session(
        self,
        channel_id: str,
        user_key: str,
        conversation_key: Optional[str] = None
    ) -> Optional[SessionRecord]:
        """Get the active session for a channel/user/conversation.

        Args:
            channel_id: Channel identifier
            user_key: User identifier
            conversation_key: Optional conversation identifier

        Returns:
            Session dictionary or None if no active session
        """
        if conversation_key is None:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT active_session_id
                    FROM channel_sessions
                    WHERE channel_id = ? AND user_key = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (channel_id, user_key))
                row = cursor.fetchone()
                if row:
                    session_id = row[0]
                    data = self._get_session_by_id(conn, session_id)
                    return self._to_record(data) if data else None

            # If conversation_key not provided, use user_key as default
            # (for USER scope channels)
            conversation_key = user_key

        if conversation_key:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT active_session_id
                    FROM channel_sessions
                    WHERE channel_id = ? AND user_key = ? AND conversation_key = ?
                """, (channel_id, user_key, conversation_key))
                row = cursor.fetchone()
                if row:
                    session_id = row[0]
                    data = self._get_session_by_id(conn, session_id)
                    return self._to_record(data) if data else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT active_session_id
                FROM channel_sessions
                WHERE channel_id = ? AND user_key = ? AND conversation_key = ?
            """, (channel_id, user_key, conversation_key))

            row = cursor.fetchone()
            if not row:
                return None

            session_id = row[0]
            data = self._get_session_by_id(conn, session_id)
            return self._to_record(data) if data else None

    def switch_session(
        self,
        channel_id: str,
        user_key: str,
        conversation_key: str,
        new_session_id: str
    ) -> None:
        """Switch to a different session.

        Args:
            channel_id: Channel identifier
            user_key: User identifier
            conversation_key: Conversation identifier
            new_session_id: Session ID to switch to

        Raises:
            ValueError: If new session doesn't exist
        """
        now = int(utc_now().timestamp() * 1000)

        with sqlite3.connect(self.db_path) as conn:
            # Verify new session exists
            cursor = conn.execute(
                "SELECT scope FROM sessions WHERE session_id = ?",
                (new_session_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Session not found: {new_session_id}")

            scope_str = row[0]
            scope = SessionScope(scope_str)

            # Get current active session (if any) to log the switch
            cursor = conn.execute("""
                SELECT active_session_id
                FROM channel_sessions
                WHERE channel_id = ? AND user_key = ? AND conversation_key = ?
            """, (channel_id, user_key, conversation_key))
            old_row = cursor.fetchone()
            old_session_id = old_row[0] if old_row else None

            # Update active session
            self._set_active_session_internal(
                conn, channel_id, user_key, conversation_key,
                scope, new_session_id, now
            )

            # Log to history
            details = f"Switched from {old_session_id}" if old_session_id else "Set as active"
            self._log_history(conn, new_session_id, "activated", details, now)

            if old_session_id and old_session_id != new_session_id:
                self._log_history(
                    conn, old_session_id, "deactivated",
                    f"Switched to {new_session_id}", now
                )

            conn.commit()

        logger.info(
            f"Switched session for {channel_id}:{user_key} "
            f"from {old_session_id} to {new_session_id}"
        )

    def list_sessions(
        self,
        channel_id: str,
        user_key: str,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[SessionRecord]:
        """List sessions for a user on a channel.

        Args:
            channel_id: Channel identifier
            user_key: User identifier
            status: Optional status filter (active, inactive, archived)
            limit: Maximum number of sessions to return

        Returns:
            List of session dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            if status:
                cursor = conn.execute("""
                    SELECT session_id, channel_id, user_key, conversation_key,
                           scope, title, status, message_count, metadata,
                           created_at, updated_at
                    FROM sessions
                    WHERE channel_id = ? AND user_key = ? AND status = ?
                    ORDER BY updated_at DESC, rowid DESC
                    LIMIT ?
                """, (channel_id, user_key, status, limit))
            else:
                cursor = conn.execute("""
                    SELECT session_id, channel_id, user_key, conversation_key,
                           scope, title, status, message_count, metadata,
                           created_at, updated_at
                    FROM sessions
                    WHERE channel_id = ? AND user_key = ?
                    ORDER BY updated_at DESC, rowid DESC
                    LIMIT ?
                """, (channel_id, user_key, limit))

            sessions = []
            for row in cursor.fetchall():
                metadata = json.loads(row[8]) if row[8] else None
                sessions.append({
                    "session_id": row[0],
                    "channel_id": row[1],
                    "user_key": row[2],
                    "conversation_key": row[3],
                    "scope": row[4],
                    "title": row[5],
                    "status": row[6],
                    "message_count": row[7],
                    "metadata": metadata,
                    "created_at": row[9],
                    "updated_at": row[10],
                })

            return [self._to_record(s) for s in sessions]

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        """Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session dictionary or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            data = self._get_session_by_id(conn, session_id)
            if not data:
                return None
            return self._to_record(data)

    def get_active_session_id(
        self,
        channel_id: str,
        user_key: str,
        conversation_key: Optional[str] = None
    ) -> Optional[str]:
        """Get active session ID for a channel/user/conversation."""
        candidates = []
        if conversation_key is not None:
            candidates.append(conversation_key)
        else:
            candidates.append(None)
            candidates.append(user_key)
            candidates.append(f"{channel_id}:{user_key}")

        for key in candidates:
            active = self.get_active_session(channel_id, user_key, key)
            if active:
                if isinstance(active, dict):
                    return active["session_id"]
                return getattr(active, "session_id", None)
        return None

    def set_active_session(
        self,
        channel_id: str,
        user_key: str,
        session_id: str,
        conversation_key: Optional[str] = None
    ) -> bool:
        """Set active session for a channel/user/conversation."""
        if conversation_key is None:
            conversation_key = user_key
        try:
            self.switch_session(channel_id, user_key, conversation_key, session_id)
        except ValueError:
            return False
        return True

    def close_session(self, session_id: str) -> bool:
        """Close a session and clear active pointer if needed."""
        now = int(utc_now().timestamp() * 1000)
        with sqlite3.connect(self.db_path) as conn:
            session = self._get_session_by_id(conn, session_id)
            if not session:
                return False

            conn.execute(
                "UPDATE sessions SET status = ?, updated_at = ? WHERE session_id = ?",
                (SessionStatus.CLOSED, now, session_id)
            )

            conn.execute(
                "DELETE FROM channel_sessions WHERE active_session_id = ?",
                (session_id,)
            )

            self._log_history(conn, session_id, "closed", "Session closed", now)
            conn.commit()

        return True

    def update_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update session metadata.

        Args:
            session_id: Session identifier
            title: Optional new title
            status: Optional new status
            metadata: Optional metadata to merge (set key to None to delete)
        """
        now = int(utc_now().timestamp() * 1000)

        with sqlite3.connect(self.db_path) as conn:
            # Build update query dynamically
            updates = ["updated_at = ?"]
            params = [now]

            if title is not None:
                updates.append("title = ?")
                params.append(title)

            if status is not None:
                updates.append("status = ?")
                params.append(status)

            if metadata is not None:
                # Get current metadata
                cursor = conn.execute(
                    "SELECT metadata FROM sessions WHERE session_id = ?",
                    (session_id,)
                )
                row = cursor.fetchone()
                if row:
                    current_metadata = json.loads(row[0]) if row[0] else {}
                    # Merge metadata
                    for key, value in metadata.items():
                        if value is None:
                            current_metadata.pop(key, None)
                        else:
                            current_metadata[key] = value

                    updates.append("metadata = ?")
                    params.append(json.dumps(current_metadata))

            params.append(session_id)
            query = f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = ?"

            conn.execute(query, params)

            # Log to history
            changes = []
            if title is not None:
                changes.append(f"title='{title}'")
            if status is not None:
                changes.append(f"status='{status}'")
            if metadata is not None:
                changes.append("metadata updated")

            details = "Updated: " + ", ".join(changes) if changes else "Updated"
            self._log_history(conn, session_id, "updated", details, now)

            conn.commit()

    def increment_message_count(self, session_id: str) -> None:
        """Increment the message count for a session.

        Args:
            session_id: Session identifier
        """
        now = int(utc_now().timestamp() * 1000)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sessions
                SET message_count = message_count + 1, updated_at = ?
                WHERE session_id = ?
            """, (now, session_id))
            conn.commit()

    def archive_session(self, session_id: str) -> None:
        """Archive a session (soft delete).

        Args:
            session_id: Session identifier
        """
        now = int(utc_now().timestamp() * 1000)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sessions
                SET status = ?, updated_at = ?
                WHERE session_id = ?
            """, (SessionStatus.ARCHIVED, now, session_id))

            self._log_history(conn, session_id, "archived", "Session archived", now)
            conn.commit()

        logger.info(f"Archived session {session_id}")

    def get_session_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get history for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of history entries to return

        Returns:
            List of history entry dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT action, details, created_at
                FROM session_history
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (session_id, limit))

            history = []
            for row in cursor.fetchall():
                history.append({
                    "action": row[0],
                    "details": row[1],
                    "created_at": row[2],
                })

            return history

    def _set_active_session_internal(
        self,
        conn: sqlite3.Connection,
        channel_id: str,
        user_key: str,
        conversation_key: str,
        scope: SessionScope,
        session_id: str,
        now: int
    ) -> None:
        """Internal method to set active session (within transaction).

        Args:
            conn: Database connection
            channel_id: Channel identifier
            user_key: User identifier
            conversation_key: Conversation identifier
            scope: Session scope
            session_id: Session ID to set as active
            now: Current timestamp (epoch milliseconds)
        """
        # Check if entry exists
        cursor = conn.execute("""
            SELECT id FROM channel_sessions
            WHERE channel_id = ? AND user_key = ? AND conversation_key = ?
        """, (channel_id, user_key, conversation_key))

        if cursor.fetchone():
            # Update existing
            conn.execute("""
                UPDATE channel_sessions
                SET active_session_id = ?, updated_at = ?
                WHERE channel_id = ? AND user_key = ? AND conversation_key = ?
            """, (session_id, now, channel_id, user_key, conversation_key))
        else:
            # Insert new
            conn.execute("""
                INSERT INTO channel_sessions
                (channel_id, user_key, conversation_key, scope,
                 active_session_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                channel_id, user_key, conversation_key,
                scope.value, session_id, now, now
            ))

    def _get_session_by_id(
        self,
        conn: sqlite3.Connection,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Internal method to get session by ID.

        Args:
            conn: Database connection
            session_id: Session identifier

        Returns:
            Session dictionary or None if not found
        """
        cursor = conn.execute("""
            SELECT session_id, channel_id, user_key, conversation_key,
                   scope, title, status, message_count, metadata,
                   created_at, updated_at
            FROM sessions
            WHERE session_id = ?
        """, (session_id,))

        row = cursor.fetchone()
        if not row:
            return None

        metadata = json.loads(row[8]) if row[8] else None

        return {
            "session_id": row[0],
            "channel_id": row[1],
            "user_key": row[2],
            "conversation_key": row[3],
            "scope": row[4],
            "title": row[5],
            "status": row[6],
            "message_count": row[7],
            "metadata": metadata,
            "created_at": row[9],
            "updated_at": row[10],
        }

    def _log_history(
        self,
        conn: sqlite3.Connection,
        session_id: str,
        action: str,
        details: Optional[str],
        now: int
    ) -> None:
        """Internal method to log session history.

        Args:
            conn: Database connection
            session_id: Session identifier
            action: Action performed
            details: Optional details
            now: Current timestamp (epoch milliseconds)
        """
        conn.execute("""
            INSERT INTO session_history
            (session_id, action, details, created_at)
            VALUES (?, ?, ?, ?)
        """, (session_id, action, details, now))

    @staticmethod
    def _to_record(session: Dict[str, Any]) -> SessionRecord:
        created_at = datetime.fromtimestamp(session["created_at"] / 1000, tz=timezone.utc)
        updated_at = datetime.fromtimestamp(session["updated_at"] / 1000, tz=timezone.utc)
        return SessionRecord(
            session_id=session["session_id"],
            channel_id=session["channel_id"],
            user_key=session["user_key"],
            conversation_key=session.get("conversation_key") or session["user_key"],
            scope=session.get("scope") or SessionScope.USER.value,
            created_at=created_at,
            updated_at=updated_at,
            status=session.get("status", SessionStatus.ACTIVE),
            title=session.get("title"),
            message_count=session.get("message_count", 0),
            metadata=session.get("metadata")
        )
