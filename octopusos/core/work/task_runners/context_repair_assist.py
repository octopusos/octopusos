from __future__ import annotations

import json
from pathlib import Path

from octopusos.core.db import registry_db
from octopusos.core.work.models import RunResult
from octopusos.store.timestamp_utils import now_ms


def _report_path(task_id: str) -> Path:
    out_dir = Path("reports") / "exec_tasks" / task_id
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / "context_repair_assist.md"


def run(*, task_id: str, input_obj: dict) -> RunResult:
    session_id = str(input_obj.get("session_id") or "")
    card_id = str(input_obj.get("card_id") or "")
    ts = now_ms()

    if not session_id:
        return RunResult(ok=False, output_json="{}", evidence_paths=[], error_json=json.dumps({"error": "missing_session_id"}))

    conn = registry_db.get_db()
    rows = conn.execute(
        """
        SELECT message_id, role, content, created_at_ms, metadata
        FROM chat_messages
        WHERE session_id = ?
        ORDER BY created_at_ms ASC
        LIMIT 500
        """,
        (session_id,),
    ).fetchall()

    findings: list[dict] = []
    artifact_paths: list[str] = []
    for r in rows or []:
        role = str(r[1] or "")
        if role not in {"assistant", "system"}:
            continue
        meta_raw = str(r[4] or "{}")
        try:
            meta = json.loads(meta_raw) if meta_raw else {}
        except Exception:
            meta = {}
        if not isinstance(meta, dict):
            continue
        if meta.get("context_integrity_blocked") is True:
            findings.append(
                {
                    "message_id": str(r[0]),
                    "created_at_ms": int(r[3] or 0),
                    "reason_code": meta.get("context_integrity_reason_code") or meta.get("context_integrity_reason"),
                    "artifact_path": meta.get("context_integrity_artifact_path"),
                }
            )
            if meta.get("context_integrity_artifact_path"):
                artifact_paths.append(str(meta.get("context_integrity_artifact_path")))

    report = _report_path(task_id)
    lines: list[str] = []
    lines.append("# context_repair_assist")
    lines.append("")
    lines.append(f"- task_id: `{task_id}`")
    if card_id:
        lines.append(f"- card_id: `{card_id}`")
    lines.append(f"- session_id: `{session_id}`")
    lines.append(f"- generated_at_ms: `{ts}`")
    lines.append("")
    if not findings:
        lines.append("No `context_integrity_blocked` markers were found in recent assistant/system messages.")
        lines.append("")
        lines.append("Suggested next steps:")
        lines.append("- Open Inbox for the originating card and review the attached evidence/context.")
        lines.append("- Re-run the action once you have a complete context pack (e.g. include missing files/evidence refs).")
    else:
        lines.append("Detected context integrity blocks:")
        lines.append("")
        for f in findings[:50]:
            lines.append(f"- message_id={f.get('message_id')} reason={f.get('reason_code')}")
            if f.get("artifact_path"):
                lines.append(f"  - artifact_path: `{f.get('artifact_path')}`")
        lines.append("")
        lines.append("Suggested next steps:")
        lines.append("- Open Inbox to review evidence and fix missing/invalid context inputs.")
        lines.append("- If an artifact_path exists, inspect the generated evidence JSON to understand what was dropped.")

    report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    output = {
        "session_id": session_id,
        "card_id": card_id or None,
        "finding_count": len(findings),
        "artifact_paths": artifact_paths[:50],
        "report_path": str(report),
    }
    return RunResult(ok=True, output_json=json.dumps(output, ensure_ascii=False), evidence_paths=[str(report)])
