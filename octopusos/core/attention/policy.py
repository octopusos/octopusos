from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from octopusos.core.attention.attention_mode import (
    card_cooldown_ms,
    get_attention_mode_global,
    quiet_hours_enabled,
    quiet_hours_end,
    quiet_hours_start,
)
from octopusos.core.attention.models import InboxDeliveryType, StateCard


Decision = Literal["suppress", "inbox_only", "notify", "confirm"]


@dataclass(frozen=True)
class DeliveryDecision:
    decision: Decision
    delivery_type: InboxDeliveryType | None = None
    reason: str = ""


def _parse_hhmm(value: str) -> tuple[int, int] | None:
    raw = (value or "").strip()
    if len(raw) != 5 or raw[2] != ":":
        return None
    try:
        hh = int(raw[0:2])
        mm = int(raw[3:5])
    except Exception:
        return None
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return hh, mm


def _in_quiet_hours(now_struct: time.struct_time) -> bool:
    start = _parse_hhmm(quiet_hours_start())
    end = _parse_hhmm(quiet_hours_end())
    if not start or not end:
        return False
    start_min = start[0] * 60 + start[1]
    end_min = end[0] * 60 + end[1]
    now_min = now_struct.tm_hour * 60 + now_struct.tm_min
    if start_min == end_min:
        return False
    if start_min < end_min:
        return start_min <= now_min < end_min
    # Window crosses midnight.
    return now_min >= start_min or now_min < end_min


def decide_delivery(*, card: StateCard, now_ms: int, is_new: bool, has_existing_delivery: bool) -> DeliveryDecision:
    mode = get_attention_mode_global()
    if mode == "silent":
        return DeliveryDecision(decision="suppress", reason="mode:silent")

    if quiet_hours_enabled():
        try:
            if _in_quiet_hours(time.localtime(now_ms / 1000.0)):
                # Still allow inbox-only on initial creation; suppress noisy updates.
                if not is_new:
                    return DeliveryDecision(decision="suppress", reason="quiet_hours:update")
        except Exception:
            pass

    # Cooldown is meant to suppress repeated updates after we've delivered at least once.
    if (
        not is_new
        and has_existing_delivery
        and card.cooldown_until_ms is not None
        and now_ms < int(card.cooldown_until_ms)
    ):
        return DeliveryDecision(decision="suppress", reason="card:cooldown_until")

    # Avoid writing on every update. Exception: if the card was created while delivery was suppressed
    # (e.g. mode=silent), and later modes enable delivery, we should enqueue once.
    if not is_new and has_existing_delivery:
        return DeliveryDecision(decision="suppress", reason="update:already_delivered")

    if mode == "reactive":
        return DeliveryDecision(decision="inbox_only", delivery_type="inbox_only", reason="mode:reactive")
    if mode == "proactive":
        # Gate-2 redline: no chat insertion. Delivery channel is inbox only for now.
        return DeliveryDecision(decision="inbox_only", delivery_type="inbox_only", reason="mode:proactive")

    return DeliveryDecision(decision="suppress", reason="mode:unknown")


def compute_next_cooldown_until_ms(now_ms: int) -> int | None:
    cooldown = int(card_cooldown_ms() or 0)
    if cooldown <= 0:
        return None
    return int(now_ms + cooldown)
