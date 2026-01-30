"""Thread-safe SQLite connection factory.

每个线程获取自己的连接,避免跨线程共享。

Design:
- Thread-local storage for connections (one per thread)
- Optimal PRAGMA settings for read operations
- Automatic connection reuse within same thread
- Clean shutdown support

Usage:
    from agentos.store.connection_factory import init_factory, get_thread_connection

    # Initialize once at startup
    init_factory("/path/to/db.sqlite")

    # Get connection in any thread
    conn = get_thread_connection()
    cursor = conn.execute("SELECT * FROM tasks")

    # Each thread gets its own connection automatically
"""

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ConnectionFactory:
    """Thread-local SQLite connection factory.

    Manages separate database connections for each thread to avoid
    cross-thread connection sharing, which can cause SQLite errors.

    Features:
    - Thread-local storage (one connection per thread)
    - WAL mode for better concurrency
    - Configurable busy timeout
    - Foreign key support
    - Row factory for dict-like access

    Thread Safety:
        This class is thread-safe. Each thread gets its own connection
        stored in thread-local storage.
    """

    def __init__(
        self,
        db_path: str,
        busy_timeout: int = 5000,
        enable_wal: bool = True,
        enable_foreign_keys: bool = True
    ):
        """Initialize connection factory.

        Args:
            db_path: Path to SQLite database file
            busy_timeout: Busy timeout in milliseconds (default: 5000)
            enable_wal: Enable WAL mode for better concurrency (default: True)
            enable_foreign_keys: Enable foreign key constraints (default: True)
        """
        self.db_path = db_path
        self.busy_timeout = busy_timeout
        self.enable_wal = enable_wal
        self.enable_foreign_keys = enable_foreign_keys

        # Thread-local storage for connections
        self._local = threading.local()

        logger.info(
            f"ConnectionFactory initialized: db_path={db_path}, "
            f"busy_timeout={busy_timeout}ms, wal={enable_wal}"
        )

    def get_connection(self) -> sqlite3.Connection:
        """Get thread-local connection.

        Returns the existing connection for this thread, or creates a new one
        if this is the first call from this thread.

        Returns:
            sqlite3.Connection: Thread-local database connection

        Thread Safety:
            Safe to call from multiple threads. Each thread gets its own connection.
        """
        # Check if this thread already has a connection
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            # Create new connection for this thread
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._configure_connection(conn)
            self._local.conn = conn

            logger.debug(
                f"Created new connection for thread {threading.current_thread().name}"
            )

        return self._local.conn

    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        """Configure connection with optimal settings.

        Args:
            conn: Connection to configure
        """
        # Enable WAL mode for better concurrency
        if self.enable_wal:
            conn.execute("PRAGMA journal_mode = WAL")

        # Balance performance and safety
        conn.execute("PRAGMA synchronous = NORMAL")

        # Increase lock timeout
        conn.execute(f"PRAGMA busy_timeout = {self.busy_timeout}")

        # Store temp tables in memory
        conn.execute("PRAGMA temp_store = MEMORY")

        # Enable foreign key constraints
        if self.enable_foreign_keys:
            conn.execute("PRAGMA foreign_keys = ON")

        # Use Row factory for dict-like access
        conn.row_factory = sqlite3.Row

    def close_connection(self) -> None:
        """Close thread-local connection.

        Closes the connection for the current thread if one exists.
        Safe to call even if no connection exists.
        """
        if hasattr(self._local, 'conn') and self._local.conn:
            try:
                self._local.conn.close()
                logger.debug(
                    f"Closed connection for thread {threading.current_thread().name}"
                )
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
                self._local.conn = None

    def close_all_connections(self) -> None:
        """Close all connections (all threads).

        Note: This can only close the connection for the current thread.
        Other threads must close their own connections.
        """
        self.close_connection()


# Global factory instance
_factory: Optional[ConnectionFactory] = None
_factory_lock = threading.Lock()


def init_factory(
    db_path: str,
    busy_timeout: int = 5000,
    enable_wal: bool = True,
    enable_foreign_keys: bool = True
) -> ConnectionFactory:
    """Initialize global connection factory.

    Should be called once at application startup.

    Args:
        db_path: Path to SQLite database file
        busy_timeout: Busy timeout in milliseconds (default: 5000)
        enable_wal: Enable WAL mode (default: True)
        enable_foreign_keys: Enable foreign key constraints (default: True)

    Returns:
        ConnectionFactory: Initialized factory instance

    Thread Safety:
        Safe to call from multiple threads. Only the first call will
        create the factory; subsequent calls return the existing instance.
    """
    global _factory

    with _factory_lock:
        if _factory is None:
            _factory = ConnectionFactory(
                db_path=db_path,
                busy_timeout=busy_timeout,
                enable_wal=enable_wal,
                enable_foreign_keys=enable_foreign_keys
            )
            logger.info("Global ConnectionFactory initialized")
        else:
            logger.debug("ConnectionFactory already initialized, returning existing instance")

    return _factory


def get_thread_connection() -> sqlite3.Connection:
    """Get connection for current thread.

    Returns the thread-local connection from the global factory.
    Must call init_factory() first.

    Returns:
        sqlite3.Connection: Thread-local database connection

    Raises:
        RuntimeError: If factory not initialized (call init_factory first)

    Thread Safety:
        Safe to call from multiple threads. Each thread gets its own connection.

    Example:
        >>> init_factory("/path/to/db.sqlite")
        >>> conn = get_thread_connection()
        >>> cursor = conn.execute("SELECT * FROM tasks")
    """
    if _factory is None:
        raise RuntimeError(
            "ConnectionFactory not initialized. Call init_factory() first."
        )

    return _factory.get_connection()


def close_thread_connection() -> None:
    """Close connection for current thread.

    Safe to call even if no connection exists.
    """
    if _factory is not None:
        _factory.close_connection()


def get_factory() -> Optional[ConnectionFactory]:
    """Get global factory instance.

    Returns:
        ConnectionFactory or None if not initialized
    """
    return _factory


def shutdown_factory() -> None:
    """Shutdown global factory.

    Closes connections and clears global instance.
    """
    global _factory

    with _factory_lock:
        if _factory is not None:
            _factory.close_connection()
            _factory = None
            logger.info("ConnectionFactory shut down")
