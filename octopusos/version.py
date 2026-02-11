"""Centralized application version metadata."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VERSION_FILE = _REPO_ROOT / "VERSION"


def _read_release_version() -> str:
    try:
        return _VERSION_FILE.read_text(encoding="utf-8").strip() or "0.0"
    except OSError:
        return "0.0"


APP_NAME = "AgentOS"
WEBUI_NAME = "AgentOS WebUI"
RELEASE_VERSION = _read_release_version()
BUILD_VERSION = RELEASE_VERSION

