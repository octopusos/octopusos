from __future__ import annotations

import io
import json
import os
import zipfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable

from octopusos.core.db import registry_db
from octopusos.store.timestamp_utils import now_ms


ALLOWED_EVIDENCE_DIRS: tuple[str, ...] = ("reports", "output", "logs")


@dataclass(frozen=True)
class TransparencyBundle:
    filename: str
    content_type: str
    data: bytes


def _safe_json_loads(raw: str) -> Any:
    try:
        return json.loads(raw or "")
    except Exception:
        return None


def _iter_evidence_paths(*, work_rows: Iterable[dict], task_rows: Iterable[dict]) -> list[str]:
    paths: list[str] = []
    for r in work_rows:
        raw = r.get("evidence_ref_json")
        data = _safe_json_loads(str(raw or "[]"))
        if isinstance(data, list):
            for p in data:
                if isinstance(p, str) and p.strip():
                    paths.append(p.strip())
    for r in task_rows:
        raw = r.get("evidence_paths_json")
        data = _safe_json_loads(str(raw or "[]"))
        if isinstance(data, list):
            for p in data:
                if isinstance(p, str) and p.strip():
                    paths.append(p.strip())
    # Stable ordering + de-dupe.
    seen: set[str] = set()
    out: list[str] = []
    for p in paths:
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
    return out


def _is_allowed_evidence_path(path: Path) -> bool:
    # Only allow including files under a few well-known output dirs.
    parts = path.parts
    if not parts:
        return False
    return parts[0] in ALLOWED_EVIDENCE_DIRS


def _resolve_evidence_path(raw: str, *, base_dir: Path) -> Path | None:
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None

    p = Path(s)
    # Treat absolute paths as-is, but still require they are under base_dir.
    resolved = (p if p.is_absolute() else (base_dir / p)).resolve()
    try:
        base_resolved = base_dir.resolve()
        resolved.relative_to(base_resolved)
    except Exception:
        return None

    rel = resolved.relative_to(base_dir.resolve())
    if not _is_allowed_evidence_path(rel):
        return None
    return resolved


def build_transparency_bundle(*, limit: int = 50) -> TransparencyBundle:
    limit = int(max(1, min(limit, 500)))
    ts = now_ms()

    conn = registry_db.get_db()
    conn.row_factory = getattr(conn, "row_factory", None)  # appease type checkers

    # Cards
    cards = conn.execute(
        """
        SELECT
          card_id, scope_type, scope_id, card_type, severity, status,
          title, summary, first_seen_ms, last_seen_ms, last_event_id, merge_key,
          cooldown_until_ms, metadata_json,
          resolution_status, resolution_reason, resolved_at_ms, resolved_by, resolution_note, linked_task_id
        FROM state_cards
        ORDER BY last_seen_ms DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    card_rows: list[dict] = []
    for r in cards or []:
        card_rows.append(
            {
                "card_id": r[0],
                "scope_type": r[1],
                "scope_id": r[2],
                "card_type": r[3],
                "severity": r[4],
                "status": r[5],
                "title": r[6],
                "summary": r[7],
                "first_seen_ms": r[8],
                "last_seen_ms": r[9],
                "last_event_id": r[10],
                "merge_key": r[11],
                "cooldown_until_ms": r[12],
                "metadata_json": r[13],
                "resolution_status": r[14],
                "resolution_reason": r[15],
                "resolved_at_ms": r[16],
                "resolved_by": r[17],
                "resolution_note": r[18],
                "linked_task_id": r[19],
            }
        )

    # Work list
    works = conn.execute(
        """
        SELECT
          work_id, type, title, status, priority,
          scope_type, scope_id, source_card_id,
          created_at_ms, updated_at_ms, started_at_ms, finished_at_ms,
          summary, detail_json, evidence_ref_json
        FROM work_list_items
        ORDER BY updated_at_ms DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    work_rows: list[dict] = []
    for r in works or []:
        work_rows.append(
            {
                "work_id": r[0],
                "type": r[1],
                "title": r[2],
                "status": r[3],
                "priority": r[4],
                "scope_type": r[5],
                "scope_id": r[6],
                "source_card_id": r[7],
                "created_at_ms": r[8],
                "updated_at_ms": r[9],
                "started_at_ms": r[10],
                "finished_at_ms": r[11],
                "summary": r[12],
                "detail_json": r[13],
                "evidence_ref_json": r[14],
            }
        )

    # Exec tasks
    tasks = conn.execute(
        """
        SELECT
          task_id, work_id, card_id, task_type, status, risk_level, requires_confirmation,
          created_at_ms, updated_at_ms, started_at_ms, finished_at_ms,
          input_json, output_json, error_json, evidence_paths_json, idempotency_key
        FROM exec_tasks
        ORDER BY updated_at_ms DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    task_rows: list[dict] = []
    for r in tasks or []:
        task_rows.append(
            {
                "task_id": r[0],
                "work_id": r[1],
                "card_id": r[2],
                "task_type": r[3],
                "status": r[4],
                "risk_level": r[5],
                "requires_confirmation": bool(int(r[6] or 0)),
                "created_at_ms": r[7],
                "updated_at_ms": r[8],
                "started_at_ms": r[9],
                "finished_at_ms": r[10],
                "input_json": r[11],
                "output_json": r[12],
                "error_json": r[13],
                "evidence_paths_json": r[14],
                "idempotency_key": r[15],
            }
        )

    # Injection ledger events (recent)
    inj_events = conn.execute(
        """
        SELECT
          event_id, session_id, event_type, source, idempotency_key, causation_id, correlation_id,
          payload_json, created_at_ms, apply_status
        FROM session_event_ledger
        WHERE event_type LIKE 'chat_injection_%'
        ORDER BY created_at_ms DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    ledger_rows: list[dict] = []
    for r in inj_events or []:
        ledger_rows.append(
            {
                "event_id": r[0],
                "session_id": r[1],
                "event_type": r[2],
                "source": r[3],
                "idempotency_key": r[4],
                "causation_id": r[5],
                "correlation_id": r[6],
                "payload_json": r[7],
                "created_at_ms": r[8],
                "apply_status": r[9],
            }
        )

    base_dir = Path(os.getcwd()).resolve()
    evidence_paths = _iter_evidence_paths(work_rows=work_rows, task_rows=task_rows)

    evidence_index: list[dict[str, Any]] = []
    missing: list[str] = []

    buf = io.BytesIO()
    filename = f"transparency-bundle-{ts}.zip"
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Add evidence files (best-effort).
        for raw in evidence_paths:
            resolved = _resolve_evidence_path(raw, base_dir=base_dir)
            if not resolved or not resolved.exists() or not resolved.is_file():
                missing.append(raw)
                evidence_index.append({"path": raw, "included": False})
                continue
            rel = resolved.relative_to(base_dir)
            zip_path = str(Path("evidence") / rel)
            content = resolved.read_bytes()
            zf.writestr(zip_path, content)
            evidence_index.append(
                {
                    "path": raw,
                    "included": True,
                    "zip_path": zip_path,
                    "size_bytes": len(content),
                    "sha256": sha256(content).hexdigest(),
                }
            )

        manifest = {
            "generated_at_ms": ts,
            "limit": limit,
            "cards": card_rows,
            "work_items": work_rows,
            "exec_tasks": task_rows,
            "chat_injection_ledger_events": ledger_rows,
            "evidence_files": evidence_index,
            "missing_evidence_paths": missing,
            "allowed_evidence_dirs": list(ALLOWED_EVIDENCE_DIRS),
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))

    return TransparencyBundle(filename=filename, content_type="application/zip", data=buf.getvalue())

