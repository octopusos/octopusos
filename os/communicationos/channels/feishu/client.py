"""Feishu/Lark OpenAPI client (minimal).

Only supports:
- tenant_access_token/internal
- send message to chat_id

This client is bridge-only and contains no LLM logic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class _TokenCache:
    token: str = ""
    expires_at_s: float = 0.0

    def valid(self) -> bool:
        # keep a small margin to avoid edge expiry
        return bool(self.token) and time.time() < (self.expires_at_s - 30)


class FeishuClient:
    def __init__(self, *, app_id: str, app_secret: str, base_url: str = "https://open.feishu.cn"):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = base_url.rstrip("/")
        self._cache = _TokenCache()

    def _get_tenant_access_token(self) -> str:
        if self._cache.valid():
            return self._cache.token

        url = f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal"
        resp = httpx.post(url, json={"app_id": self.app_id, "app_secret": self.app_secret}, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        if int(data.get("code", 0)) != 0:
            raise RuntimeError(f"feishu_token_failed:{data.get('msg') or data}")

        token = str(data.get("tenant_access_token") or "")
        expire = int(data.get("expire") or 0)
        if not token:
            raise RuntimeError("feishu_token_missing")
        self._cache.token = token
        self._cache.expires_at_s = time.time() + max(0, expire)
        return token

    def send_text_to_chat(self, *, chat_id: str, text: str) -> None:
        token = self._get_tenant_access_token()
        url = f"{self.base_url}/open-apis/im/v1/messages"
        params = {"receive_id_type": "chat_id"}
        payload = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": {"text": text},
        }
        headers = {"Authorization": f"Bearer {token}"}
        resp = httpx.post(url, params=params, json=payload, headers=headers, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        if int(data.get("code", 0)) != 0:
            raise RuntimeError(f"feishu_send_failed:{data.get('msg') or data}")

