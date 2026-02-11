from __future__ import annotations

import base64
import email.message
import json
import time
from typing import Optional

import requests

from octopusos.core.email.models import EmailHeader, EmailMessage, SendResult
from octopusos.core.email.providers.base import EmailProvider
from octopusos.store.timestamp_utils import now_ms
from octopusos.webui.secret_resolver import resolve_secret_ref
from octopusos.webui.secrets import SecretStore


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


class GmailOAuthEmailProvider(EmailProvider):
    """Gmail API provider using OAuth token bundle stored as secret_ref."""

    def __init__(self, *, config: dict, token_secret_ref: str):
        self._config = config or {}
        self._token_ref = token_secret_ref or ""

    def _token_bundle(self) -> dict:
        raw = resolve_secret_ref(self._token_ref) or ""
        if not raw:
            return {}
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    def _save_bundle(self, bundle: dict) -> None:
        if not self._token_ref:
            return
        try:
            SecretStore().set(self._token_ref, json.dumps(bundle, ensure_ascii=False))
        except Exception:
            pass

    def _access_token(self) -> str:
        b = self._token_bundle()
        token = str(b.get("access_token") or "").strip()
        exp = int(b.get("expires_at_ms") or 0)
        if token and exp and now_ms() < exp - 15_000:
            return token

        # Best-effort refresh if refresh_token exists.
        refresh = str(b.get("refresh_token") or "").strip()
        if not refresh:
            return token
        client_id = str(self._config.get("client_id") or "").strip()
        client_secret = str(self._config.get("client_secret") or "").strip()
        if not client_id:
            return token

        data = {
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh,
        }
        if client_secret:
            data["client_secret"] = client_secret
        resp = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=20)
        if resp.status_code >= 400:
            return token
        out = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if not isinstance(out, dict) or not out.get("access_token"):
            return token
        b["access_token"] = out.get("access_token")
        if out.get("expires_in"):
            b["expires_at_ms"] = int(now_ms() + int(out.get("expires_in")) * 1000)
        self._save_bundle(b)
        return str(b.get("access_token") or "").strip()

    def _headers(self) -> dict:
        tok = self._access_token()
        return {"Authorization": f"Bearer {tok}"} if tok else {}

    def test_connection(self) -> tuple[bool, str | None]:
        hdr = self._headers()
        if not hdr:
            return False, "missing_token"
        resp = requests.get("https://gmail.googleapis.com/gmail/v1/users/me/profile", headers=hdr, timeout=20)
        if resp.status_code >= 400:
            return False, f"http_{resp.status_code}"
        return True, None

    def list_unread(self, *, since_ms: Optional[int], limit: int) -> list[EmailHeader]:
        hdr = self._headers()
        if not hdr:
            return []
        lim = max(1, min(int(limit), 50))
        q = "is:unread"
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?{requests.compat.urlencode({'q': q, 'maxResults': lim})}"
        resp = requests.get(url, headers=hdr, timeout=20)
        if resp.status_code >= 400:
            return []
        payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        msgs = payload.get("messages", []) if isinstance(payload, dict) else []
        out: list[EmailHeader] = []
        for m in msgs or []:
            mid = str(m.get("id") or "").strip() if isinstance(m, dict) else ""
            if not mid:
                continue
            # Fetch metadata for subject/from/date/snippet
            meta_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}?format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date"
            r2 = requests.get(meta_url, headers=hdr, timeout=20)
            if r2.status_code >= 400:
                continue
            msg = r2.json() if r2.headers.get("content-type", "").startswith("application/json") else {}
            if not isinstance(msg, dict):
                continue
            snippet = str(msg.get("snippet") or "")
            headers = msg.get("payload", {}).get("headers", []) if isinstance(msg.get("payload"), dict) else []
            hv = {str(h.get("name") or ""): str(h.get("value") or "") for h in headers if isinstance(h, dict)}
            subj = hv.get("Subject", "")
            frm = hv.get("From", "")
            date_ms = now_ms()
            out.append(
                EmailHeader(
                    message_id=mid,
                    from_email=frm,
                    from_name=None,
                    subject=subj,
                    date_ms=int(date_ms),
                    snippet=snippet,
                    importance="normal",
                )
            )
        return out

    def get_message(self, *, message_id: str) -> EmailMessage:
        hdr = self._headers()
        if not hdr:
            raise ValueError("missing_token")
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}?format=full"
        resp = requests.get(url, headers=hdr, timeout=20)
        if resp.status_code >= 400:
            raise ValueError("MESSAGE_NOT_FOUND")
        msg = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if not isinstance(msg, dict):
            raise ValueError("MESSAGE_NOT_FOUND")
        snippet = str(msg.get("snippet") or "")
        md = f"**Message:** `{message_id}`\n\n---\n\n{snippet}\n"
        return EmailMessage(
            message_id=str(message_id),
            from_email="",
            from_name=None,
            to=[],
            cc=[],
            subject="",
            date_ms=now_ms(),
            body_text=snippet,
            body_md=md,
        )

    def create_draft_reply(self, *, message_id: str, user_text: str) -> tuple[str, str, str]:
        msg = self.get_message(message_id=message_id)
        subject = msg.subject or "(no subject)"
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        body_md = f"Hi,\n\n{(user_text or '').strip()}\n\n---\n\n> (quoted)\n"
        return subject, body_md, "Rule-based formatting (no model)."

    def send(self, *, subject: str, body_text: str, to: list[str], cc: list[str] | None = None) -> SendResult:
        hdr = self._headers()
        if not hdr:
            return SendResult(ok=False, error="missing_token")
        if not to:
            return SendResult(ok=False, error="missing_to")
        msg = email.message.EmailMessage()
        msg["To"] = ", ".join(to)
        if cc:
            msg["Cc"] = ", ".join(cc)
        msg["Subject"] = subject
        msg.set_content(body_text or "")
        raw = _b64url(msg.as_bytes())
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        resp = requests.post(url, headers={**hdr, "Content-Type": "application/json"}, json={"raw": raw}, timeout=20)
        if resp.status_code >= 400:
            return SendResult(ok=False, error=f"http_{resp.status_code}")
        out = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        mid = str(out.get("id") or "") if isinstance(out, dict) else ""
        return SendResult(ok=True, provider_message_id=mid or None)

    def supports_mark_read(self) -> bool:
        return True

    def mark_read(self, *, message_id: str) -> None:
        hdr = self._headers()
        if not hdr:
            raise ValueError("missing_token")
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify"
        resp = requests.post(url, headers={**hdr, "Content-Type": "application/json"}, json={"removeLabelIds": ["UNREAD"]}, timeout=20)
        if resp.status_code >= 400:
            raise ValueError(f"http_{resp.status_code}")

