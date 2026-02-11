from __future__ import annotations

import json
from pathlib import Path

from octopusos.core.chat.session_writer import SessionWriter
from octopusos.core.db import registry_db
from octopusos.core.work.models import RunResult
from octopusos.store.timestamp_utils import now_ms


def _report_path(task_id: str) -> Path:
    out_dir = Path("reports") / "exec_tasks" / task_id
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / "writer_recovery_assist.md"


def run(*, task_id: str, input_obj: dict) -> RunResult:
    session_id = str(input_obj.get("session_id") or "")
    card_id = str(input_obj.get("card_id") or "")
    failed_event_id = str(input_obj.get("failed_event_id") or "")
    ts = now_ms()

    if not session_id:
        return RunResult(ok=False, output_json="{}", evidence_paths=[], error_json=json.dumps({"error": "missing_session_id"}))

    writer = SessionWriter()
    applied_count = writer.recover_pending_for_session(session_id=session_id, limit=1000)

    # Add a lightweight diagnosis of failed ledger events.
    conn = registry_db.get_db()
    failed_rows = conn.execute(
        """
        SELECT event_id, event_type, apply_error_json, created_at_ms
        FROM session_event_ledger
        WHERE session_id = ? AND apply_status = 'failed'
        ORDER BY created_at_ms DESC
        LIMIT 20
        """,
        (session_id,),
    ).fetchall()

    report = _report_path(task_id)
    lines: list[str] = []
    lines.append("# writer_recovery_assist")
    lines.append("")
    lines.append(f"- task_id: `{task_id}`")
    if card_id:
        lines.append(f"- card_id: `{card_id}`")
    lines.append(f"- session_id: `{session_id}`")
    if failed_event_id:
        lines.append(f"- failed_event_id: `{failed_event_id}`")
    lines.append(f"- generated_at_ms: `{ts}`")
    lines.append(f"- recover_pending_applied: `{applied_count}`")
    lines.append("")
    if failed_rows:
        lines.append("Recent failed ledger events:")
        lines.append("")
        for r in failed_rows:
            lines.append(f"- event_id={str(r[0])} type={str(r[1])} at_ms={int(r[3] or 0)}")
            if r[2]:
                lines.append(f"  - error: `{str(r[2])[:400]}`")
        lines.append("")
    else:
        lines.append("No failed ledger events found for this session.")
        lines.append("")

    lines.append("Suggested next steps:")
    lines.append("- Open Inbox for details and apply any recommended recovery steps.")
    lines.append("- If failures persist, keep chat injection in inbox_only and investigate database locks or schema mismatches.")

    report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    output = {
        "session_id": session_id,
        "card_id": card_id or None,
        "failed_event_id": failed_event_id or None,
        "recover_pending_applied": applied_count,
        "report_path": str(report),
    }
    return RunResult(ok=True, output_json=json.dumps(output, ensure_ascii=False), evidence_paths=[str(report)])

