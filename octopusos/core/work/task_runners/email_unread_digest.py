from __future__ import annotations

import json

from octopusos.core.attention.state_card_store import StateCardStore
from octopusos.core.email.digest import run_unread_digest, since_start_of_day_ms
from octopusos.core.email.instance_store import EmailInstanceStore
from octopusos.core.work.models import RunResult
from octopusos.store.timestamp_utils import now_ms


def run(*, task_id: str, input_obj: dict) -> RunResult:
    instance_id = str(input_obj.get("instance_id") or "")
    instance_name = str(input_obj.get("instance_name") or instance_id)
    tz_name = str(input_obj.get("schedule_tz") or "Australia/Sydney")

    if not instance_id:
        return RunResult(ok=False, output_json="{}", evidence_paths=[], error_json=json.dumps({"error": "missing_instance_id"}))

    since_ms = since_start_of_day_ms(tz_name=tz_name, now_ms_value=now_ms())
    result = run_unread_digest(
        task_id=task_id,
        instance_id=instance_id,
        instance_name=instance_name,
        since_ms=since_ms,
        limit=50,
        tz_name=tz_name,
    )

    # Update card summary to reflect counts (best-effort).
    card_id = str(input_obj.get("card_id") or "")
    if card_id:
        try:
            cards = StateCardStore()
            # There's no "update by id" API; use resolution update would be wrong here.
            # We keep the card open but refresh summary via a direct UPDATE.
            from octopusos.core.db import registry_db

            conn = registry_db.get_db()
            conn.execute(
                """
                UPDATE state_cards
                SET title = COALESCE(title, title),
                    summary = ?,
                    last_seen_ms = CASE
                      WHEN last_seen_ms IS NULL OR ? > last_seen_ms THEN ?
                      ELSE last_seen_ms
                    END
                WHERE card_id = ?
                """,
                (
                    f"{result.total_unread} unread (important {len(result.important)}) for {instance_name}",
                    int(now_ms()),
                    int(now_ms()),
                    card_id,
                ),
            )
            conn.commit()
        except Exception:
            pass

    out = {
        "instance_id": instance_id,
        "instance_name": instance_name,
        "total_unread": result.total_unread,
        "important": len(result.important),
        "normal": len(result.normal),
        "filtered": len(result.filtered),
        "report_path": result.report_path,
        "digest_md": result.digest_md,
    }
    return RunResult(ok=True, output_json=json.dumps(out, ensure_ascii=False), evidence_paths=[result.report_path])

