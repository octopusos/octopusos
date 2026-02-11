"""Store module - SQLite database management"""

import logging
import sqlite3
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from octopusos.core.db import SQLiteWriter

from .migrator import auto_migrate, get_migration_status
from .store import Store

logger = logging.getLogger(__name__)

__all__ = [
    "Store",
    "get_db",  # Re-exported from registry_db (DEPRECATED: import from registry_db directly)
    "get_db_path",
    "get_store_path",
    "init_db",
    "ensure_migrations",
    "get_migration_status",
    "get_writer",
    "get_migration_version",
    "apply_migrations",
    "init_factory",
    "get_thread_connection",
    "shutdown_factory",
]

# Global writer instance (singleton per process)
_writer_instance: Optional["SQLiteWriter"] = None
_factory_db_path: Optional[str] = None
_factory_thread_local = None


def get_migration_version(db_path: Path) -> int:
    """Get current migration version for a database."""
    from .migrator import Migrator
    migrations_dir = Path(__file__).parent / "migrations"
    migrator = Migrator(db_path, migrations_dir)
    conn = sqlite3.connect(str(db_path))
    try:
        return migrator.get_current_version(conn)
    finally:
        conn.close()


def apply_migrations(db_path: Path) -> int:
    """Apply pending migrations to a database."""
    return ensure_migrations(db_path)


def init_factory(db_path: str) -> None:
    """Initialize thread-local connection factory."""
    global _factory_db_path, _factory_thread_local
    _factory_db_path = db_path
    if _factory_thread_local is None:
        import threading
        _factory_thread_local = threading.local()


def get_thread_connection() -> sqlite3.Connection:
    """Get a thread-local connection for tests."""
    global _factory_db_path, _factory_thread_local
    if _factory_db_path is None:
        raise RuntimeError("init_factory() must be called before get_thread_connection()")
    if _factory_thread_local is None:
        import threading
        _factory_thread_local = threading.local()
    conn = getattr(_factory_thread_local, "connection", None)
    if conn is None:
        conn = sqlite3.connect(_factory_db_path)
        conn.row_factory = sqlite3.Row
        _factory_thread_local.connection = conn
    return conn


def shutdown_factory() -> None:
    """Shutdown thread-local connection factory."""
    global _factory_thread_local, _factory_db_path
    if _factory_thread_local is not None and hasattr(_factory_thread_local, "connection"):
        try:
            _factory_thread_local.connection.close()
        except Exception:
            pass
        _factory_thread_local.connection = None
    _factory_db_path = None


def get_db_path() -> Path:
    """Get the database path (DEPRECATED: use octopusos.core.storage.paths.component_db_path).

    This function is deprecated and maintained for backward compatibility only.
    New code should use: octopusos.core.storage.paths.component_db_path('octopusos')

    Returns:
        Path to the main database file
    """
    # Lazy import to avoid circular dependency
    from octopusos.core.storage.paths import component_db_path

    warnings.warn(
        "get_db_path() is deprecated. Use octopusos.core.storage.paths.component_db_path('octopusos') instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return component_db_path("octopusos")


def get_store_path(subdir: str = "") -> Path:
    """
    Get a path within the store directory

    Args:
        subdir: Subdirectory name (e.g., "extensions", "logs", "cache")
               If empty, returns the store root directory

    Returns:
        Path to the requested directory

    Examples:
        >>> get_store_path()  # Returns "store/"
        >>> get_store_path("extensions")  # Returns "store/extensions/"
        >>> get_store_path("logs")  # Returns "store/logs/"
    """
    store_root = get_db_path().parent
    if subdir:
        return store_root / subdir
    return store_root


# Lazy import of get_db to avoid circular dependency
# This is done via __getattr__ at the bottom of this file


def init_db(auto_migrate_after_init: bool = True):
    """
    Initialize database with base schema

    工作流程：
    1. 创建空数据库文件
    2. 创建 schema_version 表
    3. 自动执行所有迁移（v01 ~ v23）

    Args:
        auto_migrate_after_init: 是否在初始化后自动执行迁移（默认: True）

    User contract:
    - After running `octopusos init`, all CLI commands must work immediately.
    - Database schema is always up-to-date.
    """
    import sqlite3

    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # 如果数据库已存在，只执行迁移
    if db_path.exists():
        logger.info(f"Database already exists: {db_path}")
        if auto_migrate_after_init:
            migrated = ensure_migrations(db_path)
            if migrated > 0:
                logger.info(f"Applied {migrated} pending migrations")
        return db_path

    # 创建新数据库
    logger.info(f"Creating new database: {db_path}")
    conn = sqlite3.connect(str(db_path))

    try:
        # 只创建 schema_version 表，其他表由迁移创建
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)
        conn.commit()
        logger.info("Database file created with schema_version table")

    finally:
        conn.close()

    # 自动执行所有迁移
    if auto_migrate_after_init:
        logger.info("Running auto-migration...")
        migrated = ensure_migrations(db_path)
        logger.info(f"Applied {migrated} migrations, database is ready")

    return db_path


def ensure_migrations(db_path: Path = None) -> int:
    """
    确保数据库迁移已应用

    自动检测并执行所有未应用的迁移文件。
    程序启动时调用此函数，确保数据库 schema 始终是最新的。

    Args:
        db_path: 数据库路径（可选，默认使用 get_db_path()）

    Returns:
        应用的迁移数量

    Raises:
        MigrationError: 迁移失败
    """
    if db_path is None:
        db_path = get_db_path()

    if not db_path.exists():
        logger.warning(f"Database not found: {db_path}, skipping migrations")
        return 0

    try:
        migrated = auto_migrate(db_path)
        if migrated > 0:
            logger.info(f"Applied {migrated} database migrations")
        return migrated
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise


def get_writer() -> "SQLiteWriter":
    """
    Get global SQLiteWriter instance (singleton per process)

    SQLiteWriter 串行化所有数据库写入操作，解决 SQLite 并发锁问题。

    使用场景：
    - 所有数据库写入（INSERT/UPDATE/DELETE）都应该通过 writer.submit()
    - 读操作仍使用 get_db()（支持并发读）

    Returns:
        SQLiteWriter: 全局单例 writer 实例

    Example:
        >>> writer = get_writer()
        >>> def insert_task(conn):
        ...     conn.execute("INSERT INTO tasks ...")
        >>> writer.submit(insert_task, timeout=10.0)
    """
    # Import here to avoid circular dependency
    from octopusos.core.db import SQLiteWriter

    global _writer_instance
    if _writer_instance is None:
        _writer_instance = SQLiteWriter(str(get_db_path()))
    return _writer_instance


def __getattr__(name):
    """Lazy import for get_db to avoid circular dependencies.

    DEPRECATED: get_db is re-exported from registry_db for backward compatibility.
    Use octopusos.core.db.registry_db.get_db() directly in new code.
    """
    if name == "get_db":
        from octopusos.core.db.registry_db import get_db
        return get_db
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
