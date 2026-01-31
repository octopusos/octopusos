# Database Migration Quick Reference

## 🚀 常用命令

### 查看当前版本

```bash
cd /Users/pangge/PycharmProjects/AgentOS
python3 -c "
import sqlite3
from agentos.store import get_db_path
conn = sqlite3.connect(str(get_db_path()))
result = conn.execute('SELECT version FROM schema_version').fetchone()
print(f'Current version: {result[0] if result else \"Unknown\"}')
conn.close()
"
```

### 迁移到最新版本（0.10.0）

```bash
cd /Users/pangge/PycharmProjects/AgentOS
python3 -m agentos.store.migrations migrate
```

### 迁移到指定版本

```bash
cd /Users/pangge/PycharmProjects/AgentOS
python3 -m agentos.store.migrations migrate 0.8.0
```

### 回滚到旧版本

```bash
cd /Users/pangge/PycharmProjects/AgentOS
python3 -m agentos.store.migrations rollback 0.7.0
```

---

## 📊 版本功能表

| 版本 | 功能 | 包含表 |
|------|------|--------|
| 0.6.0 | Task-Driven Architecture | tasks, task_lineage, task_sessions, task_agents, task_audits |
| 0.7.0 | ProjectKB（文档知识库） | kb_sources, kb_chunks, kb_chunks_fts, kb_index_meta, kb_embeddings |
| 0.8.0 | Vector Embeddings | kb_embeddings (增强), kb_embedding_meta |
| 0.9.0 | Command History | command_history, pinned_commands |
| 0.10.0 | Fix FTS Triggers | 修复 kb_chunks_fts 触发器错误 |

---

## 🔄 迁移链

系统自动处理连续迁移：

```
v0.6.0 → v0.7.0 → v0.8.0 → v0.9.0 → v0.10.0
```

**示例**：从 v0.6.0 迁移到 v0.9.0

```bash
python3 -m agentos.store.migrations migrate 0.9.0
```

自动执行：
1. v0.6.0 → v0.7.0 (ProjectKB)
2. v0.7.0 → v0.8.0 (Vector Embeddings)
3. v0.8.0 → v0.9.0 (Command History)

---

## ⚠️ 注意事项

### 备份数据库

在迁移前务必备份：

```bash
cp ~/.agentos/store/registry.sqlite ~/.agentos/store/registry.sqlite.backup
```

### 回滚会删除数据

| 回滚操作 | 删除的数据 |
|----------|-----------|
| v0.10.0 → v0.9.0 | 无（仅修改触发器） |
| v0.9.0 → v0.8.0 | 所有命令历史记录 |
| v0.8.0 → v0.7.0 | 所有向量嵌入数据 |
| v0.7.0 → v0.6.0 | 所有 KB 数据（文档、chunks、索引） |

### 迁移失败恢复

如果迁移失败，事务会自动回滚：

```bash
# 恢复备份
cp ~/.agentos/store/registry.sqlite.backup ~/.agentos/store/registry.sqlite

# 查看错误日志
python3 -m agentos.store.migrations migrate
```

---

## 🧪 测试迁移

### 测试环境准备

```bash
# 使用测试数据库
export AGENTOS_DB_PATH=/tmp/test_registry.sqlite

# 初始化 v0.6.0 数据库
python3 -c "from agentos.store import init_db; init_db()"

# 测试迁移
python3 -m agentos.store.migrations migrate 0.10.0

# 验证
sqlite3 /tmp/test_registry.sqlite "SELECT version FROM schema_version"
sqlite3 /tmp/test_registry.sqlite ".tables"
```

---

## 📝 添加新迁移

### 步骤 1: 创建 SQL 文件

```bash
# 假设当前最新版本是 0.10.0，新版本是 0.11.0
touch agentos/store/migrations/v11_new_feature.sql
```

SQL 文件内容模板：

```sql
-- Migration v0.11.0: New Feature Description
-- Add new feature tables and indexes

-- 1. 创建新表
CREATE TABLE IF NOT EXISTS new_table (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

-- 2. 创建索引
CREATE INDEX IF NOT EXISTS idx_new_table_created 
ON new_table(created_at DESC);

-- 3. 更新 schema 版本
UPDATE schema_version SET version = '0.11.0' WHERE version = '0.10.0';
```

