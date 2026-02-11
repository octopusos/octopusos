from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from zoneinfo import ZoneInfo

from octopusos.core.email.adapter import EmailAdapter
from octopusos.core.email.models import EmailHeader
from octopusos.store.timestamp_utils import now_ms


@dataclass(frozen=True)
class DigestResult:
    instance_id: str
    total_unread: int
    important: list[EmailHeader]
    normal: list[EmailHeader]
    filtered: list[EmailHeader]
    digest_md: str
    report_path: str


def _report_path(task_id: str) -> Path:
    out_dir = Path("reports") / "exec_tasks" / task_id
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / "email_unread_digest.md"


def _format_header(h: EmailHeader) -> str:
    when = dt.datetime.fromtimestamp(int(h.date_ms or 0) / 1000.0, tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")
    snippet = (h.snippet or "").strip().replace("\n", " ")
    snippet = (snippet[:160] + "...") if len(snippet) > 160 else snippet
    snip_line = f"  \n  snippet: {snippet}" if snippet else ""
    return (
        f"- **{h.subject or '(no subject)'}**  \n"
        f"  from: `{h.from_email}`  \n"
        f"  at: `{when}`  \n"
        f"  id: `{h.message_id}`{snip_line}"
    )


def build_digest_md(*, instance_name: str, headers: list[EmailHeader], tz_name: str) -> tuple[str, list[EmailHeader], list[EmailHeader], list[EmailHeader]]:
    important = [h for h in headers if h.importance == "important"]
    normal = [h for h in headers if h.importance == "normal"]
    filtered = [h for h in headers if h.importance == "filtered"]

    lines: list[str] = []
    lines.append("# Email unread digest")
    lines.append("")
    lines.append(f"You have **{len(headers)}** unread (Important **{len(important)}**).")
    lines.append("")
    lines.append(f"- instance: `{instance_name}`")
    lines.append(f"- generated_at_ms: `{now_ms()}`")
    lines.append(f"- timezone: `{tz_name}`")
    lines.append("")

    lines.append(f"## Important ({len(important)})")
    lines.append("")
    if important:
        for h in important[:6]:
            lines.append(_format_header(h))
            lines.append("")
            lines.append("  suggested: `Reply` | `Ignore` | `Block sender` | `Snooze 24h`")
    else:
        lines.append("_None_")
    lines.append("")

    lines.append(f"## Normal ({len(normal)})")
    lines.append("")
    lines.append("<details><summary>Show normal</summary>")
    lines.append("")
    if normal:
        lines.extend([_format_header(h) for h in normal[:20]])
    else:
        lines.append("_None_")
    lines.append("")
    lines.append("</details>")
    lines.append("")

    lines.append(f"## Filtered ({len(filtered)})")
    lines.append("")
    # Show only counts + top sources by default.
    domains: dict[str, int] = {}
    for h in filtered:
        sender = (h.from_email or "").strip().lower()
        dom = sender.split("@")[-1] if "@" in sender else ""
        if dom:
            domains[dom] = domains.get(dom, 0) + 1
    top = sorted(domains.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    if top:
        lines.append("Top sources:")
        for dom, cnt in top:
            lines.append(f"- `{dom}`: {cnt}")
        lines.append("")
    lines.append("<details><summary>Show filtered</summary>")
    lines.append("")
    if filtered:
        lines.extend([_format_header(h) for h in filtered[:30]])
    else:
        lines.append("_None_")
    lines.append("")
    lines.append("</details>")
    lines.append("")

    lines.append("## Next actions")
    lines.append("")
    lines.append("- Open Inbox (card) to review and act")
    lines.append("- Open MCP Email page to manage instances and rules")
    lines.append("- Draft reply to an important message (requires confirmation to send)")
    lines.append("")

    return "\n".join(lines) + "\n", important, normal, filtered


def since_start_of_day_ms(*, tz_name: str, now_ms_value: Optional[int] = None) -> int:
    tz = ZoneInfo(tz_name)
    now_dt = dt.datetime.fromtimestamp((now_ms_value or now_ms()) / 1000.0, tz=tz)
    sod = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(sod.timestamp() * 1000)


def run_unread_digest(*, task_id: str, instance_id: str, instance_name: str, since_ms: int | None, limit: int, tz_name: str) -> DigestResult:
    adapter = EmailAdapter()
    headers = adapter.list_unread(instance_id=instance_id, since_ms=since_ms, limit=limit)
    md, important, normal, filtered = build_digest_md(instance_name=instance_name, headers=headers, tz_name=tz_name)
    report = _report_path(task_id)
    report.write_text(md, encoding="utf-8")
    return DigestResult(
        instance_id=instance_id,
        total_unread=len(headers),
        important=important,
        normal=normal,
        filtered=filtered,
        digest_md=md,
        report_path=str(report),
    )
