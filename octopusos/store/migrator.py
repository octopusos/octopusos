"""Database Migration System

自动检测并执行未应用的迁移文件。
迁移文件命名规范：schema_vXX.sql (XX 为两位数版本号)

特性：
1. 自动检测未应用的迁移
2. 按版本号顺序执行
3. 幂等性保证（IF NOT EXISTS）
4. 事务支持（每个迁移文件一个事务）
5. 版本追踪（schema_version 表）
"""

import logging
import re
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """迁移执行错误"""
    pass


class Migrator:
    """数据库迁移管理器"""

    def __init__(self, db_path: Path, migrations_dir: Path, component: Optional[str] = None):
        """
        初始化迁移器

        Args:
            db_path: 数据库文件路径
            migrations_dir: 迁移文件目录
        """
        self.db_path = db_path
        self.migrations_dir = migrations_dir
        self.component = component or self._infer_component_from_db_path(db_path)

    @staticmethod
    def _infer_component_from_db_path(db_path: Path) -> str:
        """Infer storage component from ~/.octopusos/store/<component>/db.sqlite."""
        parts = db_path.resolve().parts
        try:
            store_idx = parts.index("store")
        except ValueError:
            return "octopusos"
        if store_idx + 1 >= len(parts):
            return "octopusos"
        return parts[store_idx + 1]

    def _allow_migration_for_component(self, sql_file: Path) -> bool:
        """Filter out migrations that belong to other OS components."""
        name = sql_file.name.lower()
        tokens = {
            "memoryos": ("memory",),
            "networkos": ("networkos", "network_", "tunnel_"),
            "brainos": ("brain", "classifier", "decision_record", "info_need"),
        }
        component_tokens = tokens.get(self.component, ())
        if component_tokens:
            return any(token in name for token in component_tokens)

        # OctopusOS must not apply component-owned migrations.
        cross_tokens = (
            "networkos", "network_", "tunnel_",
            "memory_", "memoryos",
            "brain_", "classifier", "decision_record", "info_need",
        )
        return not any(token in name for token in cross_tokens)

    def get_current_version(self, conn: sqlite3.Connection) -> int:
        """
        获取当前数据库版本

        Args:
            conn: 数据库连接

        Returns:
            当前版本号（整数），如果没有版本表返回 0
        """
        versions: List[int] = []

        for table_name in ("schema_versions", "schema_version"):
            if not self._table_exists(conn, table_name):
                continue
            try:
                cursor = conn.execute(
                    f"SELECT version FROM {table_name} ORDER BY version DESC"
                )
                rows = cursor.fetchall()
            except sqlite3.OperationalError:
                continue

            for row in rows:
                version_str = row[0]
                match = re.search(r'0\.(\d+)\.', version_str)
                if match:
                    versions.append(int(match.group(1)))
                match_v = re.search(r'v(\d+)$', version_str)
                if match_v:
                    versions.append(int(match_v.group(1)))

        return max(versions) if versions else 0

    def get_available_migrations(self) -> List[Tuple[int, Path]]:
        """
        获取所有Available的迁移文件

        Returns:
            (版本号, 文件路径) 元组列表，按版本号排序
        """
        migrations = []

        # 匹配 schema_vXX.sql 或 schema_vXX_suffix.sql 格式
        pattern = re.compile(r'schema_v(\d+)(?:_[a-z_]+)?\.sql')

        for sql_file in self.migrations_dir.glob('schema_v*.sql'):
            if not self._allow_migration_for_component(sql_file):
                continue
            match = pattern.match(sql_file.name)
            if match:
                version = int(match.group(1))
                migrations.append((version, sql_file))

        # 按版本号排序
        migrations.sort(key=lambda x: x[0])
        return migrations

    def get_pending_migrations(self, conn: sqlite3.Connection) -> List[Tuple[int, Path]]:
        """
        获取待执行的迁移文件

        Args:
            conn: 数据库连接

        Returns:
            待执行的 (版本号, 文件路径) 元组列表
        """
        current_version = self.get_current_version(conn)
        all_migrations = self.get_available_migrations()

        # 过滤出版本号大于当前版本的迁移
        pending = [(v, p) for v, p in all_migrations if v > current_version]

        logger.info(
            f"Current version: v{current_version:02d}, "
            f"Available migrations: {len(all_migrations)}, "
            f"Pending: {len(pending)}"
        )

        return pending

    def execute_migration(
        self,
        conn: sqlite3.Connection,
        version: int,
        migration_file: Path
    ) -> None:
        """
        执行单个迁移文件

        Args:
            conn: 数据库连接
            version: 迁移版本号
            migration_file: 迁移文件路径

        Raises:
            MigrationError: 迁移执行失败
        """
        logger.info(f"Executing migration v{version:02d}: {migration_file.name}")

        try:
            self._ensure_schema_tables(conn)

            if version == 31:
                self._ensure_tasks_project_id_column(conn)
            if version == 18 or version >= 79:
                self._ensure_projects_table(conn)

            # 读取迁移文件
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration_sql = f.read()

            # 执行迁移（在事务中）
            try:
                conn.executescript(migration_sql)
            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                if "duplicate column name" in msg or "already exists" in msg:
                    self._executescript_lenient(conn, migration_sql)
                else:
                    raise

            # 记录版本（如果迁移文件没有自己记录的话）
            for table_name in ("schema_versions", "schema_version"):
                if not self._table_exists(conn, table_name):
                    continue
                cursor = conn.execute(
                    f"SELECT COUNT(*) FROM {table_name} WHERE version LIKE ?",
                    (f'%{version}%',)
                )
                if cursor.fetchone()[0] == 0:
                    conn.execute(
                        f"INSERT INTO {table_name} (version) VALUES (?)",
                        (f'0.{version}.0',)
                    )

            conn.commit()
            logger.info(f"Migration v{version:02d} completed successfully")

        except Exception as e:
            conn.rollback()
            error_msg = f"Migration v{version:02d} failed: {e}"
            logger.error(error_msg, exc_info=True)
            raise MigrationError(error_msg) from e

    def _executescript_lenient(
        self,
        conn: sqlite3.Connection,
        migration_sql: str,
    ) -> None:
        statements = [stmt.strip() for stmt in migration_sql.split(";") if stmt.strip()]
        for stmt in statements:
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                if "duplicate column name" in msg or "already exists" in msg:
                    continue
                raise

    def _ensure_tasks_project_id_column(self, conn: sqlite3.Connection) -> None:
        """Ensure tasks.project_id exists before v31 migration steps reference it."""
        try:
            cursor = conn.execute("PRAGMA table_info(tasks)")
            existing = {row[1] for row in cursor.fetchall()}
            if "project_id" not in existing:
                conn.execute("ALTER TABLE tasks ADD COLUMN project_id TEXT")
        except sqlite3.Error:
            # If tasks table does not exist yet, v31 migration will create needed structures.
            pass

    def _ensure_projects_table(self, conn: sqlite3.Connection) -> None:
        """Ensure base projects table exists before v18 references it."""
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
            )
            if cursor.fetchone() is None:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS projects (
                        id TEXT PRIMARY KEY,
                        path TEXT NOT NULL,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
        except sqlite3.Error:
            pass

    def _table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return cursor.fetchone() is not None

    def _ensure_schema_tables(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_versions (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
            """
        )
        conn.commit()

    def migrate(self) -> int:
        """
        执行所有待应用的迁移

        Returns:
            执行的迁移数量

        Raises:
            MigrationError: 迁移执行失败
        """
        # 确保数据库文件存在
        if not self.db_path.exists():
            raise MigrationError(
                f"Database not found: {self.db_path}. "
                "Please run init_db() first."
            )

        conn = sqlite3.connect(str(self.db_path))

        try:
            # 确保 schema_version(s) 表存在
            self._ensure_schema_tables(conn)

            # 获取待执行的迁移
            pending_migrations = self.get_pending_migrations(conn)

            if not pending_migrations:
                logger.info("No pending migrations")
                return 0

            # 执行迁移
            for version, migration_file in pending_migrations:
                self.execute_migration(conn, version, migration_file)

            logger.info(f"Successfully applied {len(pending_migrations)} migrations")
            return len(pending_migrations)

        finally:
            conn.close()

    def status(self) -> dict:
        """
        获取迁移状态

        Returns:
            状态字典：
            {
                "current_version": int,
                "latest_version": int,
                "pending_count": int,
                "applied_migrations": List[str],
                "pending_migrations": List[str]
            }
        """
        if not self.db_path.exists():
            return {
                "current_version": 0,
                "latest_version": 0,
                "pending_count": 0,
                "applied_migrations": [],
                "pending_migrations": [],
                "error": "Database not found"
            }

        conn = sqlite3.connect(str(self.db_path))

        try:
            # 确保 schema_version(s) 表存在
            self._ensure_schema_tables(conn)

            current_version = self.get_current_version(conn)
            all_migrations = self.get_available_migrations()
            pending_migrations = self.get_pending_migrations(conn)

            latest_version = all_migrations[-1][0] if all_migrations else 0

            applied = [f"v{v:02d}" for v, _ in all_migrations if v <= current_version]
            pending = [f"v{v:02d}" for v, _ in pending_migrations]

            return {
                "current_version": current_version,
                "latest_version": latest_version,
                "pending_count": len(pending_migrations),
                "applied_migrations": applied,
                "pending_migrations": pending
            }

        finally:
            conn.close()


def auto_migrate(db_path: Path) -> int:
    """
    自动执行数据库迁移

    Args:
        db_path: 数据库文件路径

    Returns:
        执行的迁移数量

    Raises:
        MigrationError: 迁移失败
    """
    migrations_dir = Path(__file__).parent / 'migrations'
    migrator = Migrator(db_path, migrations_dir)
    return migrator.migrate()


def get_migration_status(db_path: Path) -> dict:
    """
    获取迁移状态

    Args:
        db_path: 数据库文件路径

    Returns:
        迁移状态字典
    """
    migrations_dir = Path(__file__).parent / 'migrations'
    migrator = Migrator(db_path, migrations_dir)
    return migrator.status()
