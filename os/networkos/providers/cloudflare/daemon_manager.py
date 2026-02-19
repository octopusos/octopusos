"""Cloudflared daemon manager (Part C, M2).

Hard boundaries:
- Execution only: local process/service management + status collection
- No Cloudflare API writes here (tunnel/access/DNS provisioning handled elsewhere)
- No secrets in logs or returned payloads
"""

from __future__ import annotations

import os
import json
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Dict, Optional


_LABEL = "com.octopusos.networkos.cloudflared"
_SYSTEMD_UNIT = "octopusos-cloudflared.service"


@dataclass
class DetectInfo:
    installed: bool
    path: str | None
    version: str | None

    def to_dict(self) -> Dict[str, Any]:
        return {"installed": bool(self.installed), "path": self.path, "version": self.version}


@dataclass
class DaemonStatus:
    # Required by acceptance: not_installed/stopped/running/error
    state: str
    installed: bool
    service_installed: bool
    autostart_enabled: bool
    credentials_present: bool
    pid: int | None = None
    uptime_s: int | None = None
    last_error: str | None = None
    logs_tail: str | None = None
    platform: str | None = None
    service_type: str | None = None
    tunnel_name: str | None = None
    cloudflared_path: str | None = None
    cloudflared_version: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "installed": bool(self.installed),
            "service_installed": bool(self.service_installed),
            "autostart_enabled": bool(self.autostart_enabled),
            "credentials_present": bool(self.credentials_present),
            "pid": self.pid,
            "uptime_s": self.uptime_s,
            "last_error": self.last_error,
            "logs_tail": self.logs_tail,
            "platform": self.platform,
            "service_type": self.service_type,
            "tunnel_name": self.tunnel_name,
            "cloudflared_path": self.cloudflared_path,
            "cloudflared_version": self.cloudflared_version,
        }


def _now_s() -> int:
    return int(time.time())


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except Exception:
        pass


def _redact(text: str) -> str:
    # Best-effort: these are not expected in daemon logs, but keep the boundary strong.
    t = str(text or "")
    # Strip non-printable control chars (keeps newline/tab/carriage return).
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", t)
    t = re.sub(r"(CF-Access-Client-Secret:\\s*)(\\S+)", r"\\1<redacted>", t, flags=re.IGNORECASE)
    t = re.sub(r"(Authorization:\\s*Bearer\\s+)(\\S+)", r"\\1<redacted>", t, flags=re.IGNORECASE)
    return t


def _tail_file(path: str, lines: int = 50) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read()
        # naive but fine for small logs
        text = data.decode("utf-8", errors="replace")
        selected = text.splitlines()[-lines:]
        fallback_ts = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        normalized: list[str] = []
        for raw in selected:
            line = str(raw or "")
            if not line.strip():
                continue
            # Preserve timestamped lines from runner; annotate legacy lines with file mtime.
            if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\s+", line):
                normalized.append(line)
            else:
                normalized.append(f"{fallback_ts} [legacy] {line}")
        out = "\n".join(normalized)
        return _redact(out)
    except Exception:
        return ""


def _tail_latest(paths: list[str], lines: int = 50) -> str:
    """Pick tail from the most recently updated readable log file."""
    best_path = None
    best_mtime = -1.0
    for p in paths:
        try:
            if os.path.exists(p):
                mt = os.path.getmtime(p)
                if mt > best_mtime:
                    best_mtime = mt
                    best_path = p
        except Exception:
            continue
    if not best_path:
        return ""
    return _tail_file(best_path, lines=lines)


