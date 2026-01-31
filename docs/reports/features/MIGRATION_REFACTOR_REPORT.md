# 数据库迁移系统重构报告

## 📋 问题分析

### 原始问题
```
迁移路径: v0.10.0 → v0.8.0
错误信息: Migration stopped at v0.10.0
解决建议: 没有从 v0.10.0 到 v0.8.0 的完整迁移路径
```

### 根本原因

1. **版本号硬编码** ❌
   - `LATEST_VERSION = "0.8.0"` 硬编码在代码中
   - 实际已有 v0.10.0 迁移文件，但代码不知道

2. **迁移脚本位置混乱** ❌
   - 部分在 `schema_vXX.sql` (v02-v06)
   - 部分在 `migrations/` 目录 (v07-v10)
   - 没有统一管理

3. **重复的迁移函数** ❌
   - `migrate_v07_to_v08` 定义了两次（105行和295行）
   - 一个处理 vector_embeddings，一个处理 chat
   - v08 有两个不同的迁移文件

4. **版本读取错误** ❌
   - 按时间戳排序读取版本
   - 当多个迁移在同一秒执行时，版本号混乱

## ✅ 解决方案

### 1. 动态版本扫描

**before**:
```python
LATEST_VERSION = "0.8.0"  # 硬编码
```

**after**:
```python
def get_latest_version(migrations_dir: Path) -> Optional[str]:
    """从文件系统自动扫描最新版本"""
    migrations = scan_available_migrations(migrations_dir)
    return migrations[-1][0] if migrations else None
```

### 2. 统一迁移文件位置

**before**:
```
agentos/store/
├── schema_v02.sql
├── schema_v03.sql
├── schema_v04.sql
├── schema_v05.sql
├── schema_v06.sql
└── migrations/
    ├── v07_project_kb.sql
    ├── v08_chat.sql
    ├── v08_vector_embeddings.sql  ❌ 重复
    ├── v09_command_history.sql
    └── v10_fix_fts_triggers.sql
```

**after**:
```
agentos/store/
├── migrations/
│   ├── README.md
│   ├── v06_task_driven.sql      ✅ 新增
│   ├── v07_project_kb.sql
│   ├── v08_chat.sql             ✅ 合并 chat + vector_embeddings
│   ├── v09_command_history.sql
│   └── v10_fix_fts_triggers.sql
└── schema_v*.sql  (保留用于向后兼容)
```

### 3. 自动迁移链构建

**before**:
```python
# 手动维护迁移链
migrations_chain = [
    ("0.5.0", "0.6.0", migrate_v05_to_v06, "Task-Driven Architecture"),
    ("0.6.0", "0.7.0", migrate_v06_to_v07, "ProjectKB"),
    # ... 需要手动添加
]
```

**after**:
```python
def build_migration_chain(migrations_dir, from_version, to_version):
    """自动从文件系统构建迁移链"""
    all_migrations = scan_available_migrations(migrations_dir)
    # 自动计算路径
    chain = []
    for version, description, filepath in all_migrations:
        if from_version < version <= to_version:
            chain.append((prev_version, version, filepath, description))
    return chain
```

### 4. 修复版本读取逻辑

**before**:
```python
def get_current_version(conn):
    result = conn.execute(
        "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1"
    ).fetchone()  # ❌ 时间戳可能相同
```

**after**:
```python
def get_current_version(conn):
    results = conn.execute("SELECT version FROM schema_version").fetchall()
    versions = [row[0] for row in results]
    # 语义版本排序: 0.5.0 < 0.6.0 < 0.10.0
    versions.sort(key=lambda v: tuple(map(int, v.split('.'))))
    return versions[-1]  # ✅ 返回最大版本号
```

## 🎯 核心改进

### 1. 零配置添加新迁移

只需：
1. 在 `migrations/` 目录创建 `vXX_feature_name.sql`
2. 系统自动识别并加入迁移链

**无需**：
- 修改 Python 代码
- 更新 `LATEST_VERSION`
- 手动添加迁移函数

### 2. 命名规范自动解析

文件名 → 版本号：
```
v06_task_driven.sql      → 0.6.0 (Task Driven)
v07_project_kb.sql       → 0.7.0 (Project Kb)
v10_fix_fts_triggers.sql → 0.10.0 (Fix Fts Triggers)
```

### 3. 迁移路径自动计算

```bash
# 从数据库读取当前版本：0.6.0
# 从文件系统读取最新版本：0.10.0
# 自动构建路径：0.6.0 → 0.7.0 → 0.8.0 → 0.9.0 → 0.10.0
```

## 📊 测试结果

### 测试用例 1: 完整迁移 (0.5.0 → 0.10.0)

```bash
$ python3 test_migration.py
```

