#!/usr/bin/env python3
"""TL Gate B - Adapters存在性检查"""
import sys
from pathlib import Path

EXIT_CODE, PROJECT_ROOT = 0, Path(__file__).parent.parent.parent

def main():
    global EXIT_CODE
    print("=" * 60 + "\nTL Gate B - Adapters Existence\n" + "=" * 60 + "\n")
    
    files = [
        "octopusos/ext/tools/__init__.py",
        "octopusos/ext/tools/base_adapter.py",
        "octopusos/ext/tools/claude_cli_adapter.py",
        "octopusos/ext/tools/opencode_adapter.py",
        "octopusos/cli/tools.py",
    ]
    
    for f in files:
        if (PROJECT_ROOT / f).exists():
            print(f"✓ {f}")
        else:
            print(f"✗ {f} - NOT FOUND")
            EXIT_CODE = 1
    
    print("\n" + "=" * 60)
    print("✅ TL Gate B: PASSED" if EXIT_CODE == 0 else "❌ TL Gate B: FAILED")
    print("=" * 60)
    return EXIT_CODE

if __name__ == "__main__":
    sys.exit(main())
