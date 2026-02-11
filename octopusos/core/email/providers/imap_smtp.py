from __future__ import annotations

import email
import imaplib
import re
import smtplib
import ssl
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parseaddr, parsedate_to_datetime
from typing import Optional

from octopusos.core.email.models import EmailHeader, EmailMessage, SendResult
from octopusos.core.email.providers.base import EmailProvider
from octopusos.webui.secret_resolver import resolve_secret_ref
from octopusos.store.timestamp_utils import now_ms


def _decode_mime(value: str) -> str:
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value or ""


def _msg_date_ms(msg: Message) -> int:
    raw = msg.get("Date")
    if not raw:
        return now_ms()
    try:
        dt = parsedate_to_datetime(str(raw))
        return int(dt.timestamp() * 1000)
    except Exception:
        return now_ms()


def _extract_text_body(msg: Message) -> str:
    if msg.is_multipart():
        # Prefer text/plain, fall back to first part.
        plain = None
        html = None
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            disp = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disp:
                continue
            try:
                payload = part.get_payload(decode=True)
            except Exception:
                payload = None
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                text = payload.decode(charset, errors="replace")
            except Exception:
                text = payload.decode("utf-8", errors="replace")
            if ctype == "text/plain" and plain is None:
                plain = text
            elif ctype == "text/html" and html is None:
                html = text
        if plain is not None:
            return plain.strip()
        if html is not None:
            # Very lightweight HTML strip.
            txt = re.sub(r"<[^>]+>", "", html)
            return txt.strip()
        return ""
    try:
        payload = msg.get_payload(decode=True)
    except Exception:
        payload = None
    if payload is None:
        return ""
    charset = msg.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace").strip()
    except Exception:
        return payload.decode("utf-8", errors="replace").strip()


