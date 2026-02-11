from __future__ import annotations

import datetime as dt
import json
from zoneinfo import ZoneInfo

from octopusos.core.attention.inbox_service import InboxService
from octopusos.core.attention.state_card_store import StateCardStore
from octopusos.core.attention.chat_injector import ChatInjector
from octopusos.core.db import registry_db
from octopusos.core.email.instance_store import EmailInstanceStore
from octopusos.core.email.schedule_store import EmailDigestRunStore
from octopusos.core.work.exec_task_store import ExecTaskStore
from octopusos.core.work.work_store import WorkStore
from octopusos.core.work.work_mode import auto_execute_enabled, get_work_mode_global
from octopusos.store.timestamp_utils import now_ms
from octopusos.util.ulid import ulid


SCHEDULE_TZ = "Australia/Sydney"
SCHEDULE_HOUR = 18
SCHEDULE_MINUTE = 0


def _most_recent_active_session_id() -> str | None:
    conn = registry_db.get_db()
    row = conn.execute(
        "SELECT session_id FROM session_presence ORDER BY last_seen_ms DESC LIMIT 1",
    ).fetchone()
    if not row:
        return None
    return str(row[0]) if row[0] else None


def _run_key_for_now(*, now_ms_value: int, tz_name: str) -> str:
    tz = ZoneInfo(tz_name)
    now_dt = dt.datetime.fromtimestamp(now_ms_value / 1000.0, tz=tz)
    return now_dt.strftime("%Y-%m-%d")


def maybe_enqueue_daily_email_digest(*, force: bool = False, now_ms_value: int | None = None) -> int:
    """Enqueue email unread digest tasks at 18:00 Sydney in proactive/silent_proactive.

    Returns number of tasks enqueued.
    """
    work_mode = get_work_mode_global()
    if work_mode not in {"proactive", "silent_proactive"} and not force:
        return 0
    if not auto_execute_enabled() and not force:
        return 0

    nowv = int(now_ms_value or now_ms())
    tz = ZoneInfo(SCHEDULE_TZ)
    now_dt = dt.datetime.fromtimestamp(nowv / 1000.0, tz=tz)

    if not force:
        if now_dt.hour != SCHEDULE_HOUR or now_dt.minute != SCHEDULE_MINUTE:
            return 0

    run_key = _run_key_for_now(now_ms_value=nowv, tz_name=SCHEDULE_TZ)

    inst_store = EmailInstanceStore()
    run_store = EmailDigestRunStore()
    work_store = WorkStore()
    task_store = ExecTaskStore()
    cards = StateCardStore()
    inbox = InboxService()
    injector = ChatInjector()

    session_id = _most_recent_active_session_id()

    enqueued = 0
    for inst in inst_store.list():
        if run_store.already_ran(instance_id=inst.instance_id, run_key=run_key) and not force:
            continue

        # Create/refresh a session-scoped card when we have a target session. Otherwise global-only.
        scope_type = "session" if session_id else "global"
        scope_id = session_id or "all"
        merge_key = f"email_unread_digest:{inst.instance_id}:{run_key}:{scope_id}"
        event_id = f"email_digest_{ulid()}"
        upsert = cards.upsert_open_card(
            scope_type=scope_type,
            scope_id=scope_id,
            card_type="email_unread_digest",
            severity="warn",  # injection still guarded and rate-limited
            title=f"Email digest ({inst.name})",
            summary="Scheduled digest queued (pending execution).",
            merge_key=merge_key,
            event_id=event_id,
            event_created_at_ms=nowv,
            metadata_json=json.dumps({"instance_id": inst.instance_id, "run_key": run_key, "tz": SCHEDULE_TZ}, ensure_ascii=False),
            cooldown_until_ms=None,
        )
        inbox.enqueue_from_card(card=upsert.card, delivery_type="inbox_only")

        work = work_store.create(
            type="summary",
            title=f"Email unread digest: {inst.name}",
            scope_type=scope_type,
            scope_id=scope_id,
            source_card_id=upsert.card.card_id,
            priority=3,
            summary="Queued",
            detail={"instance_id": inst.instance_id, "instance_name": inst.name, "run_key": run_key},
        )

        task_id = task_store.enqueue(
            task_type="email_unread_digest",
            idempotency_key=f"email_digest:{inst.instance_id}:{run_key}:{scope_id}",
            work_id=work.work_id,
            card_id=upsert.card.card_id,
            risk_level="low",
            requires_confirmation=False,
            input_obj={
                "instance_id": inst.instance_id,
                "instance_name": inst.name,
                "run_key": run_key,
                "schedule_tz": SCHEDULE_TZ,
                # Let the runner update the card summary deterministically.
                "card_id": upsert.card.card_id,
            },
        )

        # Strict redline: silent_proactive must never attempt chat injection.
        # Proactive: best-effort enqueue, still gated by guard/rate limits.
        if work_mode == "proactive" and scope_type == "session":
            injector.maybe_enqueue_from_card_id(card_id=upsert.card.card_id)

        run_store.mark_ran(instance_id=inst.instance_id, run_key=run_key, last_run_ms=nowv)
        enqueued += 1

    return enqueued