### 步骤 2: 添加迁移函数

在 `migrations.py` 中添加：

```python
def migrate_v10_to_v11(conn: sqlite3.Connection) -> None:
    """
    Migrate from v0.10.0 to v0.11.0: Add New Feature
    
    This migration adds:
    - new_table (new feature description)
    """
    logger.info("Starting migration from v0.10.0 to v0.11.0 (New Feature)")
    
    cursor = conn.cursor()
    
    try:
        # Read v11_new_feature.sql
        schema_path = Path(__file__).parent / "migrations" / "v11_new_feature.sql"
        with open(schema_path) as f:
            schema_sql = f.read()
        
        # Execute schema
        cursor.executescript(schema_sql)
        
        conn.commit()
        logger.info("Migration v0.10.0 -> v0.11.0 completed successfully")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Migration v0.10.0 -> v0.11.0 failed: {e}")
        raise
```

### 步骤 3: 更新迁移链

在 `migrate()` 函数的 `migrations_chain` 中添加：

```python
migrations_chain = [
    ("0.5.0", "0.6.0", migrate_v05_to_v06),
    ("0.6.0", "0.7.0", migrate_v06_to_v07),
    ("0.7.0", "0.8.0", migrate_v07_to_v08),
    ("0.8.0", "0.9.0", migrate_v08_to_v09),
    ("0.9.0", "0.10.0", migrate_v09_to_v10),
    ("0.10.0", "0.11.0", migrate_v10_to_v11),  # 新增
]
```

### 步骤 4: 添加回滚函数（可选）

```python
def rollback_v11_to_v10(conn: sqlite3.Connection) -> None:
    """
    Rollback from v0.11.0 to v0.10.0: Remove New Feature
    
    WARNING: This will delete new feature data
    """
    logger.warning("Rolling back from v0.11.0 to v0.10.0")
    
    cursor = conn.cursor()
    
    try:
        # Drop new tables
        cursor.execute("DROP TABLE IF EXISTS new_table")
        
        # Update schema version
        cursor.execute("UPDATE schema_version SET version = '0.10.0' WHERE version = '0.11.0'")
        
        conn.commit()
        logger.info("Rollback v0.11.0 -> v0.10.0 completed")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Rollback v0.11.0 -> v0.10.0 failed: {e}")
        raise
```

并更新 `rollback_chain`：

```python
rollback_chain = [
    ("0.11.0", "0.10.0", rollback_v11_to_v10),  # 新增
    ("0.10.0", "0.9.0", rollback_v10_to_v09),
    # ... rest
]
```

---

## 🔍 故障排查

### 问题 1: "Database schema version unknown"

**原因**：数据库中没有 `schema_version` 表

**解决**：

```bash
# 重新初始化数据库
python3 -c "from agentos.store import init_db; init_db()"
```

### 问题 2: "No migration path from X to Y"

**原因**：当前版本和目标版本之间没有定义迁移路径

**解决**：检查版本号是否正确，或者补充缺失的迁移函数

### 问题 3: 迁移过程中断

**原因**：数据库锁定或网络问题

**解决**：

```bash
# 1. 检查数据库是否被占用
lsof ~/.agentos/store/registry.sqlite

# 2. 强制释放锁
rm ~/.agentos/store/registry.sqlite-wal
rm ~/.agentos/store/registry.sqlite-shm

# 3. 恢复备份重试
cp ~/.agentos/store/registry.sqlite.backup ~/.agentos/store/registry.sqlite
python3 -m agentos.store.migrations migrate
```

---

## 📚 相关文档

- 详细报告：`docs/demo/MIGRATION_SYSTEM_REFACTOR.md`
- Schema 定义：`agentos/store/schema_v*.sql`
- 迁移文件：`agentos/store/migrations/v*.sql`

---

**最后更新**: 2026-01-26  
**维护者**: AgentOS Team
