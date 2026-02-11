"""Desktop runtime API contract endpoints for embedded clients."""

from __future__ import annotations

import json
import os
import time
import zipfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from octopusos import __version__
from octopusos.config import load_settings
from octopusos.core.capabilities.admin_token import validate_admin_token
from octopusos.daemon.service import get_runtime_paths, read_status

router = APIRouter(tags=["desktop-runtime"])
APP_START_MONOTONIC = time.monotonic()


class DiagnosticExportRequest(BaseModel):
    include_logs: bool = True
    include_config: bool = True
    include_state: bool = True


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact(data: Any) -> Any:
    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for key, value in data.items():
            k = str(key).lower()
            if any(s in k for s in ("token", "password", "secret", "key")):
                out[str(key)] = "***redacted***"
            else:
                out[str(key)] = _redact(value)
        return out
    if isinstance(data, list):
        return [_redact(x) for x in data]
    return data


def _require_admin_token(token: str | None) -> None:
    if not validate_admin_token(token):
        raise HTTPException(status_code=403, detail="Invalid admin token")


@router.get("/api/status")
def desktop_status() -> dict[str, Any]:
    status = read_status()
    runtime_paths = get_runtime_paths()

    capabilities = {
        "daemon_control": True,
        "diagnostic_export": True,
        "tray_control": True,
    }

    return {
        "ok": True,
        "runtime": "embedded",
        "version": __version__,
        "build_hash": os.getenv("OCTOPUSOS_BUILD_SHA", "unknown"),
        "pid": status.pid,
        "running": status.running,
        "host": status.host,
        "port": status.port,
        "url": status.url,
        "port_source": status.port_source,
        "listen_scope": "loopback",
        "data_dir": str(status.data_dir),
        "log_path": str(status.log_file),
        "status_path": str(status.status_file),
        "runtime_dir": str(runtime_paths.runtime_dir),
        "capabilities": capabilities,
        "timestamp": _utc_now(),
    }


@router.post("/api/diagnostic/export")
def export_diagnostic_bundle(
    payload: DiagnosticExportRequest,
    admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> dict[str, Any]:
    _require_admin_token(admin_token)

    status = read_status()
    runtime_paths = get_runtime_paths()
    runtime_paths.runtime_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    bundle_name = f"octopusos-evidence-{ts}.zip"
    bundle_path = runtime_paths.runtime_dir / bundle_name

    status_payload = {
        "running": status.running,
        "pid": status.pid,
        "host": status.host,
        "port": status.port,
        "url": status.url,
        "port_source": status.port_source,
        "timestamp": _utc_now(),
    }

    config_snapshot = _redact(asdict(load_settings()))

    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "version": __version__,
            "build_hash": os.getenv("OCTOPUSOS_BUILD_SHA", "unknown"),
            "created_at": _utc_now(),
            "runtime": "embedded",
            "os": os.name,
            "platform": os.sys.platform,
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        if payload.include_state:
            zf.writestr("status.json", json.dumps(status_payload, ensure_ascii=False, indent=2))

        if payload.include_config:
            zf.writestr(
                "config_snapshot.json",
                json.dumps(config_snapshot, ensure_ascii=False, indent=2),
            )

        if payload.include_logs:
            zf.writestr("logs/.keep", "")
            if status.log_file.exists():
                zf.write(status.log_file, arcname=f"logs/{status.log_file.name}")

    size_bytes = bundle_path.stat().st_size if bundle_path.exists() else 0
    return {
        "ok": True,
        "bundle_path": str(bundle_path),
        "size_bytes": size_bytes,
    }
