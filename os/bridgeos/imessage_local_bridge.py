from __future__ import annotations

import hmac
import json
import logging
import re
import sqlite3
import hashlib
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib import request
from urllib.error import HTTPError, URLError


logger = logging.getLogger(__name__)


APPLE_SCRIPT_SEND = r"""
on run argv
  set targetId to item 1 of argv
  set messageText to item 2 of argv
  tell application "Messages"
    set targetService to 1st service whose service type = iMessage
    set targetEntity to missing value
    try
      set targetEntity to buddy targetId of targetService
    end try
    if targetEntity is missing value then
      try
        set targetEntity to first chat whose id contains targetId
      end try
    end if
    if targetEntity is missing value then
      error "target_not_found"
    end if
    send messageText to targetEntity
  end tell
  return "ok"
end run
"""


POLL_QUERY = """
SELECT
  m.ROWID AS rowid,
  m.guid AS guid,
  m.date AS message_date_raw,
  m.text AS text,
  m.is_from_me AS is_from_me,
  h.id AS sender_id,
  c.chat_identifier AS chat_identifier
FROM message m
LEFT JOIN handle h ON h.ROWID = m.handle_id
LEFT JOIN (
  SELECT message_id, MIN(chat_id) AS chat_id
  FROM chat_message_join
  GROUP BY message_id
) cm ON cm.message_id = m.ROWID
LEFT JOIN chat c ON c.ROWID = cm.chat_id
WHERE m.ROWID > ? AND m.is_from_me = 0
ORDER BY m.ROWID ASC
LIMIT ?
"""


def _now_ms() -> int:
    return int(time.time() * 1000)


