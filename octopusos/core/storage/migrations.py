"""Shared component migration runner.

This module provides a minimal, auditable migration mechanism for component DBs:
- unified `schema_migrations` metadata
- ordered execution of `schema_vNN_*.sql`
- checksum verification and recording
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path
from typing import List, Tuple

from .paths import component_db_path, ensure_db_exists

MIGRATION_FILE_RE = re.compile(r"schema_v(\d+)(?:_[a-z0-9_]+)?\.sql", re.IGNORECASE)


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _version_tag(version: int) -> str:
    return f"v{version:02d}"


def _ensure_schema_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now')),
            checksum TEXT NOT NULL DEFAULT '',
            notes TEXT
        )
        """
    )
    table_info = conn.execute("PRAGMA table_info(schema_migrations)").fetchall()
    cols = {row[1] for row in table_info}
    version_info = next((row for row in table_info if row[1] == "version"), None)
    version_type = str(version_info[2]).upper() if version_info else ""
    version_is_pk = bool(version_info[5]) if version_info else False

    # Legacy table with INTEGER PRIMARY KEY cannot store string tags like v01.
    if version_is_pk and "INT" in version_type:
        old_rows = conn.execute("SELECT * FROM schema_migrations").fetchall()
        old_cols = [row[1] for row in table_info]
        conn.execute("ALTER TABLE schema_migrations RENAME TO schema_migrations_legacy")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now')),
                checksum TEXT NOT NULL DEFAULT '',
                notes TEXT
            )
            """
        )
        for old in old_rows:
            data = dict(zip(old_cols, old))
            raw_version = str(data.get("version", "")).strip()
            if raw_version.isdigit():
                version = _version_tag(int(raw_version))
            elif raw_version.lower().startswith("v"):
                version = raw_version
            else:
                continue
            applied_at = data.get("applied_at") or "datetime('now')"
            checksum = str(data.get("checksum") or "")
            notes = data.get("notes") or data.get("filename")
            conn.execute(
                """
                INSERT OR REPLACE INTO schema_migrations(version, applied_at, checksum, notes)
                VALUES (?, ?, ?, ?)
                """,
                (version, str(applied_at), checksum, notes),
            )
        conn.execute("DROP TABLE IF EXISTS schema_migrations_legacy")
        conn.commit()
        table_info = conn.execute("PRAGMA table_info(schema_migrations)").fetchall()
        cols = {row[1] for row in table_info}

    # Backward-compatible column upgrades.
    if "checksum" not in cols:
        conn.execute("ALTER TABLE schema_migrations ADD COLUMN checksum TEXT NOT NULL DEFAULT ''")
    if "notes" not in cols:
        conn.execute("ALTER TABLE schema_migrations ADD COLUMN notes TEXT")

    # Normalize legacy numeric versions into vNN form for audit tooling.
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    for (raw_version,) in rows:
        if raw_version is None:
            continue
        token = str(raw_version).strip()
        if token.lower().startswith("v"):
            continue
        if token.isdigit():
            normalized = _version_tag(int(token))
            conn.execute(
                "UPDATE schema_migrations SET version = ? WHERE version = ?",
                (normalized, token),
            )
    conn.commit()


def _collect_migrations(migrations_dir: Path) -> List[Tuple[int, Path]]:
    if not migrations_dir.exists():
        return []
    entries: List[Tuple[int, Path]] = []
    for sql_file in sorted(migrations_dir.glob("schema_v*.sql")):
        match = MIGRATION_FILE_RE.match(sql_file.name)
        if not match:
            continue
        entries.append((int(match.group(1)), sql_file))
    entries.sort(key=lambda x: x[0])
    return entries


def _default_migrations_dir(repo_root: Path, component: str) -> Path:
    return repo_root / f"os/{component}/migrations"


def ensure_component_migrations(component: str, repo_root: Path | None = None) -> int:
    """Apply pending component migrations.

    Returns the number of applied migrations.
    """
    target_db = ensure_db_exists(component)
    root = repo_root or Path(__file__).resolve().parents[4]
    migrations_dir = _default_migrations_dir(root, component)

    conn = sqlite3.connect(str(target_db))
    applied_count = 0
    try:
        _ensure_schema_migrations_table(conn)
        applied = {
            str(row[0]).strip()
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
            if row[0] is not None
        }

        for version_num, sql_file in _collect_migrations(migrations_dir):
            version = _version_tag(version_num)
            if version in applied:
                continue

            script = sql_file.read_text(encoding="utf-8")
            checksum = _sha256(script)
            conn.executescript(script)
            conn.execute(
                """
                INSERT OR REPLACE INTO schema_migrations(version, applied_at, checksum, notes)
                VALUES (?, datetime('now'), ?, ?)
                """,
                (version, checksum, sql_file.name),
            )
            conn.commit()
            applied_count += 1

        return applied_count
    finally:
        conn.close()
