from __future__ import annotations

import json
import re
from dataclasses import dataclass

from octopusos.core.email.models import EmailHeader
from octopusos.core.email.snooze_store import EmailSnoozeStore
from octopusos.store.timestamp_utils import now_ms


_MARKETING_SUBJECT_RE = re.compile(
    r"(sale|discount|promo|promotion|newsletter|unsubscribe|deal|offer|limited time|black friday|cyber monday)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FilterConfig:
    allow_senders: set[str]
    block_senders: set[str]
    block_domains: set[str]


def load_filter_config(config_json: str) -> FilterConfig:
    try:
        cfg = json.loads(config_json or "{}")
    except Exception:
        cfg = {}
    allow = cfg.get("allow_senders", [])
    block = cfg.get("block_senders", [])
    block_domains = cfg.get("block_domains", [])
    return FilterConfig(
        allow_senders={str(x).lower() for x in (allow if isinstance(allow, list) else []) if str(x).strip()},
        block_senders={str(x).lower() for x in (block if isinstance(block, list) else []) if str(x).strip()},
        block_domains={str(x).lower() for x in (block_domains if isinstance(block_domains, list) else []) if str(x).strip()},
    )


def classify_header(h: EmailHeader, cfg: FilterConfig) -> str:
    sender = (h.from_email or "").strip().lower()
    domain = sender.split("@")[-1] if "@" in sender else ""
    subj = (h.subject or "").strip()

    if sender in cfg.allow_senders:
        return "important"
    if sender in cfg.block_senders:
        return "filtered"
    if domain and domain in cfg.block_domains:
        return "filtered"
    if _MARKETING_SUBJECT_RE.search(subj):
        return "filtered"
    # Default: normal.
    return "normal"


def apply_classification(headers: list[EmailHeader], cfg: FilterConfig, *, instance_id: str | None = None) -> list[EmailHeader]:
    # Optional, best-effort snooze suppression. This is instance-scoped and
    # only affects our digest/unread views (does not modify mailbox state).
    snoozed: set[str] = set()
    try:
        iid = str(instance_id or "").strip()
        if iid:
            snoozed = EmailSnoozeStore().snoozed_message_ids(
                instance_id=iid,
                message_ids=[h.message_id for h in headers],
                now_ms_value=now_ms(),
            )
    except Exception:
        snoozed = set()

    out: list[EmailHeader] = []
    for h in headers:
        importance = "filtered" if h.message_id in snoozed else classify_header(h, cfg)
        out.append(
            EmailHeader(
                message_id=h.message_id,
                from_email=h.from_email,
                from_name=h.from_name,
                subject=h.subject,
                date_ms=h.date_ms,
                snippet=h.snippet,
                importance=importance,
            )
        )
    return out