def _run(cmd: list[str], timeout_s: int = 20) -> tuple[int, str, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    return int(p.returncode), str(p.stdout or ""), str(p.stderr or "")


def _run_checked(
    cmd: list[str],
    *,
    timeout_s: int = 20,
    ok_rc: tuple[int, ...] = (0,),
    ok_substrings: tuple[str, ...] = (),
) -> tuple[str, str]:
    rc, out, err = _run(cmd, timeout_s=timeout_s)
    if rc in ok_rc:
        return out, err
    msg = (err or out or "").strip()
    low = msg.lower()
    for s in ok_substrings:
        if s and s.lower() in low:
            return out, err
    raise RuntimeError(f"command_failed:{' '.join(cmd[:3])}:rc={rc}:{msg[:200]}")


def _is_service_not_loaded_message(msg: str) -> bool:
    m = str(msg or "").strip().lower()
    if not m:
        return False
    indicators = (
        "could not find service",
        "no such process",
        "not loaded",
        "service is disabled",
    )
    return any(token in m for token in indicators)


def _credentials_present() -> bool:
    # Conservative: just detect local cloudflared credentials dir existence.
    base = os.path.expanduser("~/.cloudflared")
    if not os.path.isdir(base):
        return False
    # cert.pem OR any json indicates some form of login/tunnel credentials exist.
    if os.path.exists(os.path.join(base, "cert.pem")):
        return True
    try:
        for name in os.listdir(base):
            if name.endswith(".json"):
                return True
    except Exception:
        return False
    return False


class CloudflaredDaemonManager:
    def __init__(self, *, state_dir: Optional[str] = None):
        self.state_dir = state_dir or os.path.expanduser("~/.octopusos/networkos/cloudflared")
        self.runner_path = os.path.join(self.state_dir, "cloudflared_runner.sh")
        self.stdout_path = os.path.join(self.state_dir, "stdout.log")
        self.stderr_path = os.path.join(self.state_dir, "stderr.log")
        self.plist_path = os.path.expanduser(f"~/Library/LaunchAgents/{_LABEL}.plist")
        self.systemd_unit_path = os.path.expanduser(f"~/.config/systemd/user/{_SYSTEMD_UNIT}")

    def detect_cloudflared(self) -> DetectInfo:
        exe = shutil.which("cloudflared")
        if not exe:
            # WebUI/backend may run with a reduced PATH (common on macOS app launches).
            # Probe common install locations as fallback.
            candidates = [
                "/opt/homebrew/bin/cloudflared",
                "/usr/local/bin/cloudflared",
                "/usr/bin/cloudflared",
                "/bin/cloudflared",
            ]
            for candidate in candidates:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    exe = candidate
                    break
        if not exe:
            return DetectInfo(installed=False, path=None, version=None)
        ver = None
        try:
            rc, out, _ = _run([exe, "version"], timeout_s=5)
            if rc == 0:
                ver = out.strip().splitlines()[0][:200] if out.strip() else None
        except Exception:
            ver = None
        return DetectInfo(installed=True, path=exe, version=ver)

    def install_cli(self) -> tuple[bool, str]:
        det = self.detect_cloudflared()
        if det.installed:
            return True, "already_installed"

        plat = self._platform()
        if plat == "macos":
            brew = shutil.which("brew")
            if not brew and os.path.isfile("/opt/homebrew/bin/brew") and os.access("/opt/homebrew/bin/brew", os.X_OK):
                brew = "/opt/homebrew/bin/brew"
            if not brew and os.path.isfile("/usr/local/bin/brew") and os.access("/usr/local/bin/brew", os.X_OK):
                brew = "/usr/local/bin/brew"
            if not brew:
                return False, "brew_not_found"
            rc, out, err = _run([brew, "install", "cloudflared"], timeout_s=900)
            if rc != 0:
                msg = (err or out or "").strip()
                return False, f"brew_install_failed:{msg[:240]}"
            det2 = self.detect_cloudflared()
            return (True, "installed") if det2.installed else (False, "install_completed_but_not_detected")

        if plat == "linux":
            return False, "install_cli_linux_manual_required"
        return False, f"platform_not_supported:{plat}"

    def _platform(self) -> str:
        if sys.platform == "darwin":
            return "macos"
        if sys.platform.startswith("linux"):
            return "linux"
        return sys.platform

    def _write_runner(self, *, tunnel_name: str) -> None:
        _ensure_dir(self.state_dir)
        script = f"""#!/usr/bin/env bash
set -euo pipefail

TUNNEL_NAME="{shlex.quote(str(tunnel_name or '').strip())}"
if [[ -n "${{1:-}}" ]]; then
  TUNNEL_NAME="$1"
fi

STATE_DIR="${{OCTOPUSOS_CLOUDFLARED_STATE_DIR:-$HOME/.octopusos/networkos/cloudflared}}"
mkdir -p "${{STATE_DIR}}"
chmod 700 "${{STATE_DIR}}" || true

STDOUT="${{STATE_DIR}}/stdout.log"
STDERR="${{STATE_DIR}}/stderr.log"
TUNNEL_SAFE="${{TUNNEL_NAME//[^a-zA-Z0-9._-]/_}}"
if [[ -z "${{TUNNEL_SAFE}}" ]]; then
  TUNNEL_SAFE="default"
fi
RESTARTS="${{STATE_DIR}}/restarts-${{TUNNEL_SAFE}}.log"

ts() {{
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}}

log_out() {{
  printf "%s %s\\n" "$(ts)" "$1" >> "${{STDOUT}}" || true
}}

log_err() {{
  printf "%s %s\\n" "$(ts)" "$1" >> "${{STDERR}}" || true
}}

pipe_out() {{
  while IFS= read -r line; do
    printf "%s %s\\n" "$(ts)" "$line" >> "${{STDOUT}}" || true
  done
}}

pipe_err() {{
  while IFS= read -r line; do
    printf "%s %s\\n" "$(ts)" "$line" >> "${{STDERR}}" || true
  done
}}

now="$(date +%s)"
touch "${{RESTARTS}}"
chmod 600 "${{RESTARTS}}" || true
echo "${{now}}" >> "${{RESTARTS}}"

# Prune older than 10 minutes.
tmp="${{RESTARTS}}.tmp"
cutoff="$((now - 600))"
awk -v cutoff="${{cutoff}}" '$1 >= cutoff {{ print $1 }}' "${{RESTARTS}}" > "${{tmp}}" || true
mv "${{tmp}}" "${{RESTARTS}}"
count="$(wc -l < \"${{RESTARTS}}\" | tr -d ' ')"
if [[ "${{count}}" -gt 5 ]]; then
  log_err "flapping_detected count=${{count}} in_10m"
  # Exit 0 so launchd/systemd (Restart=on-failure) will not restart.
  exit 0
fi

if [[ ! -d \"$HOME/.cloudflared\" ]]; then
  log_err "credentials_missing:~/.cloudflared"
  exit 0
fi

if [[ -z \"${{TUNNEL_NAME}}\" ]]; then
  log_err "missing_tunnel_name"
  exit 0
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  log_err "cloudflared_not_found_in_path"
  exit 0
fi

# Resolve tunnel id first (name -> id), then run with explicit credentials file.
# This avoids ~/.cloudflared/config.yml overriding the selected tunnel.
INFO_RAW=""
if ! INFO_RAW="$(cloudflared tunnel info "${{TUNNEL_NAME}}" 2>&1)"; then
  while IFS= read -r line; do
    [[ -n "${{line}}" ]] && log_err "${{line}}"
  done <<< "${{INFO_RAW}}"
  log_err "tunnel_not_found_or_unreachable:${{TUNNEL_NAME}}"
  exit 0
fi
while IFS= read -r line; do
  [[ -n "${{line}}" ]] && log_out "${{line}}"
done <<< "${{INFO_RAW}}"

TUNNEL_ID="$(printf '%s\n' "${{INFO_RAW}}" | grep -Eo '[0-9a-fA-F-]{{36}}' | head -n 1 || true)"
if [[ -z "${{TUNNEL_ID}}" ]]; then
  if [[ "${{TUNNEL_NAME}}" =~ ^[0-9a-fA-F-]{{36}}$ ]]; then
    TUNNEL_ID="${{TUNNEL_NAME}}"
  else
    log_err "tunnel_id_parse_failed:${{TUNNEL_NAME}}"
    exit 0
  fi
fi

CRED_FILE="$HOME/.cloudflared/${{TUNNEL_ID}}.json"
if [[ ! -f "${{CRED_FILE}}" ]]; then
  log_err "credentials_file_missing:${{CRED_FILE}}"
  exit 0
fi

exec cloudflared --config /dev/null tunnel --credentials-file "${{CRED_FILE}}" run "${{TUNNEL_ID}}" > >(pipe_out) 2> >(pipe_err)
"""
        with open(self.runner_path, "w", encoding="utf-8") as f:
            f.write(script)
        os.chmod(self.runner_path, 0o700)

    def _mac_uid(self) -> str:
        return str(os.getuid())

    def _mac_target(self) -> str:
        # User GUI domain; works for desktop interactive sessions.
        return f"gui/{self._mac_uid()}"

    def _mac_service_target(self) -> str:
        return f"{self._mac_target()}/{_LABEL}"

    def _write_plist(self, *, tunnel_name: str) -> None:
        _ensure_dir(os.path.dirname(self.plist_path))
        _ensure_dir(self.state_dir)
        # Ensure runner exists.
        self._write_runner(tunnel_name=tunnel_name)
        # launchd's PATH is minimal; set a reasonable default.
        path_env = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key><string>{_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
      <string>{self.runner_path}</string>
      <string>{tunnel_name}</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
      <key>PATH</key><string>{path_env}</string>
    </dict>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key>
    <dict>
      <key>SuccessfulExit</key><false/>
    </dict>
    <key>ThrottleInterval</key><integer>10</integer>
    <key>StandardOutPath</key><string>{self.stdout_path}</string>
    <key>StandardErrorPath</key><string>{self.stderr_path}</string>
    <key>WorkingDirectory</key><string>{self.state_dir}</string>
  </dict>
</plist>
"""
        with open(self.plist_path, "w", encoding="utf-8") as f:
            f.write(plist)
        try:
            os.chmod(self.plist_path, 0o600)
        except Exception:
            pass

    def _write_systemd_unit(self, *, tunnel_name: str) -> None:
        _ensure_dir(os.path.dirname(self.systemd_unit_path))
        _ensure_dir(self.state_dir)
        self._write_runner(tunnel_name=tunnel_name)
        unit = f"""[Unit]
Description=OctopusOS cloudflared tunnel daemon (NetworkOS)
After=network-online.target

[Service]
Type=simple
ExecStart={self.runner_path} {shlex.quote(tunnel_name)}
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=600
StartLimitBurst=5

[Install]
WantedBy=default.target
"""
        with open(self.systemd_unit_path, "w", encoding="utf-8") as f:
            f.write(unit)
        try:
            os.chmod(self.systemd_unit_path, 0o600)
        except Exception:
            pass

    def install_service(self, *, tunnel_name: str) -> None:
        if self._platform() == "macos":
            self._write_plist(tunnel_name=tunnel_name)
            return
        if self._platform() == "linux":
            self._write_systemd_unit(tunnel_name=tunnel_name)
            # best-effort reload
            _run(["systemctl", "--user", "daemon-reload"], timeout_s=10)
            return
        raise RuntimeError(f"platform_not_supported:{self._platform()}")

    def sync_service_runtime(self, *, tunnel_name: str) -> None:
        """Rewrite service artifacts to keep runner/plist/unit aligned with current tunnel."""
        plat = self._platform()
        if plat == "macos":
            # Always rewrite plist/runner. If service is loaded, boot it out so next start uses new args.
            self._write_plist(tunnel_name=tunnel_name)
            _run_checked(
                ["launchctl", "bootout", self._mac_target(), self.plist_path],
                timeout_s=10,
                ok_substrings=("no such process", "not loaded", "already"),
            )
            return
        if plat == "linux":
            self._write_systemd_unit(tunnel_name=tunnel_name)
            _run(["systemctl", "--user", "daemon-reload"], timeout_s=10)
            return
        raise RuntimeError(f"platform_not_supported:{plat}")

    def uninstall_service(self) -> None:
        plat = self._platform()
        if plat == "macos":
            # Best-effort unload, then remove plist.
            self.disable_autostart()
            try:
                os.remove(self.plist_path)
            except Exception:
                pass
            return
        if plat == "linux":
            self.disable_autostart()
            try:
                os.remove(self.systemd_unit_path)
            except Exception:
                pass
            _run(["systemctl", "--user", "daemon-reload"], timeout_s=10)
            return
        raise RuntimeError(f"platform_not_supported:{plat}")

    def enable_autostart(self) -> None:
        plat = self._platform()
        if plat == "macos":
            if not os.path.exists(self.plist_path):
                raise RuntimeError("service_not_installed")
            # bootstrap loads the job into the user's launchd domain
            _run_checked(
                ["launchctl", "bootstrap", self._mac_target(), self.plist_path],
                timeout_s=10,
                ok_substrings=("already", "in progress"),
            )
            _run_checked(["launchctl", "enable", self._mac_service_target()], timeout_s=10, ok_substrings=("already",))
            return
        if plat == "linux":
            _run_checked(["systemctl", "--user", "enable", _SYSTEMD_UNIT], timeout_s=15)
            return
        raise RuntimeError(f"platform_not_supported:{plat}")

    def disable_autostart(self) -> None:
        plat = self._platform()
        if plat == "macos":
            if os.path.exists(self.plist_path):
                _run_checked(["launchctl", "disable", self._mac_service_target()], timeout_s=10, ok_substrings=("already",))
                _run_checked(
                    ["launchctl", "bootout", self._mac_target(), self.plist_path],
                    timeout_s=10,
                    ok_substrings=("no such process", "not loaded", "already"),
                )
            return
        if plat == "linux":
            _run_checked(["systemctl", "--user", "disable", _SYSTEMD_UNIT], timeout_s=15, ok_substrings=("disabled",))
            return
        raise RuntimeError(f"platform_not_supported:{plat}")

    def start(self) -> None:
        plat = self._platform()
        if plat == "macos":
            # start requires loaded job
            self.enable_autostart()
            _run_checked(["launchctl", "kickstart", "-k", self._mac_service_target()], timeout_s=15)
            return
        if plat == "linux":
            _run_checked(["systemctl", "--user", "start", _SYSTEMD_UNIT], timeout_s=20)
            return
        raise RuntimeError(f"platform_not_supported:{plat}")

    def stop(self) -> None:
        plat = self._platform()
        if plat == "macos":
            _run_checked(["launchctl", "stop", self._mac_service_target()], timeout_s=10, ok_substrings=("no such process",))
            return
        if plat == "linux":
            _run_checked(["systemctl", "--user", "stop", _SYSTEMD_UNIT], timeout_s=20)
            return
        raise RuntimeError(f"platform_not_supported:{plat}")

    def restart(self) -> None:
        plat = self._platform()
        if plat == "macos":
            self.enable_autostart()
            _run_checked(["launchctl", "kickstart", "-k", self._mac_service_target()], timeout_s=15)
            return
        if plat == "linux":
            _run_checked(["systemctl", "--user", "restart", _SYSTEMD_UNIT], timeout_s=25)
            return
        raise RuntimeError(f"platform_not_supported:{plat}")

    @staticmethod
    def _parse_systemd_show(stdout: str) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for line in (stdout or "").splitlines():
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
        return out

    @staticmethod
    def _parse_launchctl_print(stdout: str) -> Dict[str, str]:
        # Minimal extraction of "pid =" and "state ="
        m: Dict[str, str] = {}
        for line in (stdout or "").splitlines():
            s = line.strip()
            if s.startswith("state ="):
                m["state"] = s.split("=", 1)[1].strip()
            if s.startswith("pid ="):
                m["pid"] = s.split("=", 1)[1].strip()
        return m

    def get_status(self, *, tunnel_name: str, debug: bool = False) -> DaemonStatus:
        det = self.detect_cloudflared()
        creds = _credentials_present()
        plat = self._platform()

        service_installed = False
        autostart_enabled = False
        pid: int | None = None
        last_error: str | None = None
        logs_tail: str | None = None
        service_type: str | None = None

        if plat == "macos":
            service_type = "launchd"
            service_installed = bool(os.path.exists(self.plist_path) and os.path.exists(self.runner_path))
            if service_installed:
                rc, out, err = _run(["launchctl", "print", self._mac_service_target()], timeout_s=10)
                if rc == 0:
                    parsed = self._parse_launchctl_print(out)
                    if parsed.get("pid", "").isdigit():
                        pid = int(parsed["pid"])
                    state = parsed.get("state") or ""
                    running = state.lower() == "running" or pid is not None
                else:
                    running = False
                    msg = (err or out or "").strip()
                    # launchctl returns non-zero when service exists on disk but is not loaded yet.
                    # Treat this as stopped, not error.
                    if _is_service_not_loaded_message(msg):
                        last_error = None
                    else:
                        last_error = msg[:400] if msg else None

                # autostart enabled check (best-effort)
                rc2, out2, _ = _run(["launchctl", "print-disabled", self._mac_target()], timeout_s=10)
                if rc2 == 0:
                    # Output includes label = true/false for disabled state.
                    for line in out2.splitlines():
                        if _LABEL in line:
                            # e.g. "com.x = false"
                            if "false" in line:
                                autostart_enabled = True
                            break
                if debug:
                    logs_tail = _tail_latest([self.stderr_path, self.stdout_path], lines=50)
            else:
                running = False
        elif plat == "linux":
            service_type = "systemd-user"
            service_installed = bool(os.path.exists(self.systemd_unit_path) and os.path.exists(self.runner_path))
            if service_installed:
                rc, out, err = _run(
                    [
                        "systemctl",
                        "--user",
                        "show",
                        _SYSTEMD_UNIT,
                        "--property=ActiveState,SubState,MainPID,NRestarts",
                    ],
                    timeout_s=10,
                )
                if rc == 0:
                    props = self._parse_systemd_show(out)
                    active = props.get("ActiveState") == "active"
                    sub = props.get("SubState") or ""
                    running = active and sub in {"running", "listening"}
                    mp = props.get("MainPID") or ""
                    if mp.isdigit() and int(mp) > 0:
                        pid = int(mp)
                    # flapping detection via NRestarts (10m limit enforced by unit too)
                    try:
                        n = int(props.get("NRestarts") or "0")
                        if n > 5 and not running:
                            last_error = "flapping_detected"
                    except Exception:
                        pass
                else:
                    running = False
                    last_error = (err or out).strip()[:400] if (err or out) else None

                rc2, out2, _ = _run(["systemctl", "--user", "is-enabled", _SYSTEMD_UNIT], timeout_s=10)
                autostart_enabled = rc2 == 0 and out2.strip() == "enabled"
                if debug:
                    logs_tail = _tail_latest([self.stderr_path, self.stdout_path], lines=50)
                    if not logs_tail:
                        # fallback to journal
                        rcj, outj, _ = _run(["journalctl", "--user", "-u", _SYSTEMD_UNIT, "-n", "50", "--no-pager"], timeout_s=10)
                        if rcj == 0:
                            logs_tail = _redact(outj.strip()[-4000:])
            else:
                running = False
        else:
            return DaemonStatus(
                state="error",
                installed=bool(det.installed),
                service_installed=False,
                autostart_enabled=False,
                credentials_present=bool(creds),
                last_error=f"platform_not_supported:{plat}",
                platform=plat,
                service_type=None,
                tunnel_name=tunnel_name,
                cloudflared_path=det.path,
                cloudflared_version=det.version,
            )

        # Map to required state values.
        if not det.installed:
            state = "not_installed"
        elif not service_installed:
            # Binary is installed but service is not yet installed/registered.
            state = "stopped"
        else:
            if last_error and last_error.startswith("platform_not_supported"):
                state = "error"
            elif running:
                state = "running"
            else:
                # If we have an error string from service manager, surface "error".
                state = "error" if last_error else "stopped"

        return DaemonStatus(
            state=state,
            installed=bool(det.installed),
            service_installed=bool(service_installed),
            autostart_enabled=bool(autostart_enabled),
            credentials_present=bool(creds),
            pid=pid,
            uptime_s=None,
            last_error=last_error,
            logs_tail=logs_tail,
            platform=plat,
            service_type=service_type,
            tunnel_name=tunnel_name,
            cloudflared_path=det.path,
            cloudflared_version=det.version,
        )

    def list_tunnels(self) -> list[Dict[str, Any]]:
        det = self.detect_cloudflared()
        if not det.installed or not det.path:
            return []

        rc, out, _ = _run([det.path, "tunnel", "list", "--output", "json"], timeout_s=15)
        if rc != 0:
            return []

        try:
            payload = json.loads(out or "[]")
        except Exception:
            return []
        if not isinstance(payload, list):
            return []

        items: list[Dict[str, Any]] = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            tid = str(row.get("id") or "").strip()
            name = str(row.get("name") or "").strip()
            created_at = str(row.get("created_at") or "").strip() or None
            if not name:
                continue
            items.append(
                {
                    "id": tid or None,
                    "name": name,
                    "created_at": created_at,
                    "credential_file_exists": bool(
                        tid and os.path.exists(os.path.expanduser(f"~/.cloudflared/{tid}.json"))
                    ),
                }
            )
        items.sort(key=lambda x: str(x.get("name") or "").lower())
        return items

    def clear_logs(self) -> Dict[str, Any]:
        cleared: list[str] = []
        for p in (self.stdout_path, self.stderr_path):
            try:
                _ensure_dir(os.path.dirname(p))
                with open(p, "w", encoding="utf-8") as f:
                    f.write("")
                cleared.append(p)
            except Exception:
                continue
        return {"cleared": cleared, "count": len(cleared)}

    def create_tunnel(self, *, name: str) -> Dict[str, Any]:
        det = self.detect_cloudflared()
        if not det.installed or not det.path:
            raise RuntimeError("cloudflared_not_installed")
        tunnel_name = str(name or "").strip()
        if not tunnel_name:
            raise RuntimeError("tunnel_name_required")
        if not re.match(r"^[a-zA-Z0-9._-]{2,64}$", tunnel_name):
            raise RuntimeError("invalid_tunnel_name")

        # idempotent: return existing tunnel when same name is already present.
        existing = self.list_tunnels()
        for row in existing:
            if str(row.get("name") or "").strip().lower() == tunnel_name.lower():
                return {
                    "created": False,
                    "detail": "already_exists",
                    "tunnel": row,
                }

        rc, out, err = _run([det.path, "tunnel", "create", tunnel_name], timeout_s=45)
        if rc != 0:
            msg = str((err or out or "").strip())
            raise RuntimeError(f"create_tunnel_failed:{msg[:280]}")

        # Re-list for canonical id/name/credential state.
        for row in self.list_tunnels():
            if str(row.get("name") or "").strip().lower() == tunnel_name.lower():
                return {"created": True, "detail": "created", "tunnel": row}

        # Fallback when create command succeeded but list is stale.
        return {
            "created": True,
            "detail": "created_but_not_listed",
            "tunnel": {"name": tunnel_name, "id": None, "created_at": None, "credential_file_exists": False},
        }
