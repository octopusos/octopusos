"""Secret ref resolution and existence checks."""

from __future__ import annotations

import json
from pathlib import Path

from octopusos.webui.secrets import SecretStore


def is_secret_ref(value: str) -> bool:
    return isinstance(value, str) and value.startswith("secret://")


def _candidate_secret_files() -> list[Path]:
    home = Path.home()
    return [
        home / ".octopusos" / "secrets" / "providers.json",
        home / ".octopusos" / "secrets.json",
    ]


def secret_exists(ref: str) -> bool:
    return resolve_secret_ref(ref) is not None


def resolve_secret_ref(ref: str) -> str | None:
    if not is_secret_ref(ref):
        return None

    raw_path = ref[len("secret://") :].strip("/")
    if not raw_path:
        return None
    parts = [p for p in raw_path.split("/") if p]
    if not parts:
        return None

    # Prefer encrypted SecretStore if available.
    try:
        store = SecretStore()
        v = store.get(ref)
        if isinstance(v, str) and v:
            return v
    except Exception:
        pass

    for file_path in _candidate_secret_files():
        if not file_path.exists():
            continue
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        node = payload
        ok = True
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                ok = False
                break
        if ok and isinstance(node, str):
            # Support encrypted values stored by SecretStore.
            if node.startswith("enc:"):
                try:
                    store = SecretStore()
                    dec = store.get(ref)
                    return dec
                except Exception:
                    return None
            return node
    return None
