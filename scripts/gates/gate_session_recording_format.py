#!/usr/bin/env python3
"""Gate: validate recordings/sessions markdown format."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

MESSAGE_RE = re.compile(
    r"^##\s+(\d{4})\s+·\s+(\w+)\s+·\s+([0-9T:+-]{19,})(?:\s+·\s+mid=([A-Za-z0-9_-]+))?$",
    re.MULTILINE,
)
REQUIRED_FRONT_MATTER_KEYS = ("session_id", "created_at", "source")
ROLE_ALLOWLIST = {"user", "assistant", "tool", "system"}
SESSION_FILE_RE = re.compile(r"^\d{8}T\d{6}[+-]\d{4}__.+\.md$")


def _load_front_matter(text: str) -> dict:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML front matter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("front matter closing marker not found")
    yaml_raw = text[4:end]
    data = yaml.safe_load(yaml_raw) or {}
    if not isinstance(data, dict):
        raise ValueError("front matter must be a YAML mapping")
    return data


def _parse_iso(ts: str) -> None:
    try:
        datetime.fromisoformat(ts)
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {ts}") from exc


def validate_session_file(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")

    try:
        front_matter = _load_front_matter(text)
    except ValueError as exc:
        return [f"{path}: {exc}"]

    for key in REQUIRED_FRONT_MATTER_KEYS:
        if key not in front_matter or not front_matter[key]:
            errors.append(f"{path}: missing required front matter key `{key}`")

    created_at = front_matter.get("created_at")
    if created_at:
        try:
            _parse_iso(str(created_at))
        except ValueError as exc:
            errors.append(f"{path}: {exc}")

    messages = list(MESSAGE_RE.finditer(text))
    if not messages:
        return errors

    expected_seq = 1
    for item in messages:
        seq = int(item.group(1))
        role = item.group(2)
        ts = item.group(3).strip()

        if seq != expected_seq:
            errors.append(f"{path}: non-incremental sequence at {seq:04d} (expected {expected_seq:04d})")
        expected_seq = seq + 1

        if role not in ROLE_ALLOWLIST:
            errors.append(f"{path}: invalid role `{role}` in block {seq:04d}")

        try:
            _parse_iso(ts)
        except ValueError as exc:
            errors.append(f"{path}: block {seq:04d} {exc}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate session recording markdown files.")
    parser.add_argument("--root", default="recordings/sessions", help="sessions corpus root path")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"SKIP: directory does not exist: {root}")
        return 0

    files = sorted(
        path
        for path in root.rglob("*.md")
        if SESSION_FILE_RE.match(path.name)
    )
    if not files:
        print(f"SKIP: no markdown files found under {root}")
        return 0

    failures: list[str] = []
    for file_path in files:
        failures.extend(validate_session_file(file_path))

    if failures:
        print("FAIL: session recording format violations found")
        for err in failures:
            print(f" - {err}")
        return 1

    print(f"PASS: {len(files)} session recording file(s) are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
