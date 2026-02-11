from __future__ import annotations

import json

from octopusos.core.attention.models import StateCard
from octopusos.core.attention.state_card_store import StateCardStore
from octopusos.core.work.exec_task_store import ExecTaskStore
from octopusos.core.work.work_store import WorkStore
from octopusos.core.work.work_mode import auto_execute_enabled, auto_execute_safe_only
from octopusos.store.timestamp_utils import now_ms


class WorkService:
    def __init__(self) -> None:
        self._work = WorkStore()
        self._tasks = ExecTaskStore()
        self._cards = StateCardStore()

    def maybe_create_from_card(self, *, card: StateCard) -> tuple[str | None, str | None]:
        """Create work item + exec task for selected trigger cards.

        Returns:
          (work_id, task_id) or (None, None) if not eligible.
        """
        if not auto_execute_enabled():
            return None, None
        if auto_execute_safe_only() is False:
            # Phase 4: we only ship safe tasks; do not run riskier tasks automatically yet.
            pass

        if card.scope_type != "session":
            return None, None
        session_id = card.scope_id
        if not session_id:
            return None, None

        if card.card_type == "context_integrity_blocked":
            existing = self._work.find_latest_for_card(source_card_id=card.card_id, type="investigation")
            work = existing or self._work.create(
                type="investigation",
                title="Context integrity blocked",
                scope_type="session",
                scope_id=session_id,
                source_card_id=card.card_id,
                priority=2,
                summary="Preparing context repair assistance task.",
                detail={"card_id": card.card_id, "session_id": session_id, "card_type": card.card_type},
            )
            task_id = self._tasks.enqueue(
                task_type="context_repair_assist",
                idempotency_key=f"ctxfix:{card.card_id}",
                work_id=work.work_id,
                card_id=card.card_id,
                risk_level="low",
                requires_confirmation=False,
                input_obj={"card_id": card.card_id, "session_id": session_id},
            )
            self._cards.update_resolution(
                card_id=card.card_id,
                resolution_status="acknowledged",
                resolved_by="system",
                resolved_at_ms=now_ms(),
                resolution_reason="auto_execute_enqueued",
                linked_task_id=task_id,
            )
            return work.work_id, task_id

        if card.card_type == "chat_writer_anomaly":
            existing = self._work.find_latest_for_card(source_card_id=card.card_id, type="recovery")
            work = existing or self._work.create(
                type="recovery",
                title="Write anomaly detected",
                scope_type="session",
                scope_id=session_id,
                source_card_id=card.card_id,
                priority=1,
                summary="Preparing writer recovery assistance task.",
                detail={"card_id": card.card_id, "session_id": session_id, "card_type": card.card_type},
            )
            # Best-effort: attach failed event id if present in metadata_json.
            failed_event_id = None
            try:
                meta = json.loads(card.metadata_json or "{}")
                if isinstance(meta, dict):
                    failed_event_id = meta.get("source_event_id") or meta.get("failed_event_id")
            except Exception:
                failed_event_id = None

            task_id = self._tasks.enqueue(
                task_type="writer_recovery_assist",
                idempotency_key=f"wfix:{card.card_id}",
                work_id=work.work_id,
                card_id=card.card_id,
                risk_level="low",
                requires_confirmation=False,
                input_obj={"card_id": card.card_id, "session_id": session_id, "failed_event_id": failed_event_id},
            )
            self._cards.update_resolution(
                card_id=card.card_id,
                resolution_status="acknowledged",
                resolved_by="system",
                resolved_at_ms=now_ms(),
                resolution_reason="auto_execute_enqueued",
                linked_task_id=task_id,
            )
            return work.work_id, task_id

        return None, None

