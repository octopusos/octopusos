#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

SCAN_PATHS = [
    Path("apps/webui/src"),
    Path("apps/webui/tests/e2e/specs"),
    Path("apps/webui/tests/e2e/utils"),
    Path("apps/webui/vite.config.ts"),
    Path("apps/webui/playwright.config.ts"),
    Path("apps/webui/package.json"),
    Path(".github/workflows/ci.yml"),
]

FILE_EXT_ALLOWLIST = {".ts", ".tsx", ".js", ".mjs", ".cjs", ".json", ".yml", ".yaml"}
IGNORE_FILES = {
    Path("apps/webui/src/ui/text/dict.en.ts"),
    Path("apps/webui/src/ui/text/dict.zh.ts"),
    Path("apps/webui/src/modules/__examples__/usage-example.ts"),
}

PATTERNS = [
    re.compile(r":(?:5173|5174|8080|9090)\b"),
    re.compile(r"localhost:\d+"),
    re.compile(r"127\.0\.0\.1:\d+"),
    re.compile(r"https?://[^/\s]+:\d+"),
    re.compile(r"wss?://[^/\s]+:\d+"),
]


def iter_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_PATHS:
        if not root.exists():
            continue
        if root.is_file():
            if root in IGNORE_FILES:
                continue
            files.append(root)
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix in FILE_EXT_ALLOWLIST:
                if p in IGNORE_FILES:
                    continue
                files.append(p)
    return files


def main() -> int:
    violations: list[tuple[Path, int, str]] = []
    for file in iter_files():
        try:
            text = file.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            for pattern in PATTERNS:
                if pattern.search(line):
                    violations.append((file, i, line.strip()))
                    break

    if violations:
        print("Found hardcoded web endpoint/port patterns:")
        for file, line_no, line in violations:
            print(f"- {file}:{line_no}: {line}")
        return 1

    print("No hardcoded web endpoint/port patterns found in guarded paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
