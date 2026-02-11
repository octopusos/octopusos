#!/usr/bin/env python3
"""Enhanced Gate: Enforce single DB entry point with extended pattern detection.

This script extends gate_no_sqlite_connect.py with additional checks to prevent:
1. Creating new Store classes (dual-table systems)
2. Direct SQL table creation (session/message tables)
3. Bypassing registry_db for DB path access
4. Hardcoded database file paths

Exit codes:
- 0: Success (no violations found)
- 1: Violations found

Usage:
    python scripts/gates/gate_no_sqlite_connect_enhanced.py
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

# Root directory for scanning
ROOT_DIR = Path(__file__).parent.parent.parent / "octopusos"

# Whitelist: Files that are allowed to use restricted patterns
WHITELIST = {
    # Core DB infrastructure
    "octopusos/core/db/registry_db.py",
    "octopusos/core/db/writer.py",

    # Store initialization and migration
    "octopusos/store/__init__.py",
    "octopusos/store/migrator.py",
    "octopusos/store/connection_factory.py",
    "octopusos/store/migrations.py",
    "octopusos/cli/migrate.py",
    "octopusos/store/migrations/run_pr3_migration.py",
    "octopusos/store/migrations/run_p0_migration.py",  # P0 migration script
    "octopusos/store/migrations/run_p2_migration.py",  # P2 migration script

    # Legacy code (to be migrated)
    "octopusos/core/brain/service/query_impact.py",
    "octopusos/core/brain/service/query_subgraph.py",
    "octopusos/core/brain/service/query_trace.py",
    "octopusos/core/brain/service/query_why.py",
    "octopusos/core/brain/store/sqlite_schema.py",
    "octopusos/core/brain/store/sqlite_store.py",
    "octopusos/core/capabilities/policy.py",
    "octopusos/core/chat/budget_audit.py",
    "octopusos/core/chat/budget_recommender.py",
    "octopusos/core/chat/context_builder.py",
    "octopusos/core/chat/context_diff.py",
    "octopusos/core/chat/summarizer.py",
    "octopusos/core/checkpoints/evidence.py",
    "octopusos/core/checkpoints/manager.py",
    "octopusos/core/command/history.py",
    "octopusos/core/communication/network_mode.py",
    "octopusos/core/communication/storage/sqlite_store.py",
    "octopusos/core/content/facade.py",
    "octopusos/core/content/lineage.py",
    "octopusos/core/content/registry.py",
    "octopusos/core/extensions/registry.py",
    "octopusos/core/governance/orchestration/consumer.py",
    "octopusos/core/guardian/storage.py",
    "octopusos/core/idempotency/store.py",
    "octopusos/core/lead/adapters/storage.py",
    "octopusos/core/lead/dedupe.py",
    "octopusos/core/locks/file_lock.py",
    "octopusos/core/locks/task_lock.py",
    "octopusos/core/logging/store.py",
    "octopusos/core/memory/service.py",
    "octopusos/core/orchestrator/patch_tracker.py",
    "octopusos/core/project/repo_service.py",
    "octopusos/core/project/repository.py",
    "octopusos/core/project/service.py",
    "octopusos/core/project_kb/embedding/manager.py",
    "octopusos/core/project_kb/indexer.py",
    "octopusos/core/project_kb/searcher.py",
    "octopusos/core/project_kb/service.py",
    "octopusos/core/recovery/recovery_sweep.py",
    "octopusos/core/review/pack_generator.py",
    "octopusos/core/startup/health_check.py",
    "octopusos/core/supervisor/adapters/audit_adapter.py",
    "octopusos/core/supervisor/inbox.py",
    "octopusos/core/supervisor/poller.py",
    "octopusos/core/supervisor/supervisor.py",
    "octopusos/core/task/artifact_service_v31.py",
    "octopusos/core/task/binding_service.py",
    "octopusos/core/task/lineage_extensions.py",
    "octopusos/core/task/manager.py",
    "octopusos/core/task/project_settings_inheritance.py",
    "octopusos/core/task/replay_task_lifecycle.py",
    "octopusos/core/task/spec_service.py",
    "octopusos/core/task/state_machine.py",
    "octopusos/core/task/task_repo_service.py",
    "octopusos/jobs/memory_gc.py",
    "octopusos/router/persistence.py",
    "octopusos/store/answers_store.py",
    "octopusos/store/content_store.py",
    "octopusos/store/scripts/backfill_audit_decision_fields.py",
    "octopusos/store/scripts/test_backfill.py",
    "octopusos/store/test_utils.py",
    "octopusos/webui/api/config.py",
    "octopusos/webui/api/governance.py",
    "octopusos/webui/store/session_store.py",

    # Module-specific database paths (not registry.sqlite)
    "octopusos/core/database.py",  # Config system with env var support
    "octopusos/core/brain/service/index_job.py",  # BrainOS-specific DB (.brainos/index.db)
    "octopusos/core/communication/evidence.py",  # CommunicationOS-specific DB (communication.db)
    "octopusos/jobs/lead_scan.py",  # Lead scan DB (store.db)
    "octopusos/webui/api/brain.py",  # BrainOS WebUI DB (v0.1_mvp.db)
    "octopusos/webui/api/brain_governance.py",  # BrainOS governance DB (brain.db)
    "octopusos/webui/app.py",  # LogStore with env var fallback
    "octopusos/core/git/ignore.py",  # False positive: Thumbs.db is Windows file, not DB
}

# Extended forbidden patterns
FORBIDDEN_PATTERNS = {
    # Direct DB connections
    "direct_connect": [
        r"sqlite3\.connect\s*\(",
        r"apsw\.Connection\s*\(",
    ],

    # Creating new Store classes (prevents dual-table systems)
    "new_store_classes": [
        r"class\s+\w*SessionStore\s*\(",
        r"class\s+\w*MessageStore\s*\(",
        r"class\s+\w*ChatStore\s*\(",
        r"class\s+WebUI\w*Store\s*\(",
    ],

    # Direct SQL table creation (should only be in migrations)
    "table_creation": [
        r"CREATE\s+TABLE\s+.*sessions",
        r"CREATE\s+TABLE\s+.*messages",
        r"CREATE\s+TABLE\s+.*webui_",
    ],

    # Direct DB path access (should only use registry_db)
    "db_path_access": [
        r"def\s+get_db_path\s*\(",
        r"OCTOPUSOS_DB_PATH",
    ],

    # Hardcoded database files
    "hardcoded_db": [
        r'["\'].*\.sqlite["\']',
        r'["\'].*\.db["\']',
    ],
}

# Directories to exclude
EXCLUDE_DIRS = {
    "tests",
    "test",
    "__pycache__",
    ".git",
    ".pytest_cache",
    "venv",
    "env",
    ".venv",
    "node_modules",
}


def is_whitelisted(file_path: Path) -> bool:
    """Check if file is whitelisted."""
    try:
        rel_path = file_path.relative_to(Path(__file__).parent.parent.parent)
        rel_str = str(rel_path).replace(os.sep, "/")
        return rel_str in WHITELIST
    except ValueError:
        return False


def scan_file(file_path: Path) -> Dict[str, List[Tuple[int, str]]]:
    """Scan a single file for all forbidden patterns.

    Returns:
        Dictionary mapping pattern category to list of (line_number, line_content)
    """
    violations = {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")

            for category, patterns in FORBIDDEN_PATTERNS.items():
                category_violations = []

                for line_num, line in enumerate(lines, start=1):
                    # Skip comments and docstrings
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                        continue

                    for pattern in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            category_violations.append((line_num, line.strip()))

                if category_violations:
                    violations[category] = category_violations

    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)

    return violations


def scan_directory(root: Path) -> Dict[Path, Dict[str, List[Tuple[int, str]]]]:
    """Scan directory recursively for violations."""
    all_violations = {}

    for path in root.rglob("*.py"):
        # Skip excluded directories
        if any(excluded in path.parts for excluded in EXCLUDE_DIRS):
            continue

        # Skip whitelisted files
        if is_whitelisted(path):
            continue

        # Scan file
        violations = scan_file(path)
        if violations:
            all_violations[path] = violations

    return all_violations


def print_report(violations: Dict[Path, Dict[str, List[Tuple[int, str]]]]) -> None:
    """Print detailed violation report."""
    print("=" * 80)
    print("Enhanced DB Access Gate: Multi-Pattern Enforcement")
    print("=" * 80)
    print()

    if not violations:
        print("✓ PASS: No violations found")
        print()
        print("All checks passed:")
        print("  - No direct sqlite3.connect() usage")
        print("  - No duplicate Store classes")
        print("  - No SQL table creation in code")
        print("  - No direct DB path access")
        print("  - No hardcoded database files")
        return

    print(f"✗ FAIL: Found {len(violations)} file(s) with violations")
    print()

    # Group by category
    category_counts = {}
    for file_violations in violations.values():
        for category in file_violations.keys():
            category_counts[category] = category_counts.get(category, 0) + 1

    print("Violation Summary:")
    for category, count in sorted(category_counts.items()):
        print(f"  - {category}: {count} file(s)")
    print()

    # Detailed violations
    for file_path, file_violations in sorted(violations.items()):
        rel_path = file_path.relative_to(Path(__file__).parent.parent.parent)
        print(f"File: {rel_path}")

        for category, category_violations in file_violations.items():
            print(f"  Category: {category}")
            for line_num, line_content in category_violations:
                print(f"    Line {line_num}: {line_content}")
        print()

    print("=" * 80)
    print("Required Actions:")
    print("=" * 80)
    print()
    print("1. Direct connections - Replace with:")
    print("   from octopusos.core.db import registry_db")
    print("   conn = registry_db.get_db()")
    print()
    print("2. New Store classes - DO NOT CREATE. Use existing stores.")
    print()
    print("3. Table creation - Move to migration scripts in octopusos/store/migrations/")
    print()
    print("4. DB path access - Use registry_db._get_db_path() only in registry_db.py")
    print()
    print("5. Hardcoded DB files - Use environment variable OCTOPUSOS_DB_PATH")
    print()


def main() -> int:
    """Main entry point."""
    print(f"Scanning: {ROOT_DIR}")
    print(f"Whitelist: {len(WHITELIST)} file(s)")
    print(f"Pattern categories: {len(FORBIDDEN_PATTERNS)}")
    print()

    # Scan for violations
    violations = scan_directory(ROOT_DIR)

    # Print report
    print_report(violations)

    # Return exit code
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
