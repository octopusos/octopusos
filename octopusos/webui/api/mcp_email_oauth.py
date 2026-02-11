"""OAuth endpoints for MCP Email instances (PKCE + loopback/webui callback).

This is instance-scoped:
- /api/mcp/email/{instance_id}/oauth/start
- /api/mcp/email/oauth/callback
- /api/mcp/email/{instance_id}/oauth/status
- /api/mcp/email/{instance_id}/oauth/disconnect
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from octopusos.core.email.instance_store import EmailInstanceStore
from octopusos.core.email.oauth_state_store import EmailOAuthStateStore
from octopusos.store.timestamp_utils import now_ms
from octopusos.webui.secret_resolver import is_secret_ref, secret_exists
from octopusos.webui.secrets import SecretStore


def _inject_deprecation_headers(response: Response) -> None:
    # Compatibility layer: prefer /api/channels/email for Channel-first semantics.
    response.headers.setdefault("X-OctopusOS-Deprecated", "use /api/channels/email")
    response.headers.setdefault("X-OctopusOS-Deprecated-Since", "2026-02-10")
    response.headers.setdefault("Link", '</api/channels/email>; rel="successor-version"')


router = APIRouter(
    prefix="/api/mcp/email",
    tags=["mcp-email-oauth"],
    dependencies=[Depends(_inject_deprecation_headers)],
)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _pkce_challenge(verifier: str) -> str:
    return _b64url(hashlib.sha256(verifier.encode("utf-8")).digest())


def _get_cfg(inst) -> dict:
    try:
        cfg = json.loads(inst.config_json or "{}")
    except Exception:
        cfg = {}
    return cfg if isinstance(cfg, dict) else {}


def _require_provider(inst) -> str:
    pt = str(inst.provider_type or "").strip()
    if pt not in {"gmail_oauth", "outlook_oauth"}:
        raise HTTPException(status_code=400, detail="provider not oauth")
    return pt


def _scopes_for_provider(provider_type: str, cfg: dict) -> list[str]:
    raw = cfg.get("scopes")
    if isinstance(raw, list) and raw:
        return [str(x) for x in raw if str(x).strip()]

    if provider_type == "gmail_oauth":
        # Default minimal: read + send.
        return [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
        ]
    # Outlook default: read + send + offline access.
    return ["openid", "profile", "offline_access", "User.Read", "Mail.Read", "Mail.Send"]


def _redirect_uri(cfg: dict) -> str:
    uri = str(cfg.get("redirect_uri") or "").strip()
    if not uri:
        raise HTTPException(status_code=400, detail="missing redirect_uri in instance config")
    return uri


def _client_id(cfg: dict) -> str:
    cid = str(cfg.get("client_id") or "").strip()
    if not cid:
        raise HTTPException(status_code=400, detail="missing client_id in instance config")
    return cid


def _client_secret(cfg: dict) -> str:
    # Optional: allow secret_ref in config.
    ref = str(cfg.get("client_secret_ref") or "").strip()
    if ref and is_secret_ref(ref) and secret_exists(ref):
        return SecretStore().get(ref) or ""
    return str(cfg.get("client_secret") or "").strip()


def _gmail_auth_url(*, client_id: str, redirect_uri: str, scopes: list[str], state: str, code_challenge: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def _outlook_auth_url(*, tenant: str, client_id: str, redirect_uri: str, scopes: list[str], state: str, code_challenge: str) -> str:
    t = (tenant or "common").strip()
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "response_mode": "query",
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"https://login.microsoftonline.com/{t}/oauth2/v2.0/authorize?" + urlencode(params)


def _token_secret_ref(instance_id: str) -> str:
    return f"secret://email/oauth/{instance_id}/token"


@router.get("/{instance_id}/oauth/start")
def oauth_start(instance_id: str) -> Dict[str, Any]:
    inst = EmailInstanceStore().get(instance_id=instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="instance not found")
    provider_type = _require_provider(inst)
    cfg = _get_cfg(inst)

    client_id = _client_id(cfg)
    redirect_uri = _redirect_uri(cfg)
    scopes = _scopes_for_provider(provider_type, cfg)

    verifier = _b64url(secrets.token_bytes(32))
    challenge = _pkce_challenge(verifier)

    # Persist one-time state.
    state_store = EmailOAuthStateStore()
    st = state_store.create(
        instance_id=inst.instance_id,
        provider_type=provider_type,
        code_verifier=verifier,
        redirect_uri=redirect_uri,
        scopes=" ".join(scopes),
        ttl_ms=10 * 60_000,
        meta_obj={"provider_type": provider_type},
    )

    if provider_type == "gmail_oauth":
        url = _gmail_auth_url(client_id=client_id, redirect_uri=redirect_uri, scopes=scopes, state=st.state, code_challenge=challenge)
    else:
        tenant = str(cfg.get("tenant") or "common")
        url = _outlook_auth_url(
            tenant=tenant,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scopes=scopes,
            state=st.state,
            code_challenge=challenge,
        )
    return {"ok": True, "auth_url": url, "state": st.state, "provider_type": provider_type, "redirect_uri": redirect_uri, "scopes": scopes}


@router.get("/oauth/callback")
def oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> Dict[str, Any]:
    if error:
        raise HTTPException(status_code=400, detail={"error": error, "error_description": error_description})
    if not state or not code:
        raise HTTPException(status_code=400, detail="missing code/state")

    st = EmailOAuthStateStore().consume(state=state)
    if not st:
        raise HTTPException(status_code=400, detail="invalid/expired state")

    inst = EmailInstanceStore().get(instance_id=st.instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="instance not found")
    provider_type = _require_provider(inst)
    cfg = _get_cfg(inst)

    client_id = _client_id(cfg)
    redirect_uri = st.redirect_uri
    scopes = st.scopes
    client_secret = _client_secret(cfg)

    if provider_type == "gmail_oauth":
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": client_id,
            "code": code,
            "code_verifier": st.code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        if client_secret:
            data["client_secret"] = client_secret
    else:
        tenant = str(cfg.get("tenant") or "common")
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        data = {
            "client_id": client_id,
            "scope": scopes,
            "code": code,
            "code_verifier": st.code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        if client_secret:
            data["client_secret"] = client_secret

    resp = requests.post(token_url, data=data, timeout=20)
    if resp.status_code >= 400:
        raise HTTPException(status_code=400, detail={"error": "token_exchange_failed", "status": resp.status_code, "body": resp.text[:400]})
    token = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if not isinstance(token, dict) or not token.get("access_token"):
        raise HTTPException(status_code=400, detail={"error": "token_invalid", "body": token})

    # Persist token bundle as encrypted secret.
    token_ref = _token_secret_ref(inst.instance_id)
    SecretStore().set(token_ref, json.dumps(token, ensure_ascii=False))
    EmailInstanceStore().update_secret_ref(instance_id=inst.instance_id, secret_ref=token_ref)

    return {"ok": True, "instance_id": inst.instance_id, "provider_type": provider_type, "connected": True}


@router.get("/{instance_id}/oauth/status")
def oauth_status(instance_id: str) -> Dict[str, Any]:
    inst = EmailInstanceStore().get(instance_id=instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="instance not found")
    provider_type = str(inst.provider_type or "").strip()
    if provider_type not in {"gmail_oauth", "outlook_oauth"}:
        return {"ok": True, "provider_type": provider_type, "connected": False}
    connected = bool(inst.secret_ref) and is_secret_ref(inst.secret_ref) and secret_exists(inst.secret_ref)
    return {"ok": True, "instance_id": inst.instance_id, "provider_type": provider_type, "connected": connected, "token_ref": inst.secret_ref if connected else ""}


@router.post("/{instance_id}/oauth/disconnect")
def oauth_disconnect(instance_id: str) -> Dict[str, Any]:
    inst = EmailInstanceStore().get(instance_id=instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="instance not found")
    if inst.secret_ref and is_secret_ref(inst.secret_ref):
        try:
            SecretStore().delete(inst.secret_ref)
        except Exception:
            pass
    EmailInstanceStore().update_secret_ref(instance_id=inst.instance_id, secret_ref="")
    return {"ok": True, "disconnected": True}
