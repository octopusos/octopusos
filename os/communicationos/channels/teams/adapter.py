"""Microsoft Teams channel adapter.

This adapter handles:
- inbound Teams activity webhook parsing to InboundMessage
- outbound text replies via Bot Framework Connector API
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import socket
import email.utils
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError
from urllib import parse, request

from octopusos.communicationos.models import InboundMessage, MessageType, OutboundMessage
from octopusos.core.time import utc_now

logger = logging.getLogger(__name__)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _retry_after_seconds(exc: HTTPError) -> float:
    try:
        headers = getattr(exc, "headers", None)
        if not headers:
            return 0.0
        raw = str(headers.get("Retry-After") or "").strip()
        if not raw:
            return 0.0
        if raw.isdigit():
            return max(float(raw), 0.0)
        dt = email.utils.parsedate_to_datetime(raw)
        if dt is None:
            return 0.0
        delay = dt.timestamp() - time.time()
        return max(delay, 0.0)
    except Exception:
        return 0.0


class TeamsAdapter:
    def __init__(
        self,
        *,
        channel_id: str,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        bot_app_id: Optional[str] = None,
        message_bus: Any = None,
    ):
        self.channel_id = channel_id
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.bot_app_id = bot_app_id or client_id
        self.message_bus = message_bus

        self._state = "stopped"
        self._detail = ""
        self._last_event_ts_ms = _now_ms()

        # conversation_key -> conversation reference for replies
        self._conversation_refs: Dict[str, Dict[str, str]] = {}
        self._refs_lock = threading.RLock()

        # Bot Framework access token cache
        self._token_lock = threading.RLock()
        self._token: Optional[str] = None
        self._token_expire_at_ms: int = 0

    def get_channel_id(self) -> str:
        return self.channel_id

    def start(self) -> None:
        self._state = "ready"
        self._detail = ""
        self._last_event_ts_ms = _now_ms()

    def stop(self) -> None:
        self._state = "stopped"
        self._detail = ""
        self._last_event_ts_ms = _now_ms()

    def get_status(self) -> Dict[str, Any]:
        with self._refs_lock:
            refs = len(self._conversation_refs)
        return {
            "channel_id": self.channel_id,
            "state": self._state,
            "detail": self._detail,
            "last_event_ts_ms": self._last_event_ts_ms,
            "cached_conversations": refs,
        }

    def handle_webhook(self, *, headers: Dict[str, str], body_bytes: bytes) -> Tuple[int, Dict[str, Any]]:
        auth = str(headers.get("authorization") or "").strip()
        if not auth.lower().startswith("bearer "):
            raise PermissionError("missing_authorization")

        try:
            activity = json.loads(body_bytes.decode("utf-8") or "{}")
        except Exception as exc:
            raise ValueError(f"invalid_json:{exc}") from exc

        if not isinstance(activity, dict):
            return 200, {"ok": True}

        activity_type = str(activity.get("type") or "").strip().lower()
        self._last_event_ts_ms = _now_ms()

        # Only message activities are mapped to chat.
        if activity_type != "message":
            return 200, {"ok": True}

        from_obj = activity.get("from") if isinstance(activity.get("from"), dict) else {}
        # Bot loop protection.
        if str(from_obj.get("id") or "").strip() == str(self.bot_app_id).strip():
            return 200, {"ok": True}
        if str(from_obj.get("role") or "").strip().lower() == "bot":
            return 200, {"ok": True}

        conv_obj = activity.get("conversation") if isinstance(activity.get("conversation"), dict) else {}
        recipient_obj = activity.get("recipient") if isinstance(activity.get("recipient"), dict) else {}
        conversation_id = str(conv_obj.get("id") or "").strip()
        service_url = str(activity.get("serviceUrl") or "").strip()
        bot_channel_id = str(recipient_obj.get("id") or "").strip()
        message_id = str(activity.get("id") or f"teams_{_now_ms()}")
        text = str(activity.get("text") or "").strip()
        if not conversation_id or not text:
            return 200, {"ok": True}
        logger.info(
            "teams_inbound_trace message_id=%s conversation_id=%s service_url=%s text_len=%d",
            message_id,
            conversation_id[:72],
            service_url,
            len(text),
        )

        user_key = (
            str(from_obj.get("aadObjectId") or "").strip()
            or str(from_obj.get("id") or "").strip()
            or "teams-user"
        )

        if service_url:
            with self._refs_lock:
                self._conversation_refs[conversation_id] = {
                    "service_url": service_url,
                    "conversation_id": conversation_id,
                    "bot_channel_id": bot_channel_id,
                }

        inbound = InboundMessage(
            channel_id=self.channel_id,
            user_key=user_key,
            conversation_key=conversation_id,
            message_id=message_id,
            timestamp=utc_now(),
            type=MessageType.TEXT,
            text=text,
            raw=activity,
            metadata={
                "platform": "teams",
                "service_url": service_url,
                "teams_message_id": message_id,
                "teams_conversation_id": conversation_id,
            },
        )

        if self.message_bus:
            try:
                loop = asyncio.get_running_loop()
                loop.call_soon_threadsafe(lambda: asyncio.create_task(self.message_bus.process_inbound(inbound)))
            except RuntimeError:
                threading.Thread(
                    target=lambda: asyncio.run(self.message_bus.process_inbound(inbound)),
                    daemon=True,
                    name="teams-inbound-fallback",
                ).start()

        return 200, {"ok": True}

    def send_message(self, message: OutboundMessage) -> bool:
        conversation_id = str(message.conversation_key or "").strip()
        if not conversation_id:
            raise ValueError("missing_conversation_key")
        text = str(message.text or "").strip()
        if not text:
            return False

        with self._refs_lock:
            ref = dict(self._conversation_refs.get(conversation_id) or {})
        service_url = str(ref.get("service_url") or "").strip()
        if not service_url:
            raise ValueError("missing_service_url_for_conversation")

        token = self._get_bot_token(prefer_tenant=False)
        url = f"{service_url.rstrip('/')}/v3/conversations/{parse.quote(conversation_id, safe='')}/activities"
        # Bot Framework expects sender identity on outbound activities.
        from_id = str(ref.get("bot_channel_id") or self.bot_app_id or self.client_id).strip()
        payload = {
            "type": "message",
            "text": text,
            "from": {"id": from_id},
        }
        logger.info(
            "teams_send_trace conversation_id=%s service_url=%s url=%s text_len=%d",
            conversation_id[:48],
            service_url,
            url,
            len(text),
        )
        # Teams Connector occasionally responds slowly; retry transient timeouts.
        # If connector returns 401, refresh token from alternate issuer and retry once.
        for auth_round in range(2):
            for attempt in range(3):
                try:
                    code, _ = self._http_post_json(url=url, payload=payload, bearer_token=token)
                    return code in (200, 201, 202)
                except HTTPError as exc:
                    if exc.code == 401 and auth_round == 0:
                        prefer_tenant = "webchat.botframework.com" in service_url.lower()
                        token = self._get_bot_token(force_refresh=True, prefer_tenant=prefer_tenant)
                        logger.warning(
                            "teams_send_auth_retry code=401 auth_round=%d prefer_tenant=%s url=%s",
                            auth_round + 1,
                            str(prefer_tenant).lower(),
                            url,
                        )
                        break
                    # Retry only transient statuses.
                    if exc.code not in (408, 429, 500, 502, 503, 504) or attempt >= 2:
                        raise
                    delay = _retry_after_seconds(exc)
                    if delay <= 0:
                        # Teams 429 usually needs a longer cool-down window.
                        delay = 10.0 * (attempt + 1) if exc.code == 429 else 1.5 * (attempt + 1)
                    logger.warning(
                        "teams_send_http_retryable code=%d attempt=%d delay=%.2fs url=%s",
                        exc.code,
                        attempt + 1,
                        delay,
                        url,
                    )
                    time.sleep(delay)
                    continue
                except TimeoutError:
                    if attempt >= 2:
                        raise
                    logger.warning("teams_send_timeout attempt=%d url=%s", attempt + 1, url)
                except socket.timeout:
                    if attempt >= 2:
                        raise
                    logger.warning("teams_send_socket_timeout attempt=%d url=%s", attempt + 1, url)
                except Exception:
                    if attempt >= 2:
                        raise
                    logger.warning("teams_send_retryable_error attempt=%d url=%s", attempt + 1, url, exc_info=True)
                time.sleep(0.8 * (attempt + 1))
            else:
                continue
            continue
        return False

    def _get_bot_token(self, *, force_refresh: bool = False, prefer_tenant: bool = False) -> str:
        now = _now_ms()
        with self._token_lock:
            if (not force_refresh) and self._token and now < self._token_expire_at_ms:
                return self._token

            form = parse.urlencode(
                {
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "https://api.botframework.com/.default",
                }
            ).encode("utf-8")

            tenant = str(self.tenant_id or "").strip()
            tenant_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token" if tenant else ""
            bf_url = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
            if prefer_tenant and tenant_url:
                token_urls = [tenant_url, bf_url]
            else:
                token_urls = [bf_url] + ([tenant_url] if tenant_url else [])

            data: Dict[str, Any] = {}
            last_error: Optional[str] = None
            for token_url in token_urls:
                req = request.Request(
                    token_url,
                    data=form,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                try:
                    with request.urlopen(req, timeout=20) as resp:
                        body = resp.read().decode("utf-8")
                        data = json.loads(body or "{}")
                    access_token = str(data.get("access_token") or "").strip()
                    if access_token:
                        expires_in = int(data.get("expires_in") or 3600)
                        # Keep 60s safety margin.
                        self._token = access_token
                        self._token_expire_at_ms = now + max((expires_in - 60), 60) * 1000
                        return access_token
                    last_error = f"empty_access_token:{token_url}"
                except HTTPError as exc:
                    last_error = f"http_{exc.code}:{token_url}"
                except Exception as exc:
                    last_error = f"{exc}:{token_url}"
                    continue

            raise ValueError(f"failed_to_get_bot_token:{last_error or 'unknown'}")

    def _http_post_json(self, *, url: str, payload: Dict[str, Any], bearer_token: str) -> Tuple[int, Dict[str, Any]]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {bearer_token}",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=45) as resp:
                code = int(resp.getcode() or 0)
                raw = resp.read().decode("utf-8")
                try:
                    data = json.loads(raw or "{}")
                except Exception:
                    data = {}
                return code, data
        except HTTPError as exc:
            error_body = ""
            try:
                error_body = (exc.read() or b"").decode("utf-8", errors="replace")
            except Exception:
                error_body = ""
            logger.error(
                "teams_send_http_error code=%s url=%s body=%s",
                exc.code,
                url,
                error_body[:1000],
            )
            raise
