from __future__ import annotations

import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from octopusos import __version__

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080

try:
    import psutil
except Exception:  # pragma: no cover - optional runtime guard
    psutil = None


@dataclass
class WebUIDaemonStatus:
    running: bool
    pid: int | None
    host: str
    port: int
    url: str
    data_dir: Path
    log_file: Path
    status_file: Path
    started_at: str | None
    last_error: str | None
    port_source: str


@dataclass
class WebUIStartResult:
    ok: bool
    already_running: bool
    foreground: bool
    port_changed: bool
    status: WebUIDaemonStatus
    message: str


@dataclass
class RuntimePaths:
    data_dir: Path
    runtime_dir: Path
    log_dir: Path
    pid_file: Path
    lock_file: Path
    status_file: Path
    log_file: Path
    token_file: Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def _wait_port(host: str, port: int, timeout_sec: float = 20.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if _is_port_open(host, port):
            return True
        time.sleep(0.2)
    return False


def _pid_looks_like_webui(pid: int) -> bool:
    if psutil is None:
        return True
    try:
        proc = psutil.Process(pid)
        cmdline = " ".join(proc.cmdline()).lower()
        return "octopusos.webui.app:app" in cmdline
    except Exception:
        return False


def _resolve_data_dir() -> Path:
    env_path = os.environ.get("OCTOPUSOS_DATA_DIR")
    if env_path:
        return Path(env_path).expanduser().resolve()

    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
        return base / "OctopusOS"

    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/OctopusOS"

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / "octopusos"
    return Path.home() / ".local/share/octopusos"


def get_runtime_paths() -> RuntimePaths:
    data_dir = _resolve_data_dir()
    runtime_dir = data_dir / "runtime"
    log_dir = data_dir / "logs"
    return RuntimePaths(
        data_dir=data_dir,
        runtime_dir=runtime_dir,
        log_dir=log_dir,
        pid_file=runtime_dir / "webui.pid",
        lock_file=runtime_dir / "webui.lock",
        status_file=runtime_dir / "webui.status.json",
        log_file=log_dir / "webui.log",
        token_file=runtime_dir / "control.token",
    )


def ensure_runtime_dirs() -> RuntimePaths:
    paths = get_runtime_paths()
    paths.runtime_dir.mkdir(parents=True, exist_ok=True)
    paths.log_dir.mkdir(parents=True, exist_ok=True)
    return paths


def _read_pid(pid_file: Path) -> int | None:
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except Exception:
        pid_file.unlink(missing_ok=True)
        return None


def _write_status(paths: RuntimePaths, payload: dict[str, Any]) -> None:
    paths.status_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_status_file(paths: RuntimePaths) -> dict[str, Any]:
    if not paths.status_file.exists():
        return {}
    try:
        return json.loads(paths.status_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_or_create_control_token() -> str:
    paths = ensure_runtime_dirs()
    if paths.token_file.exists():
        token = paths.token_file.read_text(encoding="utf-8").strip()
        if token:
            return token

    token = secrets.token_urlsafe(32)
    paths.token_file.write_text(token, encoding="utf-8")
    try:
        os.chmod(paths.token_file, 0o600)
    except OSError:
        # Windows may not support chmod in the same way; best effort only.
        pass
    return token


def select_port(host: str, preferred_port: int, max_scan: int = 100) -> tuple[int, str]:
    if not _is_port_open(host, preferred_port):
        return preferred_port, "preferred"

    for offset in range(1, max_scan + 1):
        candidate = preferred_port + offset
        if not _is_port_open(host, candidate):
            return candidate, "fallback"

    raise RuntimeError(f"No available port in range {preferred_port}-{preferred_port + max_scan}")


def _status_from_snapshot(snapshot: dict[str, Any], paths: RuntimePaths) -> WebUIDaemonStatus:
    pid = snapshot.get("pid")
    if isinstance(pid, str) and pid.isdigit():
        pid = int(pid)

    host = str(snapshot.get("host") or DEFAULT_HOST)
    port = int(snapshot.get("port") or DEFAULT_PORT)
    running = bool(
        pid and _is_pid_running(pid) and _pid_looks_like_webui(pid) and _is_port_open(host, port)
    )

    return WebUIDaemonStatus(
        running=running,
        pid=pid if isinstance(pid, int) else None,
        host=host,
        port=port,
        url=f"http://{host}:{port}",
        data_dir=paths.data_dir,
        log_file=Path(snapshot.get("log_file") or paths.log_file),
        status_file=paths.status_file,
        started_at=snapshot.get("started_at"),
        last_error=snapshot.get("last_error"),
        port_source=str(snapshot.get("port_source") or "preferred"),
    )


def read_status() -> WebUIDaemonStatus:
    paths = ensure_runtime_dirs()
    snapshot = _read_status_file(paths)

    if not snapshot:
        pid = _read_pid(paths.pid_file)
        snapshot = {
            "host": DEFAULT_HOST,
            "port": DEFAULT_PORT,
            "pid": pid,
            "log_file": str(paths.log_file),
            "port_source": "preferred",
        }

    status = _status_from_snapshot(snapshot, paths)
    if status.pid and not status.running:
        paths.pid_file.unlink(missing_ok=True)
    return status


def _acquire_lock(paths: RuntimePaths) -> None:
    if paths.lock_file.exists():
        stale_pid = _read_pid(paths.pid_file)
        if stale_pid and _is_pid_running(stale_pid):
            raise RuntimeError("WebUI daemon is already running")
        paths.lock_file.unlink(missing_ok=True)

    fd = os.open(paths.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)


def _release_lock(paths: RuntimePaths) -> None:
    paths.lock_file.unlink(missing_ok=True)


def start_webui(
    host: str = DEFAULT_HOST,
    preferred_port: int = DEFAULT_PORT,
    foreground: bool = False,
    open_browser: bool = False,
) -> WebUIStartResult:
    paths = ensure_runtime_dirs()
    existing = read_status()
    if existing.running:
        return WebUIStartResult(
            ok=True,
            already_running=True,
            foreground=False,
            port_changed=False,
            status=existing,
            message=f"already running at {existing.url}",
        )

    _acquire_lock(paths)
    try:
        port, port_source = select_port(host, preferred_port)
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "octopusos.webui.app:app",
            "--host",
            host,
            "--port",
            str(port),
        ]
        control_token = get_or_create_control_token()
        env = os.environ.copy()
        env["OCTOPUSOS_CONTROL_TOKEN"] = control_token

        if foreground:
            snapshot = {
                "component": "webui-daemon",
                "version": __version__,
                "host": host,
                "port": port,
                "pid": os.getpid(),
                "started_at": _utc_now(),
                "log_file": str(paths.log_file),
                "data_dir": str(paths.data_dir),
                "port_source": port_source,
                "last_error": None,
            }
            _write_status(paths, snapshot)
            if open_browser:
                webbrowser.open(f"http://{host}:{port}")
            rc = subprocess.call(cmd, env=env)
            if rc != 0:
                snapshot["last_error"] = f"foreground process exited with code {rc}"
                _write_status(paths, snapshot)
            return WebUIStartResult(
                ok=rc == 0,
                already_running=False,
                foreground=True,
                port_changed=port != preferred_port,
                status=_status_from_snapshot(snapshot, paths),
                message="foreground run finished" if rc == 0 else f"foreground process exited with code {rc}",
            )

        log_handle = paths.log_file.open("a", encoding="utf-8")
        proc = subprocess.Popen(cmd, stdout=log_handle, stderr=subprocess.STDOUT, env=env)

        snapshot = {
            "component": "webui-daemon",
            "version": __version__,
            "host": host,
            "port": port,
            "pid": proc.pid,
            "started_at": _utc_now(),
            "log_file": str(paths.log_file),
            "data_dir": str(paths.data_dir),
            "port_source": port_source,
            "last_error": None,
            "control_api": f"http://{host}:{port}/api/daemon",
        }
        paths.pid_file.write_text(str(proc.pid), encoding="utf-8")
        _write_status(paths, snapshot)

        if not _wait_port(host, port, timeout_sec=25.0):
            proc.terminate()
            snapshot["last_error"] = "webui process failed to bind the selected port"
            _write_status(paths, snapshot)
            paths.pid_file.unlink(missing_ok=True)
            return WebUIStartResult(
                ok=False,
                already_running=False,
                foreground=False,
                port_changed=port != preferred_port,
                status=_status_from_snapshot(snapshot, paths),
                message="failed to start webui daemon",
            )

        if open_browser:
            webbrowser.open(f"http://{host}:{port}")

        status = _status_from_snapshot(snapshot, paths)
        return WebUIStartResult(
            ok=True,
            already_running=False,
            foreground=False,
            port_changed=port != preferred_port,
            status=status,
            message="started",
        )
    finally:
        _release_lock(paths)


def stop_webui() -> tuple[bool, str]:
    paths = ensure_runtime_dirs()
    status = read_status()

    if not status.pid or not _is_pid_running(status.pid) or not _pid_looks_like_webui(status.pid):
        snapshot = _read_status_file(paths)
        if snapshot:
            snapshot["last_error"] = "not running"
            _write_status(paths, snapshot)
        paths.pid_file.unlink(missing_ok=True)
        return True, "not running"

    try:
        os.kill(status.pid, signal.SIGTERM)
        for _ in range(50):
            if not _is_pid_running(status.pid):
                break
            time.sleep(0.1)
        if _is_pid_running(status.pid):
            os.kill(status.pid, signal.SIGKILL)
    except OSError as exc:
        return False, f"failed to stop daemon: {exc}"

    paths.pid_file.unlink(missing_ok=True)
    snapshot = _read_status_file(paths)
    if snapshot:
        snapshot["stopped_at"] = _utc_now()
        snapshot["last_error"] = None
        _write_status(paths, snapshot)
    return True, "stopped"


def tail_logs(lines: int = 100) -> str:
    paths = ensure_runtime_dirs()
    if not paths.log_file.exists():
        return ""
    all_lines = paths.log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    if lines <= 0:
        return "\n".join(all_lines)
    return "\n".join(all_lines[-lines:])
