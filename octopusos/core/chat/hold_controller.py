"""Async hold controller for streaming evidence gating."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
import uuid
from typing import Literal


HoldState = Literal["idle", "holding", "ready", "released", "timeout", "cancelled"]


@dataclass
class HoldResult:
    state: HoldState
    hold_id: str
    reason_code: str | None = None
    evidence_payload: dict | None = None


class HoldController:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cond = threading.Condition(self._lock)
        self._holds: dict[str, dict] = {}
        self._active_by_session: dict[str, str] = {}

    def begin_hold(self, session_id: str, run_id: str | None, gate_decision: dict) -> str:
        with self._cond:
            existing_id = self._active_by_session.get(session_id)
            if existing_id and existing_id in self._holds:
                existing = self._holds[existing_id]
                if existing["state"] in {"holding", "ready"}:
                    existing["state"] = "cancelled"
                    existing["reason_code"] = "cancelled_by_new_request"
                    existing["updated_at"] = time.time()

            hold_id = f"hold_{uuid.uuid4().hex[:12]}"
            self._holds[hold_id] = {
                "hold_id": hold_id,
                "session_id": session_id,
                "run_id": run_id,
                "state": "holding",
                "reason_code": None,
                "gate_decision": gate_decision,
                "evidence_payload": None,
                "created_at": time.time(),
                "updated_at": time.time(),
            }
            self._active_by_session[session_id] = hold_id
            self._cond.notify_all()
            return hold_id

    def active_hold_for_session(self, session_id: str) -> str | None:
        with self._lock:
            hold_id = self._active_by_session.get(session_id)
            if not hold_id:
                return None
            hold = self._holds.get(hold_id)
            if not hold:
                self._active_by_session.pop(session_id, None)
                return None
            if hold["state"] in {"holding", "ready"}:
                return hold_id
            return None

    def hold_state(self, hold_id: str) -> HoldState | None:
        with self._lock:
            hold = self._holds.get(hold_id)
            if not hold:
                return None
            return hold["state"]

    def wait_ready(self, hold_id: str, timeout_ms: int) -> HoldResult:
        deadline = time.time() + max(timeout_ms, 0) / 1000.0
        with self._cond:
            while True:
                hold = self._holds.get(hold_id)
                if hold is None:
                    return HoldResult(state="cancelled", hold_id=hold_id, reason_code="hold_not_found")

                state = hold["state"]
                if state in {"ready", "released", "timeout", "cancelled"}:
                    return HoldResult(
                        state=state,
                        hold_id=hold_id,
                        reason_code=hold.get("reason_code"),
                        evidence_payload=hold.get("evidence_payload"),
                    )

                remaining = deadline - time.time()
                if remaining <= 0:
                    hold["state"] = "timeout"
                    hold["reason_code"] = "STREAM_GATE_HOLD_TIMEOUT"
                    hold["updated_at"] = time.time()
                    self._cond.notify_all()
                    return HoldResult(state="timeout", hold_id=hold_id, reason_code="STREAM_GATE_HOLD_TIMEOUT")

                self._cond.wait(timeout=remaining)

    def mark_ready(self, hold_id: str, evidence_payload: dict) -> HoldResult:
        with self._cond:
            hold = self._holds.get(hold_id)
            if hold is None:
                return HoldResult(state="cancelled", hold_id=hold_id, reason_code="hold_not_found")

            if hold["state"] in {"cancelled", "timeout", "released"}:
                return HoldResult(state=hold["state"], hold_id=hold_id, reason_code=hold.get("reason_code"))

            hold["state"] = "ready"
            hold["evidence_payload"] = evidence_payload
            hold["updated_at"] = time.time()
            self._cond.notify_all()
            return HoldResult(state="ready", hold_id=hold_id, evidence_payload=evidence_payload)

    def release(self, hold_id: str, reason_code: str | None = None) -> HoldResult:
        with self._cond:
            hold = self._holds.get(hold_id)
            if hold is None:
                return HoldResult(state="cancelled", hold_id=hold_id, reason_code="hold_not_found")

            hold["state"] = "released"
            hold["reason_code"] = reason_code
            hold["updated_at"] = time.time()
            session_id = hold["session_id"]
            if self._active_by_session.get(session_id) == hold_id:
                self._active_by_session.pop(session_id, None)
            self._cond.notify_all()
            return HoldResult(
                state="released",
                hold_id=hold_id,
                reason_code=reason_code,
                evidence_payload=hold.get("evidence_payload"),
            )

    def cancel(self, hold_id: str, reason_code: str = "cancelled") -> HoldResult:
        with self._cond:
            hold = self._holds.get(hold_id)
            if hold is None:
                return HoldResult(state="cancelled", hold_id=hold_id, reason_code="hold_not_found")

            hold["state"] = "cancelled"
            hold["reason_code"] = reason_code
            hold["updated_at"] = time.time()
            session_id = hold["session_id"]
            if self._active_by_session.get(session_id) == hold_id:
                self._active_by_session.pop(session_id, None)
            self._cond.notify_all()
            return HoldResult(state="cancelled", hold_id=hold_id, reason_code=reason_code)
