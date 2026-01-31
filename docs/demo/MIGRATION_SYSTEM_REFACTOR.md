# Database Migration System 重构报告

## 🎯 问题背景

在检查 `agentos/store/` 目录时，发现了严重的**命名不一致问题**：

### 原有命名混乱

1. **外层 schema 文件**：使用语义化版本号 `0.x.0`
   - `schema_v02.sql` → v0.2.0
   - `schema_v03.sql` → v0.3.0
   - `schema_v04.sql` → v0.4.0
   - `schema_v05.sql` → v0.5.0
   - `schema_v06.sql` → v0.6.0

2. **migrations/ 目录**：使用简化版本号 `vXX`（与外层不一致）
   - `v12_project_kb.sql` → v1.2？
   - `v13_vector_embeddings.sql` → v1.3？
   - `v14_command_history.sql` → v1.4？
   - `v14_fix_fts_triggers.sql` → v1.4 补丁？

3. **migrations.py** 只处理 v0.5.0 → v0.6.0 的迁移，**完全没有处理 migrations/ 目录中的文件**！

### 潜在风险

- ❌ 迁移文件可能被遗漏执行
- ❌ 版本号混乱导致无法追踪
- ❌ schema_version 表未更新（migrations/ 中的文件没有更新版本号）
- ❌ 无法进行自动化迁移管理

---

## ✅ 解决方案

### 1. 统一命名规范

将 `migrations/` 目录中的文件重命名为与外层一致的格式：

```
v12_project_kb.sql       → v07_project_kb.sql       (0.7.0)
v13_vector_embeddings.sql → v08_vector_embeddings.sql (0.8.0)
v14_command_history.sql   → v09_command_history.sql   (0.9.0)
v14_fix_fts_triggers.sql  → v10_fix_fts_triggers.sql  (0.10.0)
```

### 2. 修复 SQL 文件

为每个迁移 SQL 文件添加版本号更新语句：

```sql
-- 在每个迁移文件末尾添加
UPDATE schema_version SET version = '0.x.0' WHERE version = '0.(x-1).0';
```

### 3. 重写 migrations.py

#### 新增迁移函数

- `migrate_v06_to_v07()` - Project KB 表结构
- `migrate_v07_to_v08()` - Vector Embeddings
- `migrate_v08_to_v09()` - Command History
- `migrate_v09_to_v10()` - Fix FTS Triggers

#### 新增回滚函数

- `rollback_v10_to_v09()` - 回滚 FTS 修复
- `rollback_v09_to_v08()` - 删除 Command History
- `rollback_v08_to_v07()` - 删除 Vector Embeddings
- `rollback_v07_to_v06()` - 删除 ProjectKB

#### 升级 migrate() 函数

使用**迁移链机制**，自动执行一系列连续迁移：

```python
migrations_chain = [
    ("0.5.0", "0.6.0", migrate_v05_to_v06),
    ("0.6.0", "0.7.0", migrate_v06_to_v07),
    ("0.7.0", "0.8.0", migrate_v07_to_v08),
    ("0.8.0", "0.9.0", migrate_v08_to_v09),
    ("0.9.0", "0.10.0", migrate_v09_to_v10),
]
```

#### 升级 CLI

支持灵活的迁移和回滚：

```bash
# 迁移到最新版本（默认 0.10.0）
python migrations.py migrate

# 迁移到指定版本
python migrations.py migrate 0.8.0

# 回滚到指定版本
python migrations.py rollback 0.7.0
```

---

## 📦 修改文件清单

### 重命名的文件

- ✅ `migrations/v12_project_kb.sql` → `migrations/v07_project_kb.sql`
- ✅ `migrations/v13_vector_embeddings.sql` → `migrations/v08_vector_embeddings.sql`
- ✅ `migrations/v14_command_history.sql` → `migrations/v09_command_history.sql`
- ✅ `migrations/v14_fix_fts_triggers.sql` → `migrations/v10_fix_fts_triggers.sql`

### 修改的文件

- ✅ `migrations/v07_project_kb.sql`
  - 更新版本号标识（v1.2 → v0.7.0）
  - 添加 `UPDATE schema_version` 语句
  - 修正元数据键名（`schema_version` → `kb_schema_version`）

