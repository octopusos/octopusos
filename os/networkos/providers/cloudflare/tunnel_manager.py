"""Cloudflare Tunnel Provider (cloudflared process wrapper)."""

import json
import logging
import subprocess
import threading
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class CloudflareTunnelManager:
    """Manage Cloudflare Tunnel lifecycle via cloudflared."""

    def __init__(
        self,
        tunnel_id: str,
        tunnel_name: str,
        token: str,  # Cloudflare Tunnel Token
        local_target: str,
        store,  # NetworkOSStore
    ):
        self.tunnel_id = tunnel_id
        self.tunnel_name = tunnel_name
        self.token = token
        self.local_target = local_target
        self.store = store

        self.process: Optional[subprocess.Popen] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self._should_stop = False

    def start(self) -> bool:
        if self.process and self.process.poll() is None:
            logger.warning("Tunnel %s already running", self.tunnel_name)
            return True

        try:
            if not self._check_cloudflared():
                logger.error("cloudflared not found. Install: brew install cloudflared")
                self._log_event("error", "cloudflared_not_found", "cloudflared not installed")
                return False

            cmd = ["cloudflared", "tunnel", "--no-autoupdate", "run", "--token", self.token]
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            self.store.update_health(self.tunnel_id, health_status="up", error_code=None, error_message=None)
            self._log_event("info", "tunnel_start", f"Tunnel {self.tunnel_name} started")

            self._should_stop = False
            self.monitor_thread = threading.Thread(target=self._monitor_process, daemon=True)
            self.monitor_thread.start()
            return True

        except Exception as e:
            logger.error("Failed to start tunnel: %s", e, exc_info=True)
            self._log_event("error", "tunnel_start_failed", str(e))
            self.store.update_health(self.tunnel_id, health_status="down", error_code="START_FAILED", error_message=str(e))
            return False

    def stop(self) -> None:
        self._should_stop = True

        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                logger.error("Error stopping tunnel: %s", e)
            finally:
                self.process = None

        self.store.update_health(self.tunnel_id, health_status="down", error_code="STOPPED", error_message="Manually stopped")
        self._log_event("info", "tunnel_stop", f"Tunnel {self.tunnel_name} stopped")

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def _check_cloudflared(self) -> bool:
        try:
            result = subprocess.run(["cloudflared", "--version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def _monitor_process(self) -> None:
        while not self._should_stop:
            if not self.process or self.process.poll() is not None:
                exit_code = self.process.returncode if self.process else -1
                logger.warning("Tunnel process exited with code %s", exit_code)

                stderr = ""
                if self.process and self.process.stderr:
                    try:
                        stderr = self.process.stderr.read()
                    except Exception:
                        stderr = ""

                self.store.update_health(
                    self.tunnel_id,
                    health_status="down",
                    error_code=f"EXIT_{exit_code}",
                    error_message=stderr[:500] if stderr else "Process exited",
                )
                self._log_event(
                    "error",
                    "cloudflared_exit",
                    f"Process exited with code {exit_code}",
                    {"exit_code": exit_code, "stderr": stderr[:500]},
                )
                break

            if self.process.stdout:
                try:
                    line = self.process.stdout.readline()
                    if line:
                        self._parse_cloudflared_output(line)
                except Exception:
                    pass

            time.sleep(1)

    def _parse_cloudflared_output(self, line: str) -> None:
        try:
            if "error" in line.lower():
                self._log_event("warn", "cloudflared_warning", line[:200])
        except Exception:
            pass

    def _log_event(self, level: str, event_type: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        import uuid

        from octopusos.core.time import utc_now_ms

        event = {
            "event_id": str(uuid.uuid4()),
            "tunnel_id": self.tunnel_id,
            "level": level,
            "event_type": event_type,
            "message": message,
            "data_json": json.dumps(data) if data else None,
            "created_at": utc_now_ms(),
        }

        try:
            self.store.append_event(event)
        except Exception as e:
            logger.error("Failed to log event: %s", e)

