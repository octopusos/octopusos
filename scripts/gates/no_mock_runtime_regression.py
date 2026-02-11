#!/usr/bin/env python3
"""Fail-fast gate for mock/placeholder regressions in runtime code."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

RUNTIME_ROOTS = (
    ROOT / "apps" / "webui" / "src",
    ROOT / "os" / "octopusos" / "webui",
)

ALLOW_PATH_PARTS = (
    "/tests/",
    "/test/",
    "/fixtures/",
    "/demos/",
    "/__mocks__/",
)

ALLOW_FILE_SUFFIXES = (
    ".spec.ts",
    ".spec.tsx",
    ".test.ts",
    ".test.tsx",
)

RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("frontend_mock_dataset", re.compile(r"\bMOCK_[A-Z0-9_]+\b")),
    ("backend_mock_return", re.compile(r'return\s+["\']mock["\']')),
    ("authgate_always_true", re.compile(r"always return true", re.IGNORECASE)),
    ("test_minimal_router", re.compile(r"minimal CRUD for tests", re.IGNORECASE)),
    ("empty_chat_end", re.compile(r'"type"\s*:\s*"message\.end"[\s\S]{0,120}"content"\s*:\s*""')),
)


def _is_allowed(path: Path) -> bool:
    raw = path.as_posix()
    if any(part in raw for part in ALLOW_PATH_PARTS):
        return True
    if raw.endswith(ALLOW_FILE_SUFFIXES):
        return True
    return False


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for root in RUNTIME_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in {".py", ".ts", ".tsx"}:
                continue
            if _is_allowed(path):
                continue
            files.append(path)
    return files


def main() -> int:
    findings: list[str] = []
    for path in _iter_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for rule_name, pattern in RULES:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path.relative_to(ROOT)}:{line}: [{rule_name}] {match.group(0)[:120]}")

    if findings:
        print("no-mock-runtime gate failed. Found runtime mock/placeholder patterns:\n")
        for item in findings:
            print(f"- {item}")
        return 1

    print("no-mock-runtime gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