- ✅ `migrations/v08_vector_embeddings.sql`
  - 更新版本号标识（v13 → v0.8.0）
  - 添加 `UPDATE schema_version` 语句

- ✅ `migrations/v09_command_history.sql`
  - 更新版本号标识（v14 → v0.9.0）
  - 添加 `UPDATE schema_version` 语句

- ✅ `migrations/v10_fix_fts_triggers.sql`
  - 更新版本号标识（v14 → v0.10.0）
  - 添加 `UPDATE schema_version` 语句
  - 修正注释中的旧版本引用

- ✅ `migrations.py`
  - 新增 4 个迁移函数（v06→v07, v07→v08, v08→v09, v09→v10）
  - 新增 4 个回滚函数（v10→v09, v09→v08, v08→v07, v07→v06）
  - 重写 `migrate()` 函数（支持迁移链）
  - 重写 CLI（支持指定目标版本）

---

## 🔧 使用指南

### 检查当前版本

```python
from agentos.store.migrations import get_current_version
import sqlite3
from agentos.store import get_db_path

conn = sqlite3.connect(str(get_db_path()))
print(get_current_version(conn))  # 例如: '0.6.0'
conn.close()
```

### 迁移到最新版本

```bash
cd /Users/pangge/PycharmProjects/AgentOS
python -m agentos.store.migrations migrate
```

### 迁移到指定版本

```bash
# 从 0.6.0 迁移到 0.8.0（会自动执行 v06→v07→v08）
python -m agentos.store.migrations migrate 0.8.0
```

### 回滚到旧版本

```bash
# 从 0.10.0 回滚到 0.7.0（会自动执行 v10→v09→v08→v07）
python -m agentos.store.migrations rollback 0.7.0
```

⚠️ **警告**：回滚会删除数据！

- v10→v09: 恢复旧 FTS 触发器（无数据丢失）
- v09→v08: 删除 `command_history`, `pinned_commands` 表
- v08→v07: 删除 `kb_embeddings`, `kb_embedding_meta` 表
- v07→v06: 删除所有 ProjectKB 表（`kb_sources`, `kb_chunks`, `kb_chunks_fts` 等）

---

## 📐 版本映射表

| 版本号 | 功能描述 | 迁移文件 |
|--------|----------|----------|
| v0.5.0 | 基础表结构 | schema_v05.sql |
| v0.6.0 | Task-Driven Architecture | schema_v06.sql |
| v0.7.0 | ProjectKB（文档知识库） | migrations/v07_project_kb.sql |
| v0.8.0 | Vector Embeddings | migrations/v08_vector_embeddings.sql |
| v0.9.0 | Command History | migrations/v09_command_history.sql |
| v0.10.0 | Fix FTS Triggers | migrations/v10_fix_fts_triggers.sql |

---

## 🚦 迁移链机制

**核心逻辑**：

```python
# 从当前版本 A 迁移到目标版本 C
# 自动执行中间所有迁移 A→B→C

current = "0.6.0"
target = "0.9.0"

# 自动执行:
# 1. migrate_v06_to_v07(conn)  → 0.7.0
# 2. migrate_v07_to_v08(conn)  → 0.8.0
# 3. migrate_v08_to_v09(conn)  → 0.9.0
```

**优势**：

- ✅ 不再需要手动执行多个脚本
- ✅ 保证迁移顺序正确
- ✅ 每次迁移后验证版本号
- ✅ 支持跨版本升级/降级

---

## 🧪 验证测试

### 测试计划

1. **测试迁移链**（v0.6.0 → v0.10.0）
   ```bash
   # 创建 v0.6.0 数据库
   python -c "from agentos.store import init_db; init_db()"
   
   # 迁移到最新版本
   python -m agentos.store.migrations migrate
   
   # 验证版本号
   sqlite3 ~/.agentos/store/registry.sqlite "SELECT version FROM schema_version"
   # 期望输出: 0.10.0
   
   # 验证表存在
   sqlite3 ~/.agentos/store/registry.sqlite ".tables"
   # 应包含: kb_sources, kb_chunks, kb_chunks_fts, command_history, pinned_commands
   ```

