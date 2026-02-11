"""
Maintenance services for OctopusOS

This module provides maintenance and housekeeping services including:
- Temporary file cleanup
- Log rotation
- Database optimization
- Cache management
"""

from octopusos.core.maintenance.temp_cleanup import (
    cleanup_old_temp_files,
    get_temp_dir_stats,
    schedule_cleanup_task,
)
from octopusos.core.maintenance.cleanup import DatabaseCleaner


def cleanup_orphans(days_old: int = 30, dry_run: bool = False):
    """Convenience wrapper for orphan task cleanup."""
    cleaner = DatabaseCleaner()
    result = cleaner.cleanup_orphan_tasks(days_old=days_old, dry_run=dry_run)
    return 0 if dry_run else result.get("deleted_count", 0)

__all__ = [
    "cleanup_old_temp_files",
    "get_temp_dir_stats",
    "schedule_cleanup_task",
    "DatabaseCleaner",
    "cleanup_orphans",
]
