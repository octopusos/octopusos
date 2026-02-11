from __future__ import annotations

import secrets
import sqlite3
from dataclasses import dataclass
from typing import Optional

from octopusos.core.db import registry_db
from octopusos.core.db.writer import SQLiteWriter
from octopusos.store.timestamp_utils import now_ms
from octopusos.util.ulid import ulid


@dataclass(frozen=True)
class DraftRow:
    draft_id: str
    instance_id: str
    message_id: str
    subject: str
    body_md: str
    confirm_token: str
    status: str
    created_at_ms: int
    expires_at_ms: int
    sent_at_ms: int | None


def _row_to_draft(row) -> DraftRow:
    return DraftRow(
        draft_id=str(row[0]),
        instance_id=str(row[1]),
        message_id=str(row[2]),
        subject=str(row[3]),
        body_md=str(row[4]),
        confirm_token=str(row[5]),
        status=str(row[6]),
        created_at_ms=int(row[7]),
        expires_at_ms=int(row[8]),
        sent_at_ms=int(row[9]) if row[9] is not None else None,
    )


class EmailDraftStore:
    def __init__(self) -> None:
        self._writer = SQLiteWriter(db_path=registry_db.get_db_path())

    def create(self, *, instance_id: str, message_id: str, subject: str, body_md: str, ttl_ms: int = 10 * 60_000) -> DraftRow:
        did = ulid()
        ts = now_ms()
        expires = int(ts + max(60_000, int(ttl_ms)))
        token = secrets.token_urlsafe(24)

        def _op(conn: sqlite3.Connection) -> DraftRow:
            conn.execute(
                """
                INSERT INTO email_drafts (
                  draft_id, instance_id, message_id, subject, body_md, confirm_token,
                  status, created_at_ms, expires_at_ms, sent_at_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, ?, NULL)
                """,
                (
                    str(did),
                    str(instance_id),
                    str(message_id),
                    str(subject),
                    str(body_md),
                    str(token),
                    int(ts),
                    int(expires),
                ),
            )
            row = conn.execute(
                """
                SELECT draft_id, instance_id, message_id, subject, body_md, confirm_token,
                       status, created_at_ms, expires_at_ms, sent_at_ms
                FROM email_drafts
                WHERE draft_id = ?
                """,
                (str(did),),
            ).fetchone()
            return _row_to_draft(row)

        return self._writer.submit(_op, timeout=10.0)

    def get(self, *, draft_id: str) -> Optional[DraftRow]:
        def _op(conn: sqlite3.Connection) -> Optional[DraftRow]:
            row = conn.execute(
                """
                SELECT draft_id, instance_id, message_id, subject, body_md, confirm_token,
                       status, created_at_ms, expires_at_ms, sent_at_ms
                FROM email_drafts
                WHERE draft_id = ?
                """,
                (str(draft_id),),
            ).fetchone()
            return _row_to_draft(row) if row else None

        return self._writer.submit(_op, timeout=10.0)

    def mark_sent(self, *, draft_id: str) -> None:
        ts = now_ms()

        def _op(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                UPDATE email_drafts
                SET status='sent', sent_at_ms=?, expires_at_ms=expires_at_ms
                WHERE draft_id = ? AND status = 'draft'
                """,
                (int(ts), str(draft_id)),
            )

        self._writer.submit(_op, timeout=10.0)

