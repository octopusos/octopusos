#!/usr/bin/env python3
"""
Gate G-AP-TUI: AnswerPack TUI Interface Requirements

Validates:
1. CLI supports --ui [cli|tui] switch for AnswerPack create
2. TUI entrypoint exists and is wired from CLI
3. TUI module provides a callable run_answer_tui()
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def check_cli_ui_flag():
    cli_file = PROJECT_ROOT / "octopusos" / "cli" / "answers.py"
    if not cli_file.exists():
        return False, "Answers CLI file not found"
    content = _read(cli_file)
    if "--ui" not in content:
        return False, "Missing --ui option in answers CLI"
    if "click.Choice([\"cli\", \"tui\"])" not in content and "click.Choice(['cli', 'tui'])" not in content:
        return False, "UI option should include cli/tui choices"
    return True, "--ui flag with cli/tui choices present"


def check_tui_entrypoint():
    cli_file = PROJECT_ROOT / "octopusos" / "cli" / "answers.py"
    content = _read(cli_file)
    if "run_answer_tui" not in content:
        return False, "CLI does not reference run_answer_tui"
    return True, "CLI references run_answer_tui"


def check_tui_module():
    tui_file = PROJECT_ROOT / "octopusos" / "ui" / "answer_tui.py"
    if not tui_file.exists():
        return False, "answer_tui.py not found"
    content = _read(tui_file)
    if "def run_answer_tui" not in content:
        return False, "run_answer_tui() not defined"
    return True, "TUI module and entrypoint present"


def main():
    print("🔒 Gate G-AP-TUI: AnswerPack TUI Interface Requirements")
    print("=" * 60)

    checks = [
        ("CLI --ui Flag", check_cli_ui_flag),
        ("CLI TUI Wiring", check_tui_entrypoint),
        ("TUI Module", check_tui_module),
    ]

    all_passed = True
    for name, fn in checks:
        passed, message = fn()
        status = "✓" if passed else "✗"
        print(f"{status} {name}: {message}")
        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("✅ Gate G-AP-TUI PASSED")
        return 0
    print("❌ Gate G-AP-TUI FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