class ImapSmtpEmailProvider(EmailProvider):
    def __init__(self, *, config: dict, secret_ref: str):
        self._config = config or {}
        self._secret_ref = secret_ref or ""

    def _password(self) -> str:
        if not self._secret_ref:
            return ""
        return resolve_secret_ref(self._secret_ref) or ""

    def _imap(self) -> imaplib.IMAP4:
        host = str(self._config.get("imap_host") or "")
        port = int(self._config.get("imap_port") or 993)
        tls = bool(self._config.get("imap_tls", True))
        if tls:
            return imaplib.IMAP4_SSL(host, port)
        return imaplib.IMAP4(host, port)

    def _smtp(self) -> smtplib.SMTP:
        host = str(self._config.get("smtp_host") or "")
        port = int(self._config.get("smtp_port") or 587)
        tls = bool(self._config.get("smtp_tls", True))
        s = smtplib.SMTP(host, port, timeout=20)
        s.ehlo()
        if tls:
            ctx = ssl.create_default_context()
            s.starttls(context=ctx)
            s.ehlo()
        return s

    def test_connection(self) -> tuple[bool, str | None]:
        user = str(self._config.get("username") or "")
        pw = self._password()
        if not user or not pw:
            return False, "missing_credentials"
        try:
            im = self._imap()
            try:
                im.login(user, pw)
                im.select("INBOX")
            finally:
                try:
                    im.logout()
                except Exception:
                    pass
            # SMTP connect only (auth may be required, but not all providers require it at connect-time).
            s = self._smtp()
            try:
                s.login(user, pw)
            finally:
                try:
                    s.quit()
                except Exception:
                    pass
            return True, None
        except Exception as exc:
            return False, str(exc)

    def list_unread(self, *, since_ms: Optional[int], limit: int) -> list[EmailHeader]:
        user = str(self._config.get("username") or "")
        pw = self._password()
        if not user or not pw:
            return []
        im = self._imap()
        try:
            im.login(user, pw)
            im.select("INBOX")
            # Search unread.
            typ, data = im.search(None, "UNSEEN")
            if typ != "OK":
                return []
            ids = [x for x in (data[0] or b"").split() if x]
            ids = ids[-max(1, min(int(limit), 200)) :]
            out: list[EmailHeader] = []
            for mid in reversed(ids):
                typ2, msg_data = im.fetch(mid, "(BODY.PEEK[HEADER])")
                if typ2 != "OK" or not msg_data:
                    continue
                raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else None
                if not raw:
                    continue
                msg = email.message_from_bytes(raw)
                date_ms = _msg_date_ms(msg)
                if since_ms is not None and date_ms < int(since_ms):
                    continue
                subj = _decode_mime(str(msg.get("Subject") or ""))
                from_raw = _decode_mime(str(msg.get("From") or ""))
                from_name, from_addr = parseaddr(from_raw)
                out.append(
                    EmailHeader(
                        message_id=str(mid.decode("utf-8", errors="replace")),
                        from_email=from_addr or from_raw,
                        from_name=from_name or None,
                        subject=subj,
                        date_ms=date_ms,
                        snippet="",
                        importance="normal",
                    )
                )
            return out
        finally:
            try:
                im.logout()
            except Exception:
                pass

    def get_message(self, *, message_id: str) -> EmailMessage:
        user = str(self._config.get("username") or "")
        pw = self._password()
        if not user or not pw:
            raise ValueError("missing_credentials")
        im = self._imap()
        try:
            im.login(user, pw)
            im.select("INBOX")
            typ, data = im.fetch(message_id.encode("utf-8"), "(RFC822)")
            if typ != "OK" or not data:
                raise ValueError("MESSAGE_NOT_FOUND")
            raw = data[0][1] if isinstance(data[0], tuple) else None
            if not raw:
                raise ValueError("MESSAGE_NOT_FOUND")
            msg = email.message_from_bytes(raw)
            subject = _decode_mime(str(msg.get("Subject") or ""))
            from_raw = _decode_mime(str(msg.get("From") or ""))
            from_name, from_addr = parseaddr(from_raw)
            body_text = _extract_text_body(msg)
            md_from = f"{from_name} <{from_addr}>" if from_addr else from_raw
            md = f"**From:** {md_from}\n\n**Subject:** {subject}\n\n---\n\n{body_text}\n"
            return EmailMessage(
                message_id=str(message_id),
                from_email=from_addr or from_raw,
                from_name=from_name or None,
                to=[],
                cc=[],
                subject=subject,
                date_ms=_msg_date_ms(msg),
                body_text=body_text,
                body_md=md,
            )
        finally:
            try:
                im.logout()
            except Exception:
                pass

    def create_draft_reply(self, *, message_id: str, user_text: str) -> tuple[str, str, str]:
        msg = self.get_message(message_id=message_id)
        subject = msg.subject
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        body_md = (
            f"Hi,\n\n{(user_text or '').strip()}\n\n---\n\n"
            f"> On {msg.date_ms}, {msg.from_email} wrote:\n"
            + "\n".join([f"> {line}" for line in (msg.body_text or "").splitlines()][:20])
            + "\n"
        )
        return subject, body_md, "Rule-based formatting (no model)."

    def send(self, *, subject: str, body_text: str, to: list[str], cc: list[str] | None = None) -> SendResult:
        user = str(self._config.get("username") or "")
        pw = self._password()
        if not user or not pw:
            return SendResult(ok=False, error="missing_credentials")
        if not to:
            return SendResult(ok=False, error="missing_to")
        msg = email.message.EmailMessage()
        msg["From"] = user
        msg["To"] = ", ".join(to)
        if cc:
            msg["Cc"] = ", ".join(cc)
        msg["Subject"] = subject
        msg.set_content(body_text or "")
        try:
            s = self._smtp()
            try:
                s.login(user, pw)
                s.send_message(msg)
            finally:
                try:
                    s.quit()
                except Exception:
                    pass
            return SendResult(ok=True, provider_message_id=None)
        except Exception as exc:
            return SendResult(ok=False, error=str(exc))

    def supports_mark_read(self) -> bool:
        return True

    def mark_read(self, *, message_id: str) -> None:
        user = str(self._config.get("username") or "")
        pw = self._password()
        if not user or not pw:
            raise ValueError("missing_credentials")
        im = self._imap()
        try:
            im.login(user, pw)
            im.select("INBOX")
            # message_id is an IMAP message sequence as used by list_unread (MVP).
            im.store(str(message_id), "+FLAGS", "\\Seen")
        finally:
            try:
                im.logout()
            except Exception:
                pass
