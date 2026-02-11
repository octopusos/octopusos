from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Optional

from octopusos.core.attention.inbox_service import InboxService
from octopusos.core.attention.chat_injector import ChatInjector
from octopusos.core.attention.card_catalog import cooldown_until_ms_for_card_type
from octopusos.core.attention.policy import compute_next_cooldown_until_ms, decide_delivery
from octopusos.core.attention.signal_shaper import shape_ledger_event
from octopusos.core.attention.state_card_store import StateCardStore
from octopusos.core.work.work_service import WorkService
from octopusos.core.chat.event_ledger import list_events_global
from octopusos.core.db import registry_db
from octopusos.core.db.writer import SQLiteWriter
from octopusos.store.timestamp_utils import now_ms


@dataclass(frozen=True)
class PollResult:
    processed_events: int
    created_cards: int
    enqueued_inbox: int


CHECKPOINT_NAME = "ledger_poll_state_cards_v1"


class LedgerPoller:
    def __init__(self) -> None:
        self._db_writer = SQLiteWriter(db_path=registry_db.get_db_path())
        self._cards = StateCardStore()
        self._inbox = InboxService()
        self._injector = ChatInjector()
        self._work = WorkService()

    def _load_checkpoint(self) -> tuple[int, str]:
        def _op(conn: sqlite3.Connection) -> tuple[int, str]:
            row = conn.execute(
                """
                SELECT last_created_at_ms, last_event_id
                FROM attention_checkpoints
                WHERE name = ?
                """,
                (CHECKPOINT_NAME,),
            ).fetchone()
            if not row:
                conn.execute(
                    "INSERT OR IGNORE INTO attention_checkpoints (name, last_created_at_ms, last_event_id) VALUES (?, 0, '')",
                    (CHECKPOINT_NAME,),
                )
                return 0, ""
            return int(row[0] or 0), str(row[1] or "")

        return self._db_writer.submit(_op, timeout=10.0)

    def _save_checkpoint(self, *, last_created_at_ms: int, last_event_id: str) -> None:
        def _op(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                INSERT INTO attention_checkpoints (name, last_created_at_ms, last_event_id)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                  last_created_at_ms = excluded.last_created_at_ms,
                  last_event_id = excluded.last_event_id
                """,
                (CHECKPOINT_NAME, int(last_created_at_ms), str(last_event_id)),
            )

        self._db_writer.submit(_op, timeout=10.0)

    def poll_and_shape_once(self, *, limit: int = 500) -> PollResult:
        after_ms, after_eid = self._load_checkpoint()
        events = list_events_global(after_created_at_ms=after_ms, after_event_id=after_eid, limit=limit)
        if not events:
            return PollResult(processed_events=0, created_cards=0, enqueued_inbox=0)

        created_cards = 0
        enqueued = 0
        last_ms = after_ms
        last_eid = after_eid
        now = now_ms()

        for e in events:
            last_ms = int(getattr(e, "created_at_ms", 0) or last_ms)
            last_eid = str(getattr(e, "event_id", "") or last_eid)

            shaped = shape_ledger_event(event=e)
            if not shaped:
                continue

            cooldown_until = cooldown_until_ms_for_card_type(card_type=shaped.card_type, now_ms=now)
            if cooldown_until is None:
                cooldown_until = compute_next_cooldown_until_ms(now)
            upsert = self._cards.upsert_open_card(
                scope_type=shaped.scope_type,
                scope_id=shaped.scope_id,
                card_type=shaped.card_type,
                severity=shaped.severity,
                title=shaped.title,
                summary=shaped.summary,
                merge_key=shaped.merge_key,
                event_id=shaped.event_id,
                event_created_at_ms=shaped.event_created_at_ms,
                metadata_json=shaped.metadata_json,
                cooldown_until_ms=cooldown_until,
            )
            self._cards.link_event(card_id=upsert.card.card_id, event_id=shaped.event_id, added_at_ms=now)

            if upsert.is_new:
                created_cards += 1
            has_delivery = self._inbox.has_delivery(card_id=upsert.card.card_id, delivery_type="inbox_only")
            decision = decide_delivery(card=upsert.card, now_ms=now, is_new=upsert.is_new, has_existing_delivery=has_delivery)
            if decision.decision == "inbox_only" and decision.delivery_type:
                item_id = self._inbox.enqueue_from_card(card=upsert.card, delivery_type=decision.delivery_type)
                if item_id:
                    enqueued += 1

            # Gate-3: if chat injection is allowed, enqueue into injection queue (consumer drains later).
            # Redline: do not directly insert into chat transcript here.
            #
            # Note: injection eligibility is independent from whether we enqueue an inbox delivery on this tick.
            # This allows "work mode" flips (reactive -> proactive) to take effect on subsequent events even if
            # the card was already delivered to inbox earlier. Idempotency in the queue prevents duplicates.
            if upsert.card.scope_type == "session":
                self._injector.maybe_enqueue_from_card_id(card_id=upsert.card.card_id)

            # Phase 4: actionability - create work + tasks for select trigger cards (safe-only).
            # This is always transparent: work/task are visible even in silent_proactive.
            self._work.maybe_create_from_card(card=upsert.card)

        self._save_checkpoint(last_created_at_ms=last_ms, last_event_id=last_eid)
        return PollResult(processed_events=len(events), created_cards=created_cards, enqueued_inbox=enqueued)
