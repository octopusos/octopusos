from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from octopusos.core.attention.inbox_service import InboxService
from octopusos.core.attention.state_card_store import StateCardStore
from octopusos.core.db import registry_db
from octopusos.store.timestamp_utils import now_ms


router = APIRouter(tags=["inbox"])


class ListInboxQuery(BaseModel):
    status: str = Field(default="unread")
    limit: int = Field(default=50, ge=1, le=500)
    scope_type: str | None = None
    scope_id: str | None = None


@router.get("/api/inbox/items")
def list_inbox_items(status: str = "unread", limit: int = 50, scope_type: str | None = None, scope_id: str | None = None):
    svc = InboxService()
    result = svc.list_items(status=status, limit=limit, scope_type=scope_type, scope_id=scope_id)
    card_ids = [item.card_id for item in result.items]
    cards_by_id: dict[str, dict] = {}
    if card_ids:
        conn = registry_db.get_db()
        rows = conn.execute(
            """
            SELECT card_id, scope_type, scope_id, card_type, severity, status, title, summary,
                   first_seen_ms, last_seen_ms, last_event_id, merge_key, cooldown_until_ms, metadata_json,
                   resolution_status, resolution_reason, resolved_at_ms, resolved_by, resolution_note, linked_task_id
            FROM state_cards
            WHERE card_id IN ({})
            """.format(",".join(["?"] * len(card_ids))),
            tuple(card_ids),
        ).fetchall()
        for row in rows or []:
            cards_by_id[str(row[0])] = {
                "card_id": str(row[0]),
                "scope_type": str(row[1]),
                "scope_id": str(row[2]),
                "card_type": str(row[3]),
                "severity": str(row[4]),
                "status": str(row[5]),
                "title": str(row[6]),
                "summary": str(row[7]),
                "first_seen_ms": int(row[8]),
                "last_seen_ms": int(row[9]),
                "last_event_id": str(row[10]) if row[10] is not None else None,
                "merge_key": str(row[11]),
                "cooldown_until_ms": int(row[12]) if row[12] is not None else None,
                "metadata_json": str(row[13] or "{}"),
                "resolution_status": str(row[14] or "open"),
                "resolution_reason": str(row[15]) if row[15] is not None else None,
                "resolved_at_ms": int(row[16]) if row[16] is not None else None,
                "resolved_by": str(row[17]) if row[17] is not None else None,
                "resolution_note": str(row[18]) if row[18] is not None else None,
                "linked_task_id": str(row[19]) if row[19] is not None else None,
            }
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "items": [{**item.__dict__, "card": cards_by_id.get(item.card_id)} for item in result.items],
            "unread_count": result.unread_count,
        },
    )


@router.get("/api/inbox/badge")
def inbox_badge():
    svc = InboxService()
    return JSONResponse(status_code=200, content={"ok": True, "unread_count": svc.unread_count()})


@router.post("/api/inbox/items/{inbox_item_id}/mark_read")
def mark_read(inbox_item_id: str):
    svc = InboxService()
    svc.mark_read(inbox_item_id=inbox_item_id)
    return JSONResponse(status_code=200, content={"ok": True})


@router.post("/api/inbox/cards/{card_id}/close")
def close_card(card_id: str):
    cards = StateCardStore()
    inbox = InboxService()
    cards.close_card(card_id=card_id)
    inbox.archive_for_card(card_id=card_id)
    return JSONResponse(status_code=200, content={"ok": True})


@router.post("/api/inbox/cards/{card_id}/ack")
def ack_card(card_id: str):
    ts = now_ms()
    cards = StateCardStore()
    cards.update_resolution(
        card_id=card_id,
        resolution_status="acknowledged",
        resolved_by="user",
        resolved_at_ms=ts,
        resolution_reason="user_ack",
    )
    return JSONResponse(status_code=200, content={"ok": True})


@router.post("/api/inbox/cards/{card_id}/resolve")
def resolve_card(card_id: str):
    ts = now_ms()
    cards = StateCardStore()
    inbox = InboxService()
    cards.update_resolution(
        card_id=card_id,
        resolution_status="resolved",
        resolved_by="user",
        resolved_at_ms=ts,
        resolution_reason="user_resolve",
    )
    inbox.archive_for_card(card_id=card_id)
    return JSONResponse(status_code=200, content={"ok": True})


@router.post("/api/inbox/cards/{card_id}/dismiss")
def dismiss_card(card_id: str):
    ts = now_ms()
    cards = StateCardStore()
    inbox = InboxService()
    cards.update_resolution(
        card_id=card_id,
        resolution_status="dismissed",
        resolved_by="user",
        resolved_at_ms=ts,
        resolution_reason="user_dismiss",
    )
    inbox.archive_for_card(card_id=card_id)
    return JSONResponse(status_code=200, content={"ok": True})


class DeferPayload(BaseModel):
    defer_ms: int = Field(default=600_000, ge=1, le=86_400_000)
    reason: str = Field(default="user_defer")


@router.post("/api/inbox/cards/{card_id}/defer")
def defer_card(card_id: str, payload: DeferPayload):
    ts = now_ms()
    cards = StateCardStore()
    cards.update_resolution(
        card_id=card_id,
        resolution_status="deferred",
        resolved_by="user",
        resolved_at_ms=ts,
        resolution_reason=payload.reason,
        defer_until_ms=int(ts + int(payload.defer_ms)),
    )
    return JSONResponse(status_code=200, content={"ok": True})


