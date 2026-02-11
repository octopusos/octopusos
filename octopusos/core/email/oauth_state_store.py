from __future__ import annotations

import json
import secrets
import sqlite3
from dataclasses import dataclass

from octopusos.core.db import registry_db
from octopusos.core.db.writer import SQLiteWriter
from octopusos.store.timestamp_utils import now_ms


@dataclass(frozen=True)
class OAuthState:
    state: str
    instance_id: str
    provider_type: str
    code_verifier: str
    redirect_uri: str
    scopes: str
    created_at_ms: int
    expires_at_ms: int
    meta_json: str


def _row_to_state(row) -> OAuthState:
    return OAuthState(
        state=str(row[0]),
        instance_id=str(row[1]),
        provider_type=str(row[2]),
        code_verifier=str(row[3]),
        redirect_uri=str(row[4]),
        scopes=str(row[5]),
        created_at_ms=int(row[6]),
        expires_at_ms=int(row[7]),
        meta_json=str(row[8] or "{}"),
    )


class EmailOAuthStateStore:
    def __init__(self) -> None:
        self._writer = SQLiteWriter(db_path=registry_db.get_db_path())

    def create(
        self,
        *,
        instance_id: str,
        provider_type: str,
        code_verifier: str,
        redirect_uri: str,
        scopes: str,
        ttl_ms: int = 10 * 60_000,
        meta_obj: dict | None = None,
    ) -> OAuthState:
        st = secrets.token_urlsafe(24)
        ts = int(now_ms())
        exp = int(ts + max(60_000, int(ttl_ms)))
        meta_json = json.dumps(meta_obj or {}, ensure_ascii=False)

        def _op(conn: sqlite3.Connection) -> OAuthState:
            conn.execute(
                """
                INSERT INTO email_oauth_states (
                  state, instance_id, provider_type, code_verifier, redirect_uri,
                  scopes, created_at_ms, expires_at_ms, meta_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(st),
                    str(instance_id),
                    str(provider_type),
                    str(code_verifier),
                    str(redirect_uri),
                    str(scopes),
                    int(ts),
                    int(exp),
                    meta_json,
                ),
            )
            row = conn.execute(
                """
                SELECT state, instance_id, provider_type, code_verifier, redirect_uri,
                       scopes, created_at_ms, expires_at_ms, meta_json
                FROM email_oauth_states
                WHERE state = ?
                """,
                (str(st),),
            ).fetchone()
            return _row_to_state(row)

        return self._writer.submit(_op, timeout=10.0)

    def consume(self, *, state: str) -> OAuthState | None:
        """One-time read: returns state and deletes the row."""
        nowv = int(now_ms())

        def _op(conn: sqlite3.Connection) -> OAuthState | None:
            row = conn.execute(
                """
                SELECT state, instance_id, provider_type, code_verifier, redirect_uri,
                       scopes, created_at_ms, expires_at_ms, meta_json
                FROM email_oauth_states
                WHERE state = ?
                """,
                (str(state),),
            ).fetchone()
            if not row:
                return None
            st = _row_to_state(row)
            conn.execute("DELETE FROM email_oauth_states WHERE state = ?", (str(state),))
            if st.expires_at_ms <= nowv:
                return None
            return st

        return self._writer.submit(_op, timeout=10.0)

    def cleanup_expired(self, *, now_ms_value: int | None = None) -> int:
        nowv = int(now_ms_value or now_ms())

        def _op(conn: sqlite3.Connection) -> int:
            cur = conn.execute("DELETE FROM email_oauth_states WHERE expires_at_ms <= ?", (int(nowv),))
            return int(cur.rowcount or 0)

        return int(self._writer.submit(_op, timeout=10.0) or 0)