**输出**:
```
╔══════════════════════════════════════════════════════════════════
║ 数据库迁移计划
╠══════════════════════════════════════════════════════════════════
║ 数据库: test.db
║ 当前版本: v0.5.0
║ 目标版本: v0.10.0
║ 迁移步骤: 5 个
╠══════════════════════════════════════════════════════════════════
║ 迁移链:
║  1. v0.5.0 → v0.6.0: Task Driven
║  2. v0.6.0 → v0.7.0: Project Kb
║  3. v0.7.0 → v0.8.0: Chat
║  4. v0.8.0 → v0.9.0: Command History
║  5. v0.9.0 → v0.10.0: Fix Fts Triggers
╚══════════════════════════════════════════════════════════════════

🔄 [1/5] Migrating v0.5.0 → v0.6.0
✅ Migration v0.5.0 → v0.6.0 completed

🔄 [2/5] Migrating v0.6.0 → v0.7.0
✅ Migration v0.6.0 → v0.7.0 completed

🔄 [3/5] Migrating v0.7.0 → v0.8.0
✅ Migration v0.7.0 → v0.8.0 completed

🔄 [4/5] Migrating v0.8.0 → v0.9.0
✅ Migration v0.8.0 → v0.9.0 completed

🔄 [5/5] Migrating v0.9.0 → v0.10.0
✅ Migration v0.9.0 → v0.10.0 completed

╔══════════════════════════════════════════════════════════════════
║ 迁移成功完成 🎉
╠══════════════════════════════════════════════════════════════════
║ 最终版本: v0.10.0
║ 执行步骤: 5 个迁移
╚══════════════════════════════════════════════════════════════════

✅ Migration test passed!
```

### 测试用例 2: 列出可用迁移

```bash
$ python3 -m agentos.store.migrations list
```

**输出**:
```
╔══════════════════════════════════════════════════════════════════
║ Available Migrations
╠══════════════════════════════════════════════════════════════════
║ Latest Version: v0.10.0
║ Total Migrations: 5
╠══════════════════════════════════════════════════════════════════
║ Migration Files:
║  • v0.6.0: Task Driven
║    v06_task_driven.sql
║  • v0.7.0: Project Kb
║    v07_project_kb.sql
║  • v0.8.0: Chat
║    v08_chat.sql
║  • v0.9.0: Command History
║    v09_command_history.sql
║  • v0.10.0: Fix Fts Triggers
║    v10_fix_fts_triggers.sql
╚══════════════════════════════════════════════════════════════════
```

## 🔄 使用方式

### 列出可用迁移
```bash
python3 -m agentos.store.migrations list
```

### 迁移到最新版本
```bash
python3 -m agentos.store.migrations migrate
```

### 迁移到指定版本
```bash
python3 -m agentos.store.migrations migrate 0.8.0
```

## 📝 添加新迁移

### 步骤 1: 创建迁移文件

在 `agentos/store/migrations/` 创建新文件：

```sql
-- migrations/v11_new_feature.sql

-- Migration v0.11.0: New Feature Description

CREATE TABLE IF NOT EXISTS new_table (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

-- Update schema version
INSERT OR REPLACE INTO schema_version (version, applied_at) 
VALUES ('0.11.0', datetime('now'));
```

### 步骤 2: 验证

```bash
# 查看是否识别
python3 -m agentos.store.migrations list

# 应该显示:
# ║  • v0.11.0: New Feature
# ║    v11_new_feature.sql
```

### 步骤 3: 测试迁移

```bash
# 创建测试数据库
sqlite3 test.db "CREATE TABLE schema_version (version TEXT PRIMARY KEY); 
                 INSERT INTO schema_version VALUES ('0.10.0');"

# 执行迁移
python3 -m agentos.store.migrations migrate

# 应该显示:
# 🔄 [1/1] Migrating v0.10.0 → v0.11.0
# ✅ Migration v0.10.0 → v0.11.0 completed
```

**完成！** 无需修改任何 Python 代码。

## 🚫 禁止的做法

### ❌ 不要硬编码版本号
```python
# ❌ 错误
LATEST_VERSION = "0.11.0"

# ✅ 正确
latest_version = get_latest_version(migrations_dir)
```

### ❌ 不要手动维护迁移函数
```python
# ❌ 错误
def migrate_v11_to_v12(conn):
    # ... SQL logic ...
    pass

migrations_chain.append(("0.11.0", "0.12.0", migrate_v11_to_v12))

# ✅ 正确
# 创建 v12_feature.sql 文件即可，系统自动处理
```

### ❌ 不要在多个地方存放迁移文件
```python
# ❌ 错误
agentos/store/schema_v11.sql  # 不要放这里

# ✅ 正确
agentos/store/migrations/v11_feature.sql
```

## 📈 性能和可靠性

### 版本冲突处理
- 使用 `INSERT OR REPLACE` 确保幂等性
- 同一版本多次执行不会失败

### 事务保护
- 每个迁移在独立事务中执行
- 失败自动回滚，不影响其他迁移

### 错误提示
- 详细的错误信息和建议
- 显示迁移路径和当前状态

## 🎉 总结

### 改进前
- ❌ 版本号硬编码
- ❌ 迁移文件分散
- ❌ 手动维护迁移链
- ❌ 版本读取逻辑错误

### 改进后
- ✅ 自动扫描版本
- ✅ 统一迁移目录
- ✅ 自动构建迁移链
- ✅ 语义版本排序
- ✅ 零配置添加迁移

### 核心价值
**添加新迁移：从 3 个步骤 → 1 个步骤**
1. ~~修改 Python 代码~~
2. ~~更新版本号~~
3. 创建 SQL 文件 ✅

---

**日期**: 2026-01-27  
**状态**: ✅ 完成  
**测试**: ✅ 通过
