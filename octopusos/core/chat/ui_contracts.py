from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from jsonschema import Draft202012Validator


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema_path = Path(__file__).resolve().parents[2] / "schemas" / "ui_contracts.v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def validate_ui_contract(ui: Dict[str, Any]) -> None:
    """
    Validate UI contract payload against frozen v1 schema.

    Raises:
        ValueError: when payload violates schema.
    """
    errors = sorted(_validator().iter_errors(ui), key=lambda e: e.path)
    if not errors:
        return
    first = errors[0]
    path = ".".join(str(p) for p in first.path) or "<root>"
    raise ValueError(f"Invalid UI contract at {path}: {first.message}")

