"""Engine-level session recording sink (append-only markdown corpus)."""

from __future__ import annotations

import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)

try:
    import fcntl  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - non-POSIX environments
    fcntl = None

SEQ_PATTERN = re.compile(r"^##\s+(\d{4})\s+·\s+\w+\s+·\s+([^\n]+)$", re.MULTILINE)
ROLE_PATTERN = re.compile(r"^(user|assistant|tool|system)$")


def _now_local() -> datetime:
    return datetime.now().astimezone()


def _iso_timestamp(dt: datetime | None = None) -> str:
    value = dt or _now_local()
    return value.isoformat(timespec="seconds")


def _compact_timestamp(dt: datetime | None = None) -> str:
    value = dt or _now_local()
    return value.strftime("%Y%m%dT%H%M%S%z")


def _slugify(raw: str) -> str:
    return re.sub(r"[^a-z0-9\-]+", "-", raw.lower()).strip("-") or "session"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _dump_front_matter(data: Dict[str, Any]) -> str:
    body = yaml.safe_dump(
        data,
        allow_unicode=False,
        sort_keys=False,
        default_flow_style=False,
    ).strip()
    return f"---\n{body}\n---\n"


@dataclass(frozen=True)
class SessionFile:
    path: Path
    session_id: str


class SessionLogger:
    """Create and append markdown session files using a stable schema."""

    def __init__(self, root_dir: str | Path = "recordings/sessions") -> None:
        self.root_dir = Path(root_dir)

    def create_session_file(
        self,
        *,
        session_id: str,
        session_slug: str | None = None,
        created_at: datetime | None = None,
        source: str = "codex",
        repo: str | None = None,
        branch: str | None = None,
        tags: list[str] | None = None,
        artifacts: list[str] | None = None,
    ) -> SessionFile:
        if not session_id:
            raise ValueError("session_id is required")

        created = created_at or _now_local()
        date_dir = created.strftime("%Y-%m-%d")
        slug = _slugify(session_slug or session_id)
        filename = f"{_compact_timestamp(created)}__{slug}.md"
        path = self.root_dir / date_dir / filename
        _ensure_parent(path)
        if path.exists():
            raise FileExistsError(f"session file already exists: {path}")

        front_matter: Dict[str, Any] = {
            "session_id": session_id,
            "created_at": _iso_timestamp(created),
            "source": source,
            "repo": repo or str(Path.cwd()),
        }
        if branch:
            front_matter["branch"] = branch
        if tags:
            front_matter["tags"] = tags
        if artifacts:
            front_matter["artifacts"] = artifacts

        header = f"# Session: {session_id}\n"
        path.write_text(f"{_dump_front_matter(front_matter)}\n{header}\n", encoding="utf-8")
        return SessionFile(path=path, session_id=session_id)

    def log_message(
        self,
        *,
        file_path: str | Path,
        role: str,
        content: str | Dict[str, Any] | list[Any],
        ts: datetime | None = None,
        message_id: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> int:
        if not ROLE_PATTERN.match(role):
            raise ValueError(f"invalid role: {role}")
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"session file not found: {path}")

        timestamp = _iso_timestamp(ts)
        with path.open("a+", encoding="utf-8") as file_obj:
            if fcntl is not None:
                fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX)
            try:
                file_obj.seek(0)
                current = file_obj.read()
                seq = self._next_seq(current)
                block = self._render_message_block(
                    seq=seq,
                    role=role,
                    timestamp=timestamp,
                    content=content,
                    message_id=message_id,
                    metadata=metadata,
                )
                file_obj.write(block)
                file_obj.flush()
                os.fsync(file_obj.fileno())
            finally:
                if fcntl is not None:
                    fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)
        return seq

    @staticmethod
    def _next_seq(raw: str) -> int:
        matches = [int(m.group(1)) for m in SEQ_PATTERN.finditer(raw)]
        return (matches[-1] + 1) if matches else 1

    @staticmethod
    def _render_message_block(
        *,
        seq: int,
        role: str,
        timestamp: str,
        content: str | Dict[str, Any] | list[Any],
        message_id: str | None,
        metadata: Dict[str, Any] | None,
    ) -> str:
        if isinstance(content, (dict, list)):
            content_body = "```json\n" + json.dumps(content, ensure_ascii=True, indent=2) + "\n```"
        else:
            content_body = str(content).rstrip()

        header = f"## {seq:04d} · {role} · {timestamp}"
        if message_id:
            header += f" · mid={message_id}"

        lines = [header]
        if metadata:
            metadata_body = yaml.safe_dump(
                metadata, allow_unicode=False, sort_keys=False, default_flow_style=False
            ).strip()
            lines.append("metadata:")
            lines.extend(f"  {line}" for line in metadata_body.splitlines())
        lines.append(content_body)
        return "\n".join(lines) + "\n\n"


@dataclass(frozen=True)
class RecordingPayload:
    session_id: str
    message_id: str
    role: str
    content: str
    created_at: datetime
    message_metadata: Dict[str, Any]


class SessionRecordingSink:
    """Asynchronous sidecar sink that records persisted messages."""

    def __init__(self, root_dir: str | Path = "recordings/sessions") -> None:
        self.logger = SessionLogger(root_dir=root_dir)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="session-recording")

    def enqueue(self, chat_service: Any, payload: RecordingPayload) -> None:
        self._executor.submit(self._record_message, chat_service, payload)

    def _record_message(self, chat_service: Any, payload: RecordingPayload) -> None:
        try:
            session = chat_service.get_session(payload.session_id)
            session_metadata = dict(session.metadata or {})
            if session_metadata.get("recording_last_message_id") == payload.message_id:
                return

            session_file = session_metadata.get("session_recording_file")
            path = Path(session_file).expanduser() if session_file else None
            if not path or not path.exists():
                created = self.logger.create_session_file(
                    session_id=payload.session_id,
                    session_slug=payload.session_id,
                    created_at=session.created_at,
                    source=str(session_metadata.get("source") or "codex"),
                    repo=str(session_metadata.get("repo") or Path.cwd()),
                    branch=session_metadata.get("branch"),
                    tags=session_metadata.get("tags") if isinstance(session_metadata.get("tags"), list) else None,
                    artifacts=(
                        session_metadata.get("artifacts")
                        if isinstance(session_metadata.get("artifacts"), list)
                        else None
                    ),
                )
                path = created.path
                chat_service.update_session_metadata(
                    payload.session_id, {"session_recording_file": str(path)}
                )

            structured_content: str | Dict[str, Any] | list[Any] = payload.content
            if payload.role == "tool":
                structured_content = self._coerce_tool_content(payload.content)

            seq = self.logger.log_message(
                file_path=path,
                role=payload.role,
                content=structured_content,
                ts=payload.created_at,
                message_id=payload.message_id,
                metadata=payload.message_metadata or None,
            )
            chat_service.update_session_metadata(
                payload.session_id,
                {
                    "recording_last_message_id": payload.message_id,
                    "recording_last_seq": seq,
                },
            )
        except Exception as exc:
            logger.warning(
                "Session recording sidecar failed for session %s message %s: %s",
                payload.session_id,
                payload.message_id,
                exc,
            )

    @staticmethod
    def _coerce_tool_content(content: str) -> str | Dict[str, Any] | list[Any]:
        if not isinstance(content, str):
            return content
        raw = content.strip()
        if not raw:
            return content
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, (dict, list)):
                return parsed
        except Exception:
            return content
        return content