def _json_response(handler: BaseHTTPRequestHandler, code: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


@dataclass
class BridgeConfig:
    listen_host: str
    listen_port: int
    webhook_url: str
    bridge_token: str
    poll_interval_s: float
    db_path: Path
    state_file: Path
    bootstrap_latest: bool
    batch_size: int = 30
    send_timeout_s: float = 20.0
    webhook_timeout_s: float = 8.0
    allow_from_me: bool = False
    auto_delete_self_mirror: bool = False


class IMessageLocalBridge:
    def __init__(self, cfg: BridgeConfig):
        self.cfg = cfg
        self._stop = threading.Event()
        self._poll_thread: Optional[threading.Thread] = None
        self._server: Optional[ThreadingHTTPServer] = None
        self._lock = threading.Lock()
        self._last_rowid = 0
        # outbound fingerprint cache (ts_ms, conversation_key, fingerprint).
        # Used for self-chat soft echo filtering only.
        self._recent_outbound: deque[tuple[int, str, str]] = deque(maxlen=256)
        # short-window inbound fingerprint cache to suppress mirrored duplicate rows
        self._recent_inbound: deque[tuple[int, str, str, str]] = deque(maxlen=512)

        self.cfg.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_state()

    def _load_state(self) -> None:
        try:
            if not self.cfg.state_file.exists():
                return
            data = json.loads(self.cfg.state_file.read_text(encoding="utf-8"))
            self._last_rowid = int(data.get("last_rowid") or 0)
        except Exception:
            logger.warning("failed to load state file: %s", self.cfg.state_file)

    def _save_state(self) -> None:
        payload = {"last_rowid": int(self._last_rowid), "updated_at_ms": _now_ms()}
        self.cfg.state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _db_connect(self) -> sqlite3.Connection:
        uri = f"file:{self.cfg.db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _db_write_connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.cfg.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # macOS Messages DB includes trigger UDFs not available in this process.
        # Register no-op replacements so best-effort mirror cleanup can run.
        try:
            conn.create_function("after_delete_message_plugin", 2, lambda *_: None)
        except Exception:
            pass
        try:
            conn.create_function("before_delete_attachment_path", 2, lambda *_: None)
        except Exception:
            pass
        try:
            conn.create_function("delete_attachment_path", 1, lambda *_: None)
        except Exception:
            pass
        return conn

    def _read_latest_rowid(self) -> int:
        with self._db_connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(ROWID), 0) AS max_rowid FROM message").fetchone()
            return int(row["max_rowid"] if row else 0)

    def _send_to_imessage(self, target: str, text: str) -> None:
        cmd = ["osascript", "-e", APPLE_SCRIPT_SEND, target, text]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.cfg.send_timeout_s)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(f"osascript_failed:{detail[:240]}")
        conv = str(target).strip()
        self._recent_outbound.append((_now_ms(), conv, self._outbound_fingerprint(conv, str(text))))
        if self.cfg.auto_delete_self_mirror:
            try:
                self._cleanup_recent_self_mirror_after_send(conversation=conv, sent_text=str(text))
            except Exception as exc:
                logger.warning("post_send_self_mirror_cleanup_failed conversation=%s error=%s", conv, exc)

    def _post_webhook(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        token = self.cfg.bridge_token.strip()
        if token:
            headers["X-iMessage-Token"] = token
        req = request.Request(self.cfg.webhook_url, data=data, headers=headers, method="POST")
        with request.urlopen(req, timeout=self.cfg.webhook_timeout_s) as resp:
            code = int(resp.getcode() or 0)
            if code not in (200, 201, 202):
                raise RuntimeError(f"webhook_status_{code}")

    def _build_inbound_payload(self, row: sqlite3.Row) -> Optional[dict[str, Any]]:
        is_from_me = bool(int(row["is_from_me"] or 0))
        sender = str(row["sender_id"] or "").strip()
        convo = str(row["chat_identifier"] or "").strip()
        if not convo:
            convo = sender
        if not sender:
            sender = convo
        text = str(row["text"] or "").strip()
        if not text:
            logger.info(
                "ignored_message_shell rowid=%s reason=empty_text_selfchat_shell is_from_me=%s sender=%s conversation=%s",
                int(row["rowid"] or 0),
                int(is_from_me),
                sender or "-",
                convo or "-",
            )
            return None
        if not sender or not convo:
            return None
        # Self-chat echo protection:
        # only suppress when sender==conversation (self-chat), and the inbound payload
        # matches a very recent outbound fingerprint.
        if (
            not is_from_me
            and sender == convo
            and self._matches_recent_outbound_fingerprint(conversation=convo, text=text)
        ):
            logger.info(
                "suppressed self-chat inbound echo by outbound fingerprint (conversation=%s)",
                convo,
            )
            if self.cfg.auto_delete_self_mirror:
                try:
                    self._delete_message_row(int(row["rowid"]))
                    self._delete_recent_outbound_shells_for_conversation(
                        conversation=convo,
                        before_rowid=int(row["rowid"]),
                        before_message_date_raw=row["message_date_raw"],
                    )
                    logger.warning(
                        "auto_delete_self_mirror enabled: deleted mirrored inbound rowid=%s conversation=%s",
                        int(row["rowid"]),
                        convo,
                    )
                except Exception as exc:
                    logger.warning(
                        "auto_delete_self_mirror failed rowid=%s conversation=%s error=%s",
                        int(row["rowid"]),
                        convo,
                        exc,
                    )
            return None
        if self._is_recent_duplicate_inbound(sender=sender, conversation=convo, text=text):
            return None
        self._remember_inbound(sender=sender, conversation=convo, text=text)
        raw_guid = str(row["guid"] or f"imsg_{int(row['rowid'])}")
        semantic_dedupe_key = self._build_semantic_dedupe_key(
            sender=sender,
            conversation=convo,
            text=text,
            message_date_raw=row["message_date_raw"],
        )
        return {
            "message_id": raw_guid,
            "semantic_dedupe_key": semantic_dedupe_key,
            "from": sender,
            "conversation_id": convo,
            "text": text,
            "direction": "inbound",
            "from_me": is_from_me,
        }

    def _outbound_fingerprint(self, conversation: str, text: str) -> str:
        conv = str(conversation or "").strip().lower()
        body = self._normalize_echo_text(str(text or "").strip()).lower()
        payload = f"{conv}|{body}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _matches_recent_outbound_fingerprint(
        self,
        *,
        conversation: str,
        text: str,
        ttl_ms: int = 15_000,
    ) -> bool:
        now = _now_ms()
        conv = str(conversation or "").strip()
        if not conv:
            return False
        fp = self._outbound_fingerprint(conv, text)
        while self._recent_outbound and (now - self._recent_outbound[0][0]) > ttl_ms:
            self._recent_outbound.popleft()
        for ts, out_conv, out_fp in self._recent_outbound:
            if (now - ts) > ttl_ms:
                continue
            if out_conv == conv and out_fp == fp:
                return True
        return False

    def _build_semantic_dedupe_key(
        self,
        *,
        sender: str,
        conversation: str,
        text: str,
        message_date_raw: Any,
    ) -> str:
        # Apple `message.date` is stable for mirrored records of the same user action.
        # Use it with normalized identity+text to collapse at-least-once duplicates
        # even when GUID differs across mirrored copies.
        payload = "|".join(
            [
                str(sender or "").strip().lower(),
                str(conversation or "").strip().lower(),
                self._normalize_echo_text(str(text or "")).lower(),
                str(message_date_raw or "").strip(),
            ]
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"imsg_sem_{digest[:32]}"

    def _remember_inbound(self, *, sender: str, conversation: str, text: str) -> None:
        self._recent_inbound.append(
            (
                _now_ms(),
                str(sender or "").strip(),
                str(conversation or "").strip(),
                self._normalize_echo_text(str(text or "").strip()),
            )
        )

    def _is_recent_duplicate_inbound(self, *, sender: str, conversation: str, text: str) -> bool:
        now = _now_ms()
        snd = str(sender or "").strip()
        conv = str(conversation or "").strip()
        body = self._normalize_echo_text(str(text or "").strip())
        if not snd or not conv or not body:
            return False
        # iMessage self-chat can replay the same message in delayed waves.
        # Use a wider dedupe window for short texts, narrower for normal text.
        ttl_ms = 60_000 if len(body) <= 8 else 12_000
        while self._recent_inbound and (now - self._recent_inbound[0][0]) > ttl_ms:
            self._recent_inbound.popleft()
        for ts, s0, c0, b0 in self._recent_inbound:
            if (now - ts) > ttl_ms:
                continue
            if s0 == snd and c0 == conv and b0 == body:
                return True
        return False

    def _delete_recent_outbound_shells_for_conversation(
        self,
        *,
        conversation: str,
        before_rowid: int,
        before_message_date_raw: Any,
        max_age_ns: int = 30_000_000_000,
        max_rows: int = 3,
    ) -> None:
        conv = str(conversation or "").strip()
        if not conv:
            return
        rid = int(before_rowid or 0)
        if rid <= 0:
            return
        try:
            raw_date = int(before_message_date_raw or 0)
        except Exception:
            raw_date = 0
        min_date = raw_date - int(max_age_ns) if raw_date > 0 else 0
        with self._db_write_connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT m.ROWID AS rowid
                FROM message m
                LEFT JOIN handle h ON h.ROWID = m.handle_id
                LEFT JOIN (
                  SELECT message_id, MIN(chat_id) AS chat_id
                  FROM chat_message_join
                  GROUP BY message_id
                ) cm ON cm.message_id = m.ROWID
                LEFT JOIN chat c ON c.ROWID = cm.chat_id
                WHERE m.ROWID < ?
                  AND m.is_from_me = 1
                  AND trim(COALESCE(m.text, '')) = ''
                  AND COALESCE(c.chat_identifier, h.id, '') = ?
                  AND (
                        ? = 0
                        OR (m.date <= ? AND m.date >= ?)
                  )
                ORDER BY m.ROWID DESC
                LIMIT ?
                """,
                (rid, conv, raw_date, raw_date, min_date, int(max_rows)),
            ).fetchall()
            if not rows:
                return
            for row in rows:
                self._delete_message_row(int(row["rowid"]))
                logger.warning(
                    "auto_delete_self_mirror enabled: deleted companion outbound shell rowid=%s conversation=%s",
                    int(row["rowid"]),
                    conv,
                )

    def _cleanup_recent_self_mirror_after_send(
        self,
        *,
        conversation: str,
        sent_text: str,
        wait_s: float = 2.4,
        poll_interval_s: float = 0.2,
    ) -> None:
        conv = str(conversation or "").strip()
        if not conv:
            return
        sent_norm = self._normalize_echo_text(str(sent_text or "")).lower()
        if not sent_norm:
            return
        deadline = time.time() + max(0.2, float(wait_s))
        while time.time() < deadline:
            with self._db_write_connect() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT m.ROWID AS rowid, m.text AS text, m.date AS message_date_raw
                    FROM message m
                    LEFT JOIN handle h ON h.ROWID = m.handle_id
                    LEFT JOIN (
                      SELECT message_id, MIN(chat_id) AS chat_id
                      FROM chat_message_join
                      GROUP BY message_id
                    ) cm ON cm.message_id = m.ROWID
                    LEFT JOIN chat c ON c.ROWID = cm.chat_id
                    WHERE m.is_from_me = 0
                      AND COALESCE(c.chat_identifier, h.id, '') = ?
                    ORDER BY m.ROWID DESC
                    LIMIT 8
                    """,
                    (conv,),
                ).fetchall()
            for row in rows:
                txt = self._normalize_echo_text(str(row["text"] or "")).lower()
                if txt != sent_norm:
                    continue
                rid = int(row["rowid"])
                self._delete_message_row(rid)
                self._delete_recent_outbound_shells_for_conversation(
                    conversation=conv,
                    before_rowid=rid,
                    before_message_date_raw=row["message_date_raw"],
                )
                logger.warning(
                    "auto_delete_self_mirror enabled: post-send deleted mirrored inbound rowid=%s conversation=%s",
                    rid,
                    conv,
                )
                return
            time.sleep(max(0.05, float(poll_interval_s)))

    def _delete_message_row(self, rowid: int) -> None:
        rid = int(rowid)
        if rid <= 0:
            return
        with self._db_write_connect() as conn:
            cur = conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            # Keep deletes conservative and local to this message row.
            for table in ("chat_message_join", "message_attachment_join"):
                if self._table_exists(conn, table):
                    cur.execute(f"DELETE FROM {table} WHERE message_id = ?", (rid,))
            cur.execute("DELETE FROM message WHERE ROWID = ?", (rid,))
            conn.commit()

    @staticmethod
    def _is_self_chat_inbound_row(row: sqlite3.Row) -> bool:
        try:
            is_from_me = bool(int(row["is_from_me"] or 0))
        except Exception:
            is_from_me = False
        sender = str(row["sender_id"] or "").strip()
        convo = str(row["chat_identifier"] or "").strip()
        if not convo:
            convo = sender
        if not sender:
            sender = convo
        return (not is_from_me) and bool(sender) and bool(convo) and sender == convo

    @staticmethod
    def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        return row is not None

    @staticmethod
    def _normalize_echo_text(text: str) -> str:
        s = str(text or "").strip()
        s = re.sub(r"^\[[^\]]+\]\s*", "", s)
        s = re.sub(r"\s+", " ", s)
        return s

    def _poll_loop(self) -> None:
        logger.info("iMessage poller started (db=%s)", self.cfg.db_path)
        while not self._stop.is_set():
            try:
                query = POLL_QUERY if not self.cfg.allow_from_me else POLL_QUERY.replace(
                    "WHERE m.ROWID > ? AND m.is_from_me = 0",
                    "WHERE m.ROWID > ?",
                )
                with self._db_connect() as conn:
                    rows = conn.execute(query, (int(self._last_rowid), int(self.cfg.batch_size))).fetchall()
                if not rows:
                    self._stop.wait(self.cfg.poll_interval_s)
                    continue

                for row in rows:
                    if self._stop.is_set():
                        break
                    rid = int(row["rowid"])
                    payload = self._build_inbound_payload(row)
                    if payload is None:
                        self._last_rowid = rid
                        self._save_state()
                        continue
                    try:
                        self._post_webhook(payload)
                    except Exception as exc:
                        logger.warning("webhook post failed for rowid=%s: %s", rid, exc)
                        break
                    if self.cfg.auto_delete_self_mirror and self._is_self_chat_inbound_row(row):
                        try:
                            self._delete_message_row(rid)
                            logger.warning(
                                "auto_delete_self_mirror enabled: deleted processed inbound self-chat rowid=%s",
                                rid,
                            )
                        except Exception as exc:
                            logger.warning(
                                "auto_delete_self_mirror failed after webhook rowid=%s error=%s",
                                rid,
                                exc,
                            )
                    self._last_rowid = rid
                    self._save_state()
            except Exception as exc:
                logger.warning("poll loop error: %s", exc)
                self._stop.wait(max(1.0, self.cfg.poll_interval_s))

    def _token_ok(self, headers: dict[str, str]) -> bool:
        expected = self.cfg.bridge_token.strip()
        if not expected:
            return True
        h1 = str(headers.get("x-imessage-token") or "").strip()
        if not h1:
            auth = str(headers.get("authorization") or "").strip()
            if auth.lower().startswith("bearer "):
                h1 = auth[7:].strip()
        return bool(h1) and hmac.compare_digest(h1, expected)

    def start(self) -> None:
        if not self.cfg.db_path.exists():
            raise FileNotFoundError(f"Messages database not found: {self.cfg.db_path}")

        if self._last_rowid <= 0 and self.cfg.bootstrap_latest:
            self._last_rowid = self._read_latest_rowid()
            self._save_state()
            logger.info("bootstrap_latest=true, start from rowid=%s", self._last_rowid)

        bridge = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "OctopusOS-iMessage-Bridge/0.1"

            def do_GET(self) -> None:  # noqa: N802
                if self.path in ("/health", "/api/health", "/"):
                    _json_response(
                        self,
                        200,
                        {
                            "ok": True,
                            "service": "imessage-local-bridge",
                            "last_rowid": bridge._last_rowid,
                            "webhook_url": bridge.cfg.webhook_url,
                        },
                    )
                    return
                _json_response(self, 404, {"ok": False, "error": "not_found"})

            def do_POST(self) -> None:  # noqa: N802
                if self.path != "/api/imessage/send":
                    _json_response(self, 404, {"ok": False, "error": "not_found"})
                    return

                if not bridge._token_ok({k.lower(): v for k, v in self.headers.items()}):
                    _json_response(self, 401, {"ok": False, "error": "unauthorized"})
                    return

                try:
                    size = int(self.headers.get("content-length") or 0)
                    raw = self.rfile.read(size) if size > 0 else b"{}"
                    payload = json.loads(raw.decode("utf-8") or "{}")
                    target = str(payload.get("to") or payload.get("conversation_key") or payload.get("user_key") or "").strip()
                    text = str(payload.get("text") or "").strip()
                    if not target or not text:
                        _json_response(self, 400, {"ok": False, "error": "target_and_text_required"})
                        return
                    bridge._send_to_imessage(target, text)
                    _json_response(self, 200, {"ok": True, "sent": True})
                except json.JSONDecodeError:
                    _json_response(self, 400, {"ok": False, "error": "invalid_json"})
                except subprocess.TimeoutExpired:
                    _json_response(self, 504, {"ok": False, "error": "send_timeout"})
                except Exception as exc:  # keep boundary explicit in response
                    _json_response(self, 500, {"ok": False, "error": f"send_failed:{exc}"})

            def log_message(self, fmt: str, *args: Any) -> None:
                logger.info("http %s - %s", self.address_string(), fmt % args)

        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True, name="imessage-db-poller")
        self._poll_thread.start()

        self._server = ThreadingHTTPServer((self.cfg.listen_host, self.cfg.listen_port), Handler)
        logger.info(
            "iMessage bridge listening on http://%s:%s (webhook=%s)",
            self.cfg.listen_host,
            self.cfg.listen_port,
            self.cfg.webhook_url,
        )
        try:
            self._server.serve_forever(poll_interval=0.5)
        finally:
            self.stop()

    def stop(self) -> None:
        self._stop.set()
        if self._server is not None:
            try:
                self._server.shutdown()
            except Exception:
                pass
            try:
                self._server.server_close()
            except Exception:
                pass
            self._server = None
        if self._poll_thread is not None and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=2.0)
        self._save_state()


def run_bridge(cfg: BridgeConfig) -> None:
    bridge = IMessageLocalBridge(cfg)
    bridge.start()
