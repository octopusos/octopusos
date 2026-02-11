"""ConnectorOS compatibility APIs for connector assets and endpoint profiles."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import APIRouter, Body, Header, HTTPException, Query
import yaml

from octopusos.connectoros.core import ConnectorService, ConnectorStore

router = APIRouter(prefix="/api/compat/connectors", tags=["compat"])
_store = ConnectorStore()
_service = ConnectorService(_store)


def _require_admin_token(token: Optional[str]) -> str:
    expected = os.getenv("OCTOPUSOS_ADMIN_TOKEN", "").strip()
    incoming = (token or "").strip()
    if not expected:
        # Missing server-side admin token should not surface as 5xx in smoke/e2e.
        raise HTTPException(status_code=401, detail="Admin token not configured")
    if not incoming:
        raise HTTPException(status_code=401, detail="Admin token required")
    if incoming != expected:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return "admin"


def _import_openapi_spec(connector_id: str, spec: Dict[str, Any], *, source_type: str, source_ref: Optional[str]) -> Dict[str, Any]:
    paths = spec.get("paths") if isinstance(spec.get("paths"), dict) else {}
    before = {
        str(ep.get("endpoint_key") or ""): ep
        for ep in _store.list_endpoints(connector_id, include_disabled=True)
    }
    added = 0
    updated = 0
    touched_keys: set[str] = set()
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            method_u = str(method or "").upper()
            if method_u not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            op_dict = op if isinstance(op, dict) else {}
            operation_id = str(op_dict.get("operationId") or "").strip()
            endpoint_key = operation_id or f"{method_u.lower()}:{str(path).strip('/')}".replace("/", "_")
            touched_keys.add(endpoint_key)
            _store.upsert_endpoint(
                connector_id,
                {
                    "endpoint_key": endpoint_key,
                    "name": str(op_dict.get("summary") or endpoint_key),
                    "capability_id": "generic",
                    "item_id": "query",
                    "method": method_u,
                    "path": str(path),
                    "tags": op_dict.get("tags") if isinstance(op_dict.get("tags"), list) else [],
                    "enabled": True,
                },
            )
            if endpoint_key in before:
                updated += 1
            else:
                added += 1
    summary = {
        "added": added,
        "updated": updated,
        "deleted": 0,
        "endpoint_count": len(_store.list_endpoints(connector_id, include_disabled=True)),
    }
    import_version = _store.save_import_version(
        connector_id=connector_id,
        source_type=source_type,
        source_ref=source_ref,
        summary=summary,
        spec_obj=spec,
    )
    return {
        "summary": summary,
        "import_version_id": import_version.get("id"),
    }


def _load_openapi_text(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="openapi spec is empty")
    try:
        parsed = json.loads(text)
    except Exception:
        try:
            parsed = yaml.safe_load(text)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"invalid openapi payload: {exc}")
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="openapi spec must be an object")
    return parsed


def _render_template(template: str, params: Dict[str, Any]) -> str:
    out = template
    for k, v in params.items():
        out = out.replace(f"{{{k}}}", str(v))
    return out


@router.get("")
async def list_connectors(include_disabled: bool = Query(default=True)):
    return {"ok": True, "data": _store.list_connectors(include_disabled=include_disabled)}


@router.post("")
async def upsert_connector(
    payload: Dict[str, Any] = Body(...),
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _require_admin_token(admin_token)
    try:
        item = _store.upsert_connector(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True, "data": item}


@router.get("/{connector_id}")
async def get_connector(connector_id: str):
    item = _store.get_connector(connector_id, mask_secret=True)
    if not item:
        raise HTTPException(status_code=404, detail="Connector not found")
    return {"ok": True, "data": item}


@router.get("/{connector_id}/import-versions")
async def list_import_versions(connector_id: str, limit: int = Query(default=20, ge=1, le=200)):
    connector = _store.get_connector(connector_id, mask_secret=True)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    return {"ok": True, "data": _store.list_import_versions(connector_id, limit=limit)}


@router.delete("/{connector_id}")
async def delete_connector(
    connector_id: str,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _require_admin_token(admin_token)
    try:
        ok = _store.delete_connector(connector_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if not ok:
        raise HTTPException(status_code=404, detail="Connector not found")
    return {"ok": True, "data": {"connector_id": connector_id}}


@router.post("/import/openapi")
async def import_openapi_deprecated(
    payload: Dict[str, Any] = Body(...),
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _require_admin_token(admin_token)
    raise HTTPException(
        status_code=410,
        detail="Deprecated route. Use POST /api/compat/connectors/{connector_id}/import/openapi",
    )


@router.post("/import/openapi-url")
async def import_openapi_url_deprecated(
    payload: Dict[str, Any] = Body(...),
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _require_admin_token(admin_token)
    raise HTTPException(
        status_code=410,
        detail="Deprecated route. Use POST /api/compat/connectors/{connector_id}/import/openapi-url",
    )


@router.post("/{connector_id}/import/openapi")
async def import_openapi(
    connector_id: str,
    payload: Dict[str, Any] = Body(...),
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _require_admin_token(admin_token)
    connector = _store.get_connector(connector_id, mask_secret=True)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    spec_raw = payload.get("spec")
    if isinstance(spec_raw, dict):
        spec = spec_raw
    else:
        spec = _load_openapi_text(str(spec_raw or ""))
    result = _import_openapi_spec(
        str(connector.get("connector_id") or ""),
        spec,
        source_type="text",
        source_ref=None,
    )
    return {"ok": True, "data": result}


@router.post("/{connector_id}/import/openapi-url")
async def import_openapi_url(
    connector_id: str,
    payload: Dict[str, Any] = Body(...),
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _require_admin_token(admin_token)
    source_url = str(payload.get("url") or "").strip()
    if not source_url:
        raise HTTPException(status_code=422, detail="url is required")
    req = Request(source_url, method="GET", headers={"Accept": "application/json, text/yaml, application/yaml, text/plain"})
    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"failed to fetch openapi url: {exc}")
    connector = _store.get_connector(connector_id, mask_secret=True)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    spec = _load_openapi_text(raw)
    result = _import_openapi_spec(
        str(connector.get("connector_id") or ""),
        spec,
        source_type="url",
        source_ref=source_url,
    )
    return {"ok": True, "data": result}


@router.get("/{connector_id}/endpoints")
async def list_endpoints(connector_id: str, include_disabled: bool = Query(default=True)):
    connector = _store.get_connector(connector_id, mask_secret=True)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    return {"ok": True, "data": _store.list_endpoints(connector_id, include_disabled=include_disabled)}


@router.post("/{connector_id}/endpoints")
async def upsert_endpoint(
    connector_id: str,
    payload: Dict[str, Any] = Body(...),
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _require_admin_token(admin_token)
    connector = _store.get_connector(connector_id, mask_secret=True)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    try:
        item = _store.upsert_endpoint(connector_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"ok": True, "data": item}


@router.delete("/{connector_id}/endpoints/{endpoint_id}")
async def delete_endpoint(
    connector_id: str,
    endpoint_id: str,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _require_admin_token(admin_token)
    ok = _store.delete_endpoint(connector_id, endpoint_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return {"ok": True, "data": {"endpoint_id": endpoint_id}}


@router.post("/{connector_id}/endpoints/{endpoint_id}/test")
async def test_endpoint(
    connector_id: str,
    endpoint_id: str,
    payload: Dict[str, Any] = Body(default_factory=dict),
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _require_admin_token(admin_token)
    connector = _store.get_connector(connector_id, mask_secret=False)
    endpoint = _store.get_endpoint(connector_id, endpoint_id)
    if not connector or not endpoint:
        raise HTTPException(status_code=404, detail="Connector or endpoint not found")

    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
    base_url = str(connector.get("base_url") or "").rstrip("/")
    path = str(endpoint.get("path") or "")
    endpoint_url = str(payload.get("url") or "").strip()
    if not endpoint_url:
        endpoint_url = path if path.startswith("http") else f"{base_url}/{path.lstrip('/')}"
    endpoint_url = _render_template(endpoint_url, params)

    method = str(payload.get("method") or endpoint.get("method") or "GET").upper()
    headers: Dict[str, str] = {"Accept": "application/json"}
    api_key = str(connector.get("api_key") or "").strip()
    if api_key:
        auth_header = str(connector.get("auth_header") or "Authorization").strip() or "Authorization"
        headers[auth_header] = api_key
    default_headers = connector.get("default_headers")
    if isinstance(default_headers, dict):
        for hk, hv in default_headers.items():
            headers[str(hk)] = _render_template(str(hv), params)
    if isinstance(payload.get("headers"), dict):
        for hk, hv in payload.get("headers").items():
            headers[str(hk)] = _render_template(str(hv), params)
    if isinstance(payload.get("query"), dict) and payload.get("query"):
        query_string = "&".join(
            f"{quote(str(k))}={quote(_render_template(str(v), params))}"
            for k, v in payload.get("query").items()
        )
        endpoint_url = endpoint_url + ("&" if "?" in endpoint_url else "?") + query_string
    req = Request(endpoint_url, method=method, headers=headers)
    try:
        with urlopen(req, timeout=12) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {"raw": raw}
            preview = parsed if isinstance(parsed, dict) else {"data": parsed}
            return {
                "ok": True,
                "data": {
                    "url": endpoint_url,
                    "method": method,
                    "status_code": int(getattr(resp, "status", 200) or 200),
                    "preview": preview,
                },
            }
    except Exception as exc:
        return {
            "ok": True,
            "data": {
                "url": endpoint_url,
                "method": method,
                "status_code": 0,
                "error": str(exc),
            },
        }


@router.post("/{connector_id}/endpoints/{endpoint_id}/infer-profile")
async def infer_profile(
    connector_id: str,
    endpoint_id: str,
    payload: Dict[str, Any] = Body(...),
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    actor = _require_admin_token(admin_token)
    endpoint = _store.get_endpoint(connector_id, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    response_sample_raw = payload.get("response_sample_json", payload.get("sample_json"))
    if isinstance(response_sample_raw, str):
        try:
            sample_json = json.loads(response_sample_raw)
        except Exception:
            raise HTTPException(status_code=422, detail="response_sample_json must be valid JSON")
    else:
        sample_json = response_sample_raw
    if not isinstance(sample_json, dict):
        raise HTTPException(status_code=422, detail="response_sample_json must be object")

    request_sample_raw = payload.get("request_sample_json")
    request_sample_json: Dict[str, Any] = {}
    if isinstance(request_sample_raw, str) and request_sample_raw.strip():
        try:
            request_parsed = json.loads(request_sample_raw)
        except Exception:
            raise HTTPException(status_code=422, detail="request_sample_json must be valid JSON")
        if not isinstance(request_parsed, dict):
            raise HTTPException(status_code=422, detail="request_sample_json must be object")
        request_sample_json = request_parsed
    elif isinstance(request_sample_raw, dict):
        request_sample_json = request_sample_raw
    elif request_sample_raw not in (None, ""):
        raise HTTPException(status_code=422, detail="request_sample_json must be object")

    endpoint_key = str(endpoint.get("endpoint_key") or "")
    capability_id = str(payload.get("capability_id") or endpoint.get("capability_id") or "")
    item_id = str(payload.get("item_id") or endpoint.get("item_id") or "")
    if not capability_id or not item_id:
        raise HTTPException(status_code=422, detail="capability_id and item_id are required")
    api_doc_text = str(payload.get("api_doc_text") or "")

    result = _service.infer_profile(
        connector_id=connector_id,
        endpoint_id=endpoint_id,
        endpoint_key=endpoint_key,
        capability_id=capability_id,
        item_id=item_id,
        sample_json=sample_json,
        request_sample_json=request_sample_json,
        api_doc_text=api_doc_text,
        actor=actor,
        endpoint_meta=payload.get("endpoint") if isinstance(payload.get("endpoint"), dict) else None,
    )
    return {"ok": True, "data": result}


@router.post("/{connector_id}/endpoints/{endpoint_id}/apply-profile")
async def apply_profile(
    connector_id: str,
    endpoint_id: str,
    payload: Dict[str, Any] = Body(...),
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    actor = _require_admin_token(admin_token)
    endpoint = _store.get_endpoint(connector_id, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    connector = _store.get_connector(connector_id, mask_secret=True)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    endpoint_key = str(endpoint.get("endpoint_key") or "")
    endpoint_url = str(payload.get("endpoint", {}).get("url") if isinstance(payload.get("endpoint"), dict) else "").strip()
    if not endpoint_url:
        base_url = str(connector.get("base_url") or "").rstrip("/")
        path = str(endpoint.get("path") or "")
        endpoint_url = path if path.startswith("http") else f"{base_url}/{path.lstrip('/')}"

    method = str(payload.get("endpoint", {}).get("method") if isinstance(payload.get("endpoint"), dict) else "").strip() or str(endpoint.get("method") or "GET")
    try:
        result = _service.apply_profile(
            connector_id=connector_id,
            endpoint_id=endpoint_id,
            endpoint_key=endpoint_key,
            endpoint_url=endpoint_url,
            endpoint_method=method,
            payload=payload,
            actor=actor,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "NO_SAMPLE_AVAILABLE_FOR_VALIDATION":
            raise HTTPException(status_code=422, detail=message)
        raise HTTPException(status_code=422, detail=message)
    return {"ok": True, "data": result}


@router.get("/{connector_id}/endpoints/{endpoint_id}/profiles")
async def list_profiles(connector_id: str, endpoint_id: str, limit: int = Query(default=20, ge=1, le=200)):
    endpoint = _store.get_endpoint(connector_id, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    endpoint_key = str(endpoint.get("endpoint_key") or "")
    return {"ok": True, "data": _store.list_profiles(connector_id, endpoint_key, limit=limit)}


@router.get("/{connector_id}/endpoints/{endpoint_id}/usage-card")
async def get_usage_card(connector_id: str, endpoint_id: str):
    card = _store.latest_usage_card(connector_id, endpoint_id)
    if not card:
        raise HTTPException(status_code=404, detail="Usage card not found")
    return {"ok": True, "data": card}


@router.get("/search/endpoints/all")
async def search_endpoints(
    q: str = Query(default=""),
    capability_id: Optional[str] = Query(default=None),
    item_id: Optional[str] = Query(default=None),
):
    query = q.strip().lower()
    out = []
    for connector in _store.list_connectors(include_disabled=False):
        cid = str(connector.get("connector_id") or "")
        for endpoint in _store.list_endpoints(cid, include_disabled=False):
            text = f"{connector.get('name','')} {endpoint.get('name','')} {endpoint.get('method','')} {endpoint.get('path','')} {endpoint.get('endpoint_key','')}".lower()
            if query and query not in text:
                continue
            if capability_id and str(endpoint.get("capability_id") or "") != capability_id:
                continue
            if item_id and str(endpoint.get("item_id") or "") != item_id:
                continue
            out.append(
                {
                    "connector_id": cid,
                    "connector_name": connector.get("name"),
                    "endpoint_id": endpoint.get("endpoint_id"),
                    "endpoint_key": endpoint.get("endpoint_key"),
                    "name": endpoint.get("name"),
                    "method": endpoint.get("method"),
                    "path": endpoint.get("path"),
                    "capability_id": endpoint.get("capability_id"),
                    "item_id": endpoint.get("item_id"),
                }
            )
    return {"ok": True, "data": out[:200]}