@router.get("/api/inbox/cards/{card_id}")
def get_card_detail(card_id: str, limit: int = 50):
    """Return a consolidated transparency view for a card.

    Includes:
    - state_cards row
    - linked state_card_events
    - linked work_list_items + exec_tasks
    - recent chat_injection_* ledger events correlated to this card
    """
    limit = int(max(1, min(limit, 200)))
    conn = registry_db.get_db()
    row = conn.execute(
        """
        SELECT card_id, scope_type, scope_id, card_type, severity, status, title, summary,
               first_seen_ms, last_seen_ms, last_event_id, merge_key, cooldown_until_ms, metadata_json,
               resolution_status, resolution_reason, resolved_at_ms, resolved_by, resolution_note, linked_task_id
        FROM state_cards
        WHERE card_id = ?
        """,
        (str(card_id),),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="CARD_NOT_FOUND")

    card = {
        "card_id": str(row[0]),
        "scope_type": str(row[1]),
        "scope_id": str(row[2]),
        "card_type": str(row[3]),
        "severity": str(row[4]),
        "status": str(row[5]),
        "title": str(row[6]),
        "summary": str(row[7]),
        "first_seen_ms": int(row[8]),
        "last_seen_ms": int(row[9]),
        "last_event_id": str(row[10]) if row[10] is not None else None,
        "merge_key": str(row[11]),
        "cooldown_until_ms": int(row[12]) if row[12] is not None else None,
        "metadata_json": str(row[13] or "{}"),
        "resolution_status": str(row[14] or "open"),
        "resolution_reason": str(row[15]) if row[15] is not None else None,
        "resolved_at_ms": int(row[16]) if row[16] is not None else None,
        "resolved_by": str(row[17]) if row[17] is not None else None,
        "resolution_note": str(row[18]) if row[18] is not None else None,
        "linked_task_id": str(row[19]) if row[19] is not None else None,
    }

    ev_rows = conn.execute(
        """
        SELECT event_id, added_at_ms
        FROM state_card_events
        WHERE card_id = ?
        ORDER BY added_at_ms DESC
        LIMIT ?
        """,
        (str(card_id), limit),
    ).fetchall()
    state_card_events = [{"event_id": str(r[0]), "added_at_ms": int(r[1] or 0)} for r in ev_rows or []]

    work_rows = conn.execute(
        """
        SELECT work_id, type, title, status, priority, scope_type, scope_id, source_card_id,
               created_at_ms, updated_at_ms, started_at_ms, finished_at_ms, summary, detail_json, evidence_ref_json
        FROM work_list_items
        WHERE source_card_id = ?
        ORDER BY updated_at_ms DESC
        LIMIT ?
        """,
        (str(card_id), limit),
    ).fetchall()
    work_items = [
        {
            "work_id": str(r[0]),
            "type": str(r[1]),
            "title": str(r[2]),
            "status": str(r[3]),
            "priority": int(r[4] or 0),
            "scope_type": str(r[5]),
            "scope_id": str(r[6]),
            "source_card_id": str(r[7]) if r[7] is not None else None,
            "created_at_ms": int(r[8] or 0),
            "updated_at_ms": int(r[9] or 0),
            "started_at_ms": int(r[10]) if r[10] is not None else None,
            "finished_at_ms": int(r[11]) if r[11] is not None else None,
            "summary": str(r[12] or ""),
            "detail_json": str(r[13] or "{}"),
            "evidence_ref_json": str(r[14] or "[]"),
        }
        for r in work_rows or []
    ]

    task_rows = conn.execute(
        """
        SELECT task_id, work_id, card_id, task_type, status, risk_level, requires_confirmation,
               created_at_ms, updated_at_ms, started_at_ms, finished_at_ms,
               input_json, output_json, error_json, evidence_paths_json, idempotency_key
        FROM exec_tasks
        WHERE card_id = ?
        ORDER BY updated_at_ms DESC
        LIMIT ?
        """,
        (str(card_id), limit),
    ).fetchall()
    tasks = [
        {
            "task_id": str(r[0]),
            "work_id": str(r[1]) if r[1] is not None else None,
            "card_id": str(r[2]) if r[2] is not None else None,
            "task_type": str(r[3]),
            "status": str(r[4]),
            "risk_level": str(r[5]),
            "requires_confirmation": bool(int(r[6] or 0)),
            "created_at_ms": int(r[7] or 0),
            "updated_at_ms": int(r[8] or 0),
            "started_at_ms": int(r[9]) if r[9] is not None else None,
            "finished_at_ms": int(r[10]) if r[10] is not None else None,
            "input_json": str(r[11] or "{}"),
            "output_json": str(r[12] or "{}"),
            "error_json": str(r[13]) if r[13] is not None else None,
            "evidence_paths_json": str(r[14] or "[]"),
            "idempotency_key": str(r[15] or ""),
        }
        for r in task_rows or []
    ]

    inj_rows = conn.execute(
        """
        SELECT event_id, session_id, event_type, payload_json, created_at_ms
        FROM session_event_ledger
        WHERE event_type LIKE 'chat_injection_%' AND correlation_id = ?
        ORDER BY created_at_ms DESC
        LIMIT ?
        """,
        (str(card_id), limit),
    ).fetchall()
    injection_events = [
        {
            "event_id": str(r[0]),
            "session_id": str(r[1]),
            "event_type": str(r[2]),
            "payload_json": str(r[3] or "{}"),
            "created_at_ms": int(r[4] or 0),
        }
        for r in inj_rows or []
    ]

    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "card": card,
            "state_card_events": state_card_events,
            "work_items": work_items,
            "tasks": tasks,
            "chat_injection_events": injection_events,
        },
    )
