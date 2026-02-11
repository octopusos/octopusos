"""Local encrypted SecretStore for secret:// refs.

This is intentionally simple and file-backed:
- Secrets are stored in ~/.octopusos/secrets.json
- Values are encrypted using Fernet with a local master key file
- Reads are compatible with secret_resolver via the `enc:` prefix

Security notes:
- This is local-desktop storage. Ensure permissions are 0600 on key + secrets file.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet


def _octopusos_dir() -> Path:
    override = os.environ.get("OCTOPUSOS_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".octopusos"


def _secrets_file() -> Path:
    return _octopusos_dir() / "secrets.json"


def _master_key_file() -> Path:
    return _octopusos_dir() / "secrets" / "master.key"


def _ensure_0600(path: Path) -> None:
    try:
        if os.name != "posix":
            return
        path.chmod(0o600)
    except Exception:
        pass


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    _ensure_0600(path)


def _get_fernet() -> Fernet:
    key_path = _master_key_file()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if not key_path.exists():
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        _ensure_0600(key_path)
    else:
        key = key_path.read_bytes()
    return Fernet(key)


class SecretStore:
    """Store secret strings at a secret:// path, encrypted at rest."""

    def __init__(self) -> None:
        self._path = _secrets_file()
        self._fernet = _get_fernet()

    def get(self, ref: str) -> Optional[str]:
        if not isinstance(ref, str) or not ref.startswith("secret://"):
            return None
        raw_path = ref[len("secret://") :].strip("/")
        if not raw_path:
            return None
        parts = [p for p in raw_path.split("/") if p]
        if not parts:
            return None

        payload = _load_json(self._path)
        node: Any = payload
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return None

        if not isinstance(node, str):
            return None
        if not node.startswith("enc:"):
            # Allow plaintext fallback (legacy)
            return node

        token = node[len("enc:") :].encode("utf-8")
        try:
            return self._fernet.decrypt(token).decode("utf-8")
        except Exception:
            return None

    def set(self, ref: str, value: str) -> None:
        if not isinstance(ref, str) or not ref.startswith("secret://"):
            raise ValueError("invalid secret ref")
        raw_path = ref[len("secret://") :].strip("/")
        if not raw_path:
            raise ValueError("invalid secret path")
        parts = [p for p in raw_path.split("/") if p]
        if not parts:
            raise ValueError("invalid secret path")

        payload = _load_json(self._path)
        node: Dict[str, Any] = payload
        for part in parts[:-1]:
            child = node.get(part)
            if not isinstance(child, dict):
                child = {}
                node[part] = child
            node = child

        enc = self._fernet.encrypt((value or "").encode("utf-8")).decode("utf-8")
        node[parts[-1]] = f"enc:{enc}"
        _write_json_atomic(self._path, payload)

    def delete(self, ref: str) -> None:
        if not isinstance(ref, str) or not ref.startswith("secret://"):
            return
        raw_path = ref[len("secret://") :].strip("/")
        parts = [p for p in raw_path.split("/") if p]
        if not parts:
            return

        payload = _load_json(self._path)
        node: Any = payload
        parents: list[tuple[Dict[str, Any], str]] = []
        for part in parts:
            if isinstance(node, dict) and part in node:
                parents.append((node, part))
                node = node[part]
            else:
                return

        # delete leaf
        parent, key = parents[-1]
        parent.pop(key, None)
        _write_json_atomic(self._path, payload)
