# 数据库迁移 v08 缺失问题修复

## 🐛 问题描述

**用户报告**:
- Chat 功能报错: `⚠️ Chat engine error: no such table: chat_messages`
- 数据库版本显示为 0.12.0（最新）
- 但 chat_messages 和 chat_sessions 表不存在

**期望行为**:
- 数据库迁移到 0.12.0 时应该包含所有之前版本的表
- chat_messages 和 chat_sessions 表应该存在（v08 引入）

---

## 🔍 根本原因

### 数据库迁移链断裂

#### 问题数据库状态

**store/registry.sqlite**:
```sql
-- schema_version 表只有 3 条记录
SELECT version, applied_at FROM schema_version ORDER BY version;
0.10.0|2026-01-26 11:10:34
0.11.0|2026-01-26 23:01:50
0.12.0|2026-01-27 14:25:24

-- 缺少 v0.2.0 到 v0.9.0 的记录！
```

**缺失的迁移**:
- v02 - v06: 早期迁移
- **v07_project_kb.sql** (0.7.0) - ProjectKB 相关表
- **v08_chat.sql** (0.8.0) - **chat_sessions 和 chat_messages 表** ← 关键缺失
- **v09_command_history.sql** (0.9.0) - command_history 相关表

#### 为什么会发生？

可能的原因：

1. **数据库从中间版本开始**
   - 数据库不是从 0.1.0/0.2.0 开始初始化的
   - 可能从某个备份或快照恢复的
   - 直接创建了 0.10.0 或更高版本

2. **迁移脚本跳过了 v02-v09**
   - 可能使用了 `CREATE TABLE IF NOT EXISTS` 导致部分表已存在
   - 迁移系统认为已完成，但实际缺少某些表

3. **手动数据库操作**
   - 可能有人手动修改了 schema_version 表
   - 或者手动删除了部分表但保留了版本记录

#### 实际影响

```bash
# 查看所有表
$ sqlite3 store/registry.sqlite ".tables"
artifacts               kb_embeddings
command_history         kb_index_meta
context_snapshot_items  kb_sources
context_snapshots       pinned_commands
kb_chunks              schema_capabilities
kb_chunks_fts          schema_version
kb_chunks_fts_*        task_*
kb_embedding_meta      webui_*

# ❌ 缺少 chat_sessions 和 chat_messages
```

### ChatEngine 错误

**agentos/core/chat/engine.py**:
```python
# ChatEngine 尝试查询 chat_messages 表
cursor.execute("SELECT * FROM chat_messages WHERE session_id = ?", (session_id,))
# ❌ sqlite3.OperationalError: no such table: chat_messages
```

---

## ✅ 修复方案

### 手动执行缺失的 v08 迁移

由于迁移链断裂，自动迁移系统无法检测到缺失的中间版本。需要手动执行 v08_chat.sql。

### 修复步骤

#### 1. 确认问题

```bash
# 检查当前版本
$ sqlite3 store/registry.sqlite "SELECT MAX(version) FROM schema_version;"
0.12.0

# 检查是否有 chat 表
$ sqlite3 store/registry.sqlite "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'chat%';"
# (无输出 - 表不存在)

# 检查迁移记录
$ sqlite3 store/registry.sqlite "SELECT version FROM schema_version ORDER BY version;"
0.10.0
0.11.0
0.12.0
# ❌ 缺少 0.2.0 到 0.9.0
```

#### 2. 手动执行 v08_chat.sql

```bash
# 执行 v08 迁移脚本
$ sqlite3 store/registry.sqlite < agentos/store/migrations/v08_chat.sql

# 验证表已创建
$ sqlite3 store/registry.sqlite "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'chat%';"
chat_sessions
chat_messages
# ✅ 表已创建
```

#### 3. 重启服务器

```bash
$ ./scripts/quick_restart.sh
✅ WebUI restarted successfully
🌐 http://127.0.0.1:8080
```

---

## 🧪 验证修复

### 验证表已创建

```sql
-- 查看 chat_sessions 表结构
sqlite> .schema chat_sessions
CREATE TABLE chat_sessions (
    session_id TEXT PRIMARY KEY,
    title TEXT,
    task_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);
CREATE INDEX idx_chat_sessions_task ON chat_sessions(task_id);
CREATE INDEX idx_chat_sessions_created ON chat_sessions(created_at DESC);
CREATE INDEX idx_chat_sessions_updated ON chat_sessions(updated_at DESC);

-- 查看 chat_messages 表结构
sqlite> .schema chat_messages
CREATE TABLE chat_messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
);
CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_role ON chat_messages(role);
CREATE INDEX idx_chat_messages_created ON chat_messages(created_at DESC);
```

### 测试 Chat 功能

**Step 1: 打开 Chat 页面**
1. 访问 http://127.0.0.1:8080
2. 点击左侧导航 "Chat"
3. ✅ WebSocket 状态显示 "Connected"

**Step 2: 选择模型**
1. Provider: `llama.cpp`
2. Model: `qwen2.5-coder-7b-instruct-q8_0.gguf`
3. ✅ Provider 状态显示 "Ready (XXms)"

**Step 3: 发送消息**
1. 输入: "你好"
2. 点击发送
3. ✅ 应该收到 AI 回复
4. ❌ 如果还是报错，检查后端日志

**Step 4: 检查数据库**
```bash
# 查看是否有消息记录
$ sqlite3 store/registry.sqlite "SELECT COUNT(*) FROM chat_messages;"
# 应该 > 0

$ sqlite3 store/registry.sqlite "SELECT COUNT(*) FROM chat_sessions;"
# 应该 > 0
```

---

## 📊 完整的迁移版本对照

