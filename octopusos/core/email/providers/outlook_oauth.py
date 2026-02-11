from __future__ import annotations

import email.message
import json
from typing import Optional

import requests

from octopusos.core.email.models import EmailHeader, EmailMessage, SendResult
from octopusos.core.email.providers.base import EmailProvider
from octopusos.store.timestamp_utils import now_ms
from octopusos.webui.secret_resolver import resolve_secret_ref
from octopusos.webui.secrets import SecretStore


class OutlookOAuthEmailProvider(EmailProvider):
    """Microsoft Graph provider using OAuth token bundle stored as secret_ref."""

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

        refresh = str(b.get("refresh_token") or "").strip()
        if not refresh:
            return token
        client_id = str(self._config.get("client_id") or "").strip()
        tenant = str(self._config.get("tenant") or "common").strip()
        client_secret = str(self._config.get("client_secret") or "").strip()
        if not client_id:
            return token
        data = {
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "scope": str(self._config.get("scopes") or "openid profile offline_access Mail.Read Mail.Send"),
        }
        if client_secret:
            data["client_secret"] = client_secret
        resp = requests.post(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", data=data, timeout=20)
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
        resp = requests.get("https://graph.microsoft.com/v1.0/me", headers=hdr, timeout=20)
        if resp.status_code >= 400:
            return False, f"http_{resp.status_code}"
        return True, None

    def list_unread(self, *, since_ms: Optional[int], limit: int) -> list[EmailHeader]:
        hdr = self._headers()
        if not hdr:
            return []
        lim = max(1, min(int(limit), 50))
        url = f"https://graph.microsoft.com/v1.0/me/mailFolders/Inbox/messages?$filter=isRead%20eq%20false&$top={lim}"
        resp = requests.get(url, headers=hdr, timeout=20)
        if resp.status_code >= 400:
            return []
        payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        items = payload.get("value", []) if isinstance(payload, dict) else []
        out: list[EmailHeader] = []
        for it in items or []:
            if not isinstance(it, dict):
                continue
            mid = str(it.get("id") or "")
            subj = str(it.get("subject") or "")
            frm = it.get("from", {}).get("emailAddress", {}) if isinstance(it.get("from"), dict) else {}
            addr = str(frm.get("address") or "")
            out.append(
                EmailHeader(
                    message_id=mid,
                    from_email=addr,
                    from_name=None,
                    subject=subj,
                    date_ms=now_ms(),
                    snippet=str(it.get("bodyPreview") or ""),
                    importance="normal",
                )
            )
        return out

    def get_message(self, *, message_id: str) -> EmailMessage:
        hdr = self._headers()
        if not hdr:
            raise ValueError("missing_token")
        url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}"
        resp = requests.get(url, headers=hdr, timeout=20)
        if resp.status_code >= 400:
            raise ValueError("MESSAGE_NOT_FOUND")
        it = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if not isinstance(it, dict):
            raise ValueError("MESSAGE_NOT_FOUND")
        subj = str(it.get("subject") or "")
        preview = str(it.get("bodyPreview") or "")
        md = f"**Message:** `{message_id}`\n\n**Subject:** {subj}\n\n---\n\n{preview}\n"
        return EmailMessage(
            message_id=str(message_id),
            from_email="",
            from_name=None,
            to=[],
            cc=[],
            subject=subj,
            date_ms=now_ms(),
            body_text=preview,
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
        url = "https://graph.microsoft.com/v1.0/me/sendMail"
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body_text or ""},
                "toRecipients": [{"emailAddress": {"address": addr}} for addr in to],
                "ccRecipients": [{"emailAddress": {"address": addr}} for addr in (cc or [])],
            },
            "saveToSentItems": True,
        }
        resp = requests.post(url, headers={**hdr, "Content-Type": "application/json"}, json=payload, timeout=20)
        if resp.status_code >= 400:
            return SendResult(ok=False, error=f"http_{resp.status_code}")
        return SendResult(ok=True, provider_message_id=None)

    def supports_mark_read(self) -> bool:
        return True

    def mark_read(self, *, message_id: str) -> None:
        hdr = self._headers()
        if not hdr:
            raise ValueError("missing_token")
        url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}"
        resp = requests.patch(url, headers={**hdr, "Content-Type": "application/json"}, json={"isRead": True}, timeout=20)
        if resp.status_code >= 400:
            raise ValueError(f"http_{resp.status_code}")

