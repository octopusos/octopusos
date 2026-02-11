from __future__ import annotations

import json
from typing import Optional

from octopusos.core.email.draft_store import EmailDraftStore
from octopusos.core.email.filtering import apply_classification, load_filter_config
from octopusos.core.email.instance_store import EmailInstanceStore
from octopusos.core.email.models import EmailDraft, EmailHeader, EmailMessage, SendResult
from octopusos.core.email.providers.base import EmailProvider
from octopusos.core.email.providers.imap_smtp import ImapSmtpEmailProvider
from octopusos.core.email.providers.gmail_oauth import GmailOAuthEmailProvider
from octopusos.core.email.providers.outlook_oauth import OutlookOAuthEmailProvider
from octopusos.core.email.providers.mock import MockEmailProvider
from octopusos.store.timestamp_utils import now_ms


class EmailAdapter:
    def __init__(self) -> None:
        self._instances = EmailInstanceStore()
        self._drafts = EmailDraftStore()

    def list_instances(self):
        return self._instances.list()

    def _provider_for_instance(self, instance_id: str) -> tuple[EmailProvider, str]:
        inst = self._instances.get(instance_id=instance_id)
        if not inst:
            raise ValueError("INSTANCE_NOT_FOUND")
        provider_type = str(inst.provider_type or "").strip()
        cfg = {}
        try:
            cfg = json.loads(inst.config_json or "{}")
        except Exception:
            cfg = {}
        if provider_type == "imap_smtp":
            return ImapSmtpEmailProvider(config=cfg, secret_ref=inst.secret_ref), inst.config_json
        if provider_type == "gmail_oauth":
            return GmailOAuthEmailProvider(config=cfg, token_secret_ref=inst.secret_ref), inst.config_json
        if provider_type == "outlook_oauth":
            return OutlookOAuthEmailProvider(config=cfg, token_secret_ref=inst.secret_ref), inst.config_json
        if provider_type == "mock":
            return MockEmailProvider(config_json=inst.config_json), inst.config_json
        raise ValueError("PROVIDER_NOT_SUPPORTED")

    def test_instance(self, *, instance_id: str) -> tuple[bool, str | None]:
        provider, _ = self._provider_for_instance(instance_id)
        return provider.test_connection()

    def list_unread(self, *, instance_id: str, since_ms: Optional[int], limit: int) -> list[EmailHeader]:
        provider, cfg_json = self._provider_for_instance(instance_id)
        headers = provider.list_unread(since_ms=since_ms, limit=limit)
        cfg = load_filter_config(cfg_json)
        return apply_classification(headers, cfg, instance_id=instance_id)

    def get_message(self, *, instance_id: str, message_id: str) -> EmailMessage:
        provider, _ = self._provider_for_instance(instance_id)
        return provider.get_message(message_id=message_id)

    def create_draft_reply(self, *, instance_id: str, message_id: str, user_text: str) -> tuple[EmailDraft, str]:
        provider, _ = self._provider_for_instance(instance_id)
        subject, body_md, reasoning = provider.create_draft_reply(message_id=message_id, user_text=user_text)
        row = self._drafts.create(instance_id=instance_id, message_id=message_id, subject=subject, body_md=body_md, ttl_ms=10 * 60_000)
        draft = EmailDraft(
            draft_id=row.draft_id,
            instance_id=row.instance_id,
            message_id=row.message_id,
            subject=row.subject,
            body_md=row.body_md,
            confirm_token=row.confirm_token,
            expires_at_ms=row.expires_at_ms,
        )
        return draft, reasoning

    def send_draft(self, *, draft_id: str, confirm_token: str) -> SendResult:
        row = self._drafts.get(draft_id=draft_id)
        if not row:
            return SendResult(ok=False, error="DRAFT_NOT_FOUND")
        if row.status != "draft":
            return SendResult(ok=False, error="DRAFT_NOT_SENDABLE")
        if not confirm_token or confirm_token != row.confirm_token:
            return SendResult(ok=False, error="CONFIRM_TOKEN_MISMATCH")
        if now_ms() > int(row.expires_at_ms):
            return SendResult(ok=False, error="DRAFT_EXPIRED")

        provider, _ = self._provider_for_instance(row.instance_id)
        # For MVP, we send back to the original sender only.
        msg = provider.get_message(message_id=row.message_id)
        to = [msg.from_email] if msg.from_email else []
        # Strip markdown for plain text fallback. Keep it readable.
        body_text = row.body_md.replace("**", "").replace("`", "")
        result = provider.send(subject=row.subject, body_text=body_text, to=to, cc=[])
        if result.ok:
            self._drafts.mark_sent(draft_id=row.draft_id)
        return result

    def supports_mark_read(self, *, instance_id: str) -> bool:
        provider, _ = self._provider_for_instance(instance_id)
        try:
            return bool(provider.supports_mark_read())
        except Exception:
            return False

    def mark_read(self, *, instance_id: str, message_id: str) -> None:
        provider, _ = self._provider_for_instance(instance_id)
        if not provider.supports_mark_read():
            raise ValueError("NOT_SUPPORTED")
        provider.mark_read(message_id=message_id)
