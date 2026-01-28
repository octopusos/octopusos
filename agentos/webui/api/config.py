"""
Config API - Configuration viewing

GET /api/config - Get current configuration (read-only)
GET /api/config/migrations - Get database migration status
POST /api/config/migrations/migrate - Run database migrations
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import sqlite3
from pathlib import Path

from agentos import __version__

router = APIRouter()


class ConfigResponse(BaseModel):
    """Configuration response"""
    version: str
    python_version: str
    environment: Dict[str, Any]
    settings: Dict[str, Any]


class MigrationInfo(BaseModel):
    """Single migration info"""
    version: str
    description: str
    filename: str


class MigrationsStatusResponse(BaseModel):
    """Database migrations status"""
    current_version: Optional[str]
    latest_version: Optional[str]
    pending_count: int
    migrations: List[MigrationInfo]
    needs_migration: bool
    db_path: str


class MigrateRequest(BaseModel):
    """Migration request"""
    target_version: Optional[str] = None


class MigrateResponse(BaseModel):
    """Migration response"""
    success: bool
    message: str
    from_version: Optional[str]
    to_version: Optional[str]
    migrations_executed: int


@router.get("")
async def get_config() -> ConfigResponse:
    """
    Get current configuration (read-only)

    Returns:
        Current configuration
    """
    import sys

    # Get environment variables (filter sensitive ones)
    env_vars = {
        k: v for k, v in os.environ.items()
        if not any(sensitive in k.upper() for sensitive in ["KEY", "SECRET", "TOKEN", "PASSWORD"])
    }

    # Load settings if available
    settings = {}
    try:
        from agentos.config import load_settings
        s = load_settings()
        settings = {
            "language": getattr(s, "language", "en"),
        }
    except Exception:
        pass

    return ConfigResponse(
        version=__version__,
        python_version=sys.version,
        environment=env_vars,
        settings=settings,
    )


@router.get("/migrations")
async def get_migrations_status() -> MigrationsStatusResponse:
    """
    Get database migration status

    Returns:
        Current migration status and available migrations
    """
    from agentos.store.migrations import (
        get_current_version,
        get_latest_version,
        scan_available_migrations
    )
    from agentos.store import get_db_path

    try:
        db_path = get_db_path()
        migrations_dir = Path(__file__).parent.parent.parent / "store" / "migrations"

        # Get current version from database
        current_version = None
        try:
            conn = sqlite3.connect(str(db_path))
            current_version = get_current_version(conn)
            conn.close()
        except Exception as e:
            print(f"Failed to get current version: {e}")

        # Get available migrations
        latest_version = get_latest_version(migrations_dir)
        all_migrations = scan_available_migrations(migrations_dir)

        # Calculate pending migrations
        pending_count = 0
        if current_version and latest_version:
            current_parts = tuple(map(int, current_version.split('.')))
            for version, _, _ in all_migrations:
                version_parts = tuple(map(int, version.split('.')))
                if version_parts > current_parts:
                    pending_count += 1

        # Build migrations list
        migrations_list = [
            MigrationInfo(
                version=version,
                description=description,
                filename=filepath.name
            )
            for version, description, filepath in all_migrations
        ]

        needs_migration = current_version != latest_version if current_version and latest_version else False

        return MigrationsStatusResponse(
            current_version=current_version,
            latest_version=latest_version,
            pending_count=pending_count,
            migrations=migrations_list,
            needs_migration=needs_migration,
            db_path=str(db_path)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get migration status: {str(e)}")


@router.post("/migrations/migrate")
async def run_migrations(request: MigrateRequest) -> MigrateResponse:
    """
    Run database migrations

    Args:
        request: Migration request with optional target version

    Returns:
        Migration result
    """
    from agentos.store.migrations import migrate, get_current_version, MigrationError
    from agentos.store import get_db_path

    try:
        db_path = get_db_path()

        # Get current version before migration
        conn = sqlite3.connect(str(db_path))
        from_version = get_current_version(conn)
        conn.close()

        # Run migrations
        try:
            migrate(db_path, request.target_version)
        except MigrationError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Get final version after migration
        conn = sqlite3.connect(str(db_path))
        to_version = get_current_version(conn)
        conn.close()

        # Calculate migrations executed
        migrations_executed = 0
        if from_version and to_version and from_version != to_version:
            from_parts = tuple(map(int, from_version.split('.')))
            to_parts = tuple(map(int, to_version.split('.')))
            migrations_executed = to_parts[1] - from_parts[1]

        return MigrateResponse(
            success=True,
            message=f"Successfully migrated from v{from_version} to v{to_version}",
            from_version=from_version,
            to_version=to_version,
            migrations_executed=migrations_executed
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")