| 版本 | 文件 | 主要内容 | 状态 |
|------|------|---------|------|
| 0.2.0 | v02_*.sql | 基础表结构 | ❌ 缺失 |
| 0.3.0 | v03_*.sql | 基础功能 | ❌ 缺失 |
| 0.4.0 | v04_*.sql | 基础功能 | ❌ 缺失 |
| 0.5.0 | v05_*.sql | 基础功能 | ❌ 缺失 |
| 0.6.0 | v06_task_driven.sql | Task-driven 架构 | ❌ 缺失 |
| 0.7.0 | v07_project_kb.sql | ProjectKB 知识库 | ❌ 缺失 |
| **0.8.0** | **v08_chat.sql** | **Chat 功能（关键）** | ❌ 缺失 → ✅ 已修复 |
| 0.9.0 | v09_command_history.sql | Command History | ❌ 缺失 |
| 0.10.0 | v10_fix_fts_triggers.sql | FTS 触发器修复 | ✅ 已应用 |
| 0.11.0 | v11_context_governance.sql | Context 治理 | ✅ 已应用 |
| 0.12.0 | v12_task_routing.sql | Task 路由 | ✅ 已应用 |

### 为什么 v07/v09 不需要手动执行？

检查表的存在情况：

```bash
$ sqlite3 store/registry.sqlite ".tables" | grep -E "kb_|command_history"
command_history         ✅ v09 的表存在（可能通过其他方式创建）
kb_chunks              ✅ v07 的表存在
kb_embeddings          ✅
kb_sources             ✅
```

**结论**：
- v07 和 v09 的表已经存在（可能通过其他机制创建）
- 只有 v08 的表完全缺失
- 所以只需要手动执行 v08

---

## 💡 根本原因分析

### 迁移系统的假设

**agentos/store/migrations.py** 的设计假设：

```python
def migrate(db_path, target_version=None):
    # 1. 获取当前版本
    current_version = get_current_version(conn)  # e.g., "0.12.0"

    # 2. 构建迁移链
    migration_chain = build_migration_chain(
        migrations_dir,
        current_version,    # from: "0.12.0"
        target_version      # to: "0.12.0"
    )

    # 3. 如果 from == to，跳过迁移
    if current_version == target_version:
        logger.info("✅ 已经是目标版本，无需迁移")
        return
```

**问题**：
- 迁移系统只检查版本号，不验证表是否真的存在
- 如果 schema_version 表中有 0.12.0 记录，就认为所有 ≤ 0.12.0 的迁移都已完成
- **实际上中间版本的迁移可能从未执行**

### 如何避免此问题？

#### 方案 1: 添加表存在性检查

```python
def verify_migration_completeness(conn, version):
    """验证指定版本的所有表是否存在"""
    expected_tables = {
        '0.8.0': ['chat_sessions', 'chat_messages'],
        '0.9.0': ['command_history', 'pinned_commands'],
        # ...
    }

    if version not in expected_tables:
        return True

    cursor = conn.cursor()
    for table in expected_tables[version]:
        result = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        ).fetchone()

        if not result:
            return False

    return True
```

#### 方案 2: 幂等迁移脚本

所有迁移脚本使用 `CREATE TABLE IF NOT EXISTS`：

```sql
-- ✅ 幂等的，可以重复执行
CREATE TABLE IF NOT EXISTS chat_sessions (...);

-- ❌ 非幂等的，第二次执行会报错
CREATE TABLE chat_sessions (...);
```

**v08_chat.sql 已经使用了 IF NOT EXISTS**，所以重复执行是安全的。

#### 方案 3: 迁移验证命令

添加 `verify` 命令来检查迁移完整性：

```bash
$ python -m agentos.store.migrations verify
Checking migration completeness...
✅ v0.10.0: All tables present
✅ v0.11.0: All tables present
✅ v0.12.0: All tables present
❌ v0.8.0: Missing tables: chat_sessions, chat_messages
⚠️  Database migration incomplete!
```

---

## 🚨 预防措施

### 1. 定期验证数据库完整性

```bash
# 添加到 CI/CD 流程
scripts/verify_db_schema.sh
```

### 2. 备份数据库

```bash
# 迁移前备份
cp store/registry.sqlite store/registry.sqlite.backup.$(date +%Y%m%d)

# 迁移后验证
python -m agentos.store.migrations verify
```

### 3. 使用迁移日志

在每次迁移时记录详细日志：

```python
# 记录迁移前的表列表
before_tables = get_table_list(conn)

# 执行迁移
execute_migration(...)

# 记录迁移后的表列表
after_tables = get_table_list(conn)

# 记录变化
new_tables = after_tables - before_tables
logger.info(f"New tables created: {new_tables}")
```

---

## ✅ 验收清单

- [x] 检查数据库版本（0.12.0）
- [x] 检查 schema_version 表（只有 0.10-0.12）
- [x] 发现缺少 chat 表
- [x] 手动执行 v08_chat.sql
- [x] 验证 chat_sessions 表已创建
- [x] 验证 chat_messages 表已创建
- [x] 重启 WebUI 服务器
- [ ] 测试 Chat 功能正常
- [ ] 验证消息可以正常保存到数据库

---

## 📋 相关文档

- **Chat 消息处理修复**: `docs/bugfixes/CHAT_MESSAGE_HANDLING_FIX.md`
- **WebSocket 状态修复**: `docs/bugfixes/WEBSOCKET_STATUS_FIX.md`
- **数据库迁移系统**: `agentos/store/migrations.py`
- **v08 迁移脚本**: `agentos/store/migrations/v08_chat.sql`

---

**修复完成时间**: 2026-01-28
**受影响的数据库**: `store/registry.sqlite`
**手动执行的迁移**: v08_chat.sql
**需要操作**: 测试 Chat 功能
