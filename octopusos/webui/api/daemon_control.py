"""Local daemon control API (loopback only, token-gated)."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Header, HTTPException, Query, Request

from octopusos.daemon.service import read_status, start_webui, tail_logs

router = APIRouter(prefix="/api/daemon", tags=["daemon-control"])


def _is_loopback_request(request: Request) -> bool:
    host = (request.client.host if request.client else "") or ""
    return host in {"127.0.0.1", "::1", "localhost"}


def _expected_token() -> str:
    token = os.environ.get("OCTOPUSOS_CONTROL_TOKEN", "").strip()
    if token:
        return token

    # Fallback when app was not started via daemon launcher.
    status = read_status()
    token_file = Path(status.data_dir) / "runtime" / "control.token"
    if token_file.exists():
        return token_file.read_text(encoding="utf-8").strip()
    return ""


def _is_loopback_origin(origin: str) -> bool:
    host = (urlparse(origin).hostname or "").strip().lower()
    return host in {"127.0.0.1", "::1", "localhost"}


def _authorize(request: Request, token: str | None) -> None:
    if not _is_loopback_request(request):
        raise HTTPException(status_code=403, detail="local loopback requests only")

    expected = _expected_token()
    if not expected:
        raise HTTPException(status_code=503, detail="control token unavailable")

    if not token or token != expected:
        raise HTTPException(status_code=401, detail="invalid control token")


@router.get("/control-token")
def daemon_control_token(request: Request, origin: str | None = Header(default=None)) -> dict:
    if not _is_loopback_request(request):
        raise HTTPException(status_code=403, detail="local loopback requests only")
    if origin and not _is_loopback_origin(origin):
        raise HTTPException(status_code=403, detail="invalid origin for control token")

    token = _expected_token()
    if not token:
        raise HTTPException(status_code=503, detail="control token unavailable")
    return {"ok": True, "token": token}


@router.get("/status")
def daemon_status(request: Request, x_octopusos_token: str | None = Header(default=None)) -> dict:
    _authorize(request, x_octopusos_token)
    status = read_status()
    return {
        "ok": True,
        "running": status.running,
        "pid": status.pid,
        "host": status.host,
        "port": status.port,
        "url": status.url,
        "data_dir": str(status.data_dir),
        "log_path": str(status.log_file),
        "log_file": str(status.log_file),
        "status_path": str(status.status_file),
        "status_file": str(status.status_file),
        "started_at": status.started_at,
        "last_error": status.last_error,
        "port_source": status.port_source,
    }


@router.get("/logs")
def daemon_logs(
    request: Request,
    lines: int = Query(default=100, ge=1, le=5000),
    x_octopusos_token: str | None = Header(default=None),
) -> dict:
    _authorize(request, x_octopusos_token)
    return {
        "ok": True,
        "lines": lines,
        "log_path": str(read_status().log_file),
        "content": tail_logs(lines=lines),
    }


@router.post("/start")
def daemon_start(request: Request, x_octopusos_token: str | None = Header(default=None)) -> dict:
    _authorize(request, x_octopusos_token)
    status = read_status()

    if status.running:
        return {"ok": True, "already_running": True, "url": status.url, "port": status.port}

    result = start_webui(host=status.host, preferred_port=status.port)
    return {
        "ok": result.ok,
        "already_running": result.already_running,
        "port_changed": result.port_changed,
        "url": result.status.url,
        "port": result.status.port,
        "message": result.message,
    }


@router.post("/restart")
def daemon_restart(request: Request, x_octopusos_token: str | None = Header(default=None)) -> dict:
    _authorize(request, x_octopusos_token)
    status = read_status()
    host = status.host
    port = status.port

    def _restart_later() -> None:
        time.sleep(0.6)
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "octopusos.cli.main",
                "webui",
                "start",
                "--host",
                host,
                "--port",
                str(port),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.kill(os.getpid(), signal.SIGTERM)

    timer = threading.Thread(target=_restart_later, daemon=True)
    timer.start()
    return {"ok": True, "message": "restarting", "host": host, "port": port}


@router.post("/stop")
def daemon_stop(request: Request, x_octopusos_token: str | None = Header(default=None)) -> dict:
    _authorize(request, x_octopusos_token)

    def _stop_later() -> None:
        os.kill(os.getpid(), signal.SIGTERM)

    timer = threading.Timer(0.2, _stop_later)
    timer.daemon = True
    timer.start()

    return {"ok": True, "message": "stopping", "pid": os.getpid()}
