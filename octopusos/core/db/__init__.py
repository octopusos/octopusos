"""Database components for OctopusOS.

Provides specialized database utilities for reliable SQLite operations.

Components:
- writer: Single-threaded write serialization with retry logic
- registry_db: Unified database access entry point (REQUIRED for all DB access)
"""

from octopusos.core.db.writer import SQLiteWriter
from octopusos.core.db import registry_db

__all__ = ["SQLiteWriter", "registry_db"]
