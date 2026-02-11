"""Runtime dependency installer helpers."""

from __future__ import annotations

import platform
import shutil
import subprocess
from typing import List, Tuple

from octopusos.core.mcp.preflight import PreflightReport


def _run(cmd: List[str], timeout_s: int = 900) -> Tuple[int, str, str]:
    process = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    return process.returncode, (process.stdout or "").strip(), (process.stderr or "").strip()


def ensure_aws_cli_if_needed(report: PreflightReport) -> tuple[bool, str]:
    """Install aws-cli on macOS Homebrew path when preflight indicates missing aws."""
    has_aws = any(check.name == "aws_cli_present" and check.ok for check in report.checks)
    if has_aws:
        return False, "aws-cli already present"

    if platform.system().lower() != "darwin":
        return False, "auto-install not supported on this OS"

    brew_path = shutil.which("brew")
    if not brew_path:
        return False, "Homebrew not found; cannot auto-install aws-cli."

    code, out, err = _run(["brew", "install", "awscli"])
    if code != 0:
        return False, f"brew install awscli failed: {err or out or 'unknown error'}"

    code, out, err = _run(["aws", "--version"], timeout_s=30)
    if code != 0:
        return False, f"aws-cli verification failed after install: {err or out or 'unknown error'}"

    return True, f"Installed aws-cli via Homebrew. {out or err}"