2. **测试部分迁移**（v0.6.0 → v0.8.0）
   ```bash
   python -m agentos.store.migrations migrate 0.8.0
   
   # 验证
   sqlite3 ~/.agentos/store/registry.sqlite "SELECT version FROM schema_version"
   # 期望输出: 0.8.0
   
   # command_history 不应该存在
   sqlite3 ~/.agentos/store/registry.sqlite "SELECT name FROM sqlite_master WHERE type='table' AND name='command_history'"
   # 期望输出: (空)
   ```

3. **测试回滚**（v0.10.0 → v0.7.0）
   ```bash
   python -m agentos.store.migrations rollback 0.7.0
   
   # 验证
   sqlite3 ~/.agentos/store/registry.sqlite "SELECT version FROM schema_version"
   # 期望输出: 0.7.0
   
   # kb_embeddings, command_history 不应该存在
   sqlite3 ~/.agentos/store/registry.sqlite "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('kb_embeddings', 'command_history')"
   # 期望输出: (空)
   ```

---

## 📋 最佳实践

### 1. 添加新迁移时

1. 创建 SQL 文件：`migrations/v{N+1}_feature_name.sql`
   - 版本号：使用 0.{N+1}.0（N = 当前最新版本号）
   - 结尾添加：`UPDATE schema_version SET version = '0.{N+1}.0' WHERE version = '0.{N}.0';`

2. 在 `migrations.py` 中添加：
   ```python
   def migrate_v{N}_to_v{N+1}(conn: sqlite3.Connection) -> None:
       """docstring"""
       cursor = conn.cursor()
       try:
           schema_path = Path(__file__).parent / "migrations" / "v{N+1}_feature_name.sql"
           with open(schema_path) as f:
               schema_sql = f.read()
           cursor.executescript(schema_sql)
           conn.commit()
           logger.info(f"Migration v0.{N}.0 -> v0.{N+1}.0 completed")
       except Exception as e:
           conn.rollback()
           logger.error(f"Migration failed: {e}")
           raise
   ```

3. 添加到 `migrations_chain`：
   ```python
   migrations_chain = [
       # ... existing migrations ...
       ("0.{N}.0", "0.{N+1}.0", migrate_v{N}_to_v{N+1}),
   ]
   ```

4. 添加对应的 rollback 函数

### 2. 迁移前备份

```bash
cp ~/.agentos/store/registry.sqlite ~/.agentos/store/registry.sqlite.backup
```

### 3. 使用日志

迁移时启用详细日志：

```python
import logging
logging.basicConfig(level=logging.INFO)

from agentos.store.migrations import migrate
from agentos.store import get_db_path

migrate(get_db_path(), "0.10.0")
```

---

## 🎉 总结

### 修复成果

- ✅ **统一命名规范**：所有迁移文件使用 `v0{N}_feature_name.sql` 格式
- ✅ **完整迁移链**：v0.5.0 → v0.6.0 → v0.7.0 → v0.8.0 → v0.9.0 → v0.10.0
- ✅ **自动化执行**：支持跨版本升级/降级
- ✅ **版本追踪**：每次迁移正确更新 `schema_version` 表
- ✅ **易于扩展**：新增迁移只需 3 步（SQL + 函数 + 链注册）

### 后续建议

1. **添加单元测试**（`tests/store/test_migrations.py`）
   - 测试每个迁移函数的幂等性
   - 测试回滚功能
   - 测试版本号更新

2. **添加迁移文档生成器**
   - 自动生成 CHANGELOG.md
   - 列出每个版本的表结构变更

3. **集成到 init_db()**
   - 在 `agentos/store/__init__.py` 的 `init_db()` 中自动检测版本并迁移

4. **添加数据迁移支持**（目前只支持 DDL）
   - 支持 DML 数据转换
   - 例如：v0.7.0 添加 ProjectKB 后，可能需要导入历史文档

---

**状态**: ✅ 完成  
**日期**: 2026-01-26  
**影响范围**: `agentos/store/migrations.py` + 4 个 SQL 文件  
**向后兼容**: 是（从 v0.6.0 开始）  
**破坏性变更**: 无
