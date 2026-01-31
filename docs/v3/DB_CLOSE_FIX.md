# 数据库连接关闭问题 - 完整修复方案

## 问题根源

AgentOS 使用 **thread-local 连接池**（`get_db()` 返回线程单例连接），但部分代码把这个共享连接当成"自己创建的"连接来关闭，导致同一线程的其他代码继续使用时出现 "database is closed" 错误。

### 错误模式（Anti-Pattern）

```python
def _get_conn(self) -> sqlite3.Connection:
    if self.db_path:
        conn = sqlite3.connect(str(self.db_path))  # ✅ 自己创建的
    else:
        conn = get_db()  # ❌ 线程共享的单例
    return conn

def save_data(self, data):
    conn = self._get_conn()
    conn.execute("INSERT INTO ...")
    conn.commit()
    conn.close()  # 💥 如果 conn 来自 get_db()，这会关闭线程共享连接！
```

### 正确做法

**规则 1：从 `get_db()` 获取的连接，永远不要 close**

```python
from agentos.core.db.registry_db import get_db, transaction

def save_data(self, data):
    # 方式 A：手动 commit（不要 close）
    conn = get_db()
    conn.execute("INSERT INTO ...")
    conn.commit()  # ✅ commit 即可，不要 close

    # 方式 B：用事务上下文（推荐）
    with transaction() as conn:
        conn.execute("INSERT INTO ...")
        # 自动 commit，不需要 close
```

**规则 2：只有自己创建的连接才能 close**

```python
def save_data_to_custom_db(self, db_path: str, data):
    # 明确创建的连接，必须 close
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("INSERT INTO ...")
        conn.commit()
    finally:
        conn.close()  # ✅ 自己创建的，必须关闭
```

---

## 快速诊断

### 步骤 1：启用追踪

```bash
# 运行你的服务/测试，追踪会自动打印 close 调用栈
./scripts/debug_db_close.sh python -m agentos.webui.app

# 或者直接设置环境变量
export AGENTOS_DEBUG_DB_CLOSE=true
python -m agentos.webui.app
```

### 步骤 2：查看日志

搜索日志中的 `🚨` 或 `[DB-TRACE]`，你会看到：

```
🚨 [DB-TRACE] SHARED CONNECTION CLOSE DETECTED! 🚨
Thread: Thread-5
Connection ID: 140234567890
This is a thread-local shared connection from get_db()!
Closing it will break other code in the same thread.

🔍 CLOSE CALLED FROM:
  File "agentos/router/persistence.py", line 86, in save_route_plan
    conn.close()
  File "agentos/webui/api/tasks.py", line 123, in create_task
    router.save_route_plan(plan)

💡 FIX: Remove conn.close() if conn comes from get_db().
```

---

## 修复清单

以下文件需要修复（按优先级排序）：

### 🔴 高优先级（核心业务代码）

1. **agentos/router/persistence.py**
   - 问题：`_get_conn()` 混用 `sqlite3.connect()` 和 `get_db()`
   - 修复：统一使用 `get_db()`，删除所有 `conn.close()`
   - 影响：路由持久化逻辑

2. **agentos/store/answers_store.py**
   - 问题：所有方法都 `_get_conn()` + `conn.close()`
   - 修复：改用 `get_db()` + `transaction()`
   - 影响：Answer Packs 功能

3. **agentos/store/content_store.py**
   - 问题：同 answers_store.py
   - 修复：同上
   - 影响：内容存储

4. **agentos/core/supervisor/inbox.py**
   - 问题：多处 `conn.close()`
   - 修复：检查是否自己创建的连接，如果是 `get_db()` 则删除 close
   - 影响：Supervisor 模式

5. **agentos/core/supervisor/poller.py**
   - 问题：同上
   - 修复：同上

6. **agentos/webui/api/governance.py**
   - 问题：line 711/1016/1068 有明确注释 "Close explicitly created connection"
   - 修复：检查是否真的是 "explicitly created"，如果不是则删除 close

### 🟡 中优先级（CLI 工具）

7. **agentos/cli/project.py**
8. **agentos/cli/project_migrate.py**
9. **agentos/cli/scan.py**
10. **agentos/cli/generate.py**
11. **agentos/cli/memory.py**
12. **agentos/jobs/memory_gc.py**
13. **agentos/jobs/lead_scan.py**

这些是 CLI 工具，通常单线程运行，问题不严重，但为了代码一致性应该修复。

### 🟢 低优先级（一次性脚本/测试）

- `agentos/store/migrations/*.py`：迁移脚本，一次性运行
- `agentos/store/scripts/*.py`：工具脚本
- `tests/**/*.py`：测试代码（允许例外）

---

## 修复模板

### 模板 1：Repository 类（推荐）

**之前：**
```python
class MyRepo:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        if self.db_path:
            conn = sqlite3.connect(str(self.db_path))
        else:
            conn = get_db()
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, data):
        conn = self._get_conn()
        conn.execute("INSERT ...")
        conn.commit()
        conn.close()  # ❌ 危险
```

**之后：**
```python
from agentos.core.db.registry_db import get_db, transaction

class MyRepo:
    def __init__(self, db_path: Optional[str] = None):
        """
        Args:
            db_path: Optional custom DB path. If None, uses default registry DB.
                     Note: Custom paths are deprecated, use registry DB instead.
        """
        if db_path:
            import warnings
            warnings.warn(
                "Custom db_path is deprecated. Use default registry DB.",
                DeprecationWarning
            )
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection.

        Note: DO NOT close the returned connection if using default DB.
        """
        if self.db_path:
            # Custom path: caller must close
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            return conn
        else:
            # Default registry: DO NOT close
            return get_db()

    def save(self, data):
        if self.db_path:
            # Custom DB: manage connection lifecycle
            conn = self._get_conn()
            try:
                conn.execute("INSERT ...")
                conn.commit()
            finally:
                conn.close()
        else:
            # Registry DB: use transaction context
            with transaction() as conn:
                conn.execute("INSERT ...")
                # Auto-commit on success
```

### 模板 2：简单函数

**之前：**
```python
def load_data(task_id: str) -> dict:
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()  # ❌ 不要关闭共享连接
    return dict(row)
```

**之后：**
```python
from agentos.core.db.registry_db import query_one

def load_data(task_id: str) -> dict:
    row = query_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    return dict(row) if row else {}
```

或者：

```python
from agentos.core.db.registry_db import get_db

def load_data(task_id: str) -> dict:
    conn = get_db()  # ✅ 拿到连接
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    # ✅ 不要 close，让 thread-local 池管理
    return dict(row)
```

---

## 自动化修复脚本

```bash
# 扫描所有问题点
python scripts/scan_db_close_issues.py

# 自动修复（谨慎使用，先备份）
python scripts/fix_db_close_issues.py --dry-run
python scripts/fix_db_close_issues.py --apply
```

---

## 验证修复

### 1. 运行追踪模式
```bash
export AGENTOS_DEBUG_DB_CLOSE=true
python -m agentos.webui.app
# 日志中不应该再出现 🚨
```

### 2. 运行回归测试
```bash
pytest tests/integration/ -v
pytest tests/e2e/ -v
```

### 3. 并发压测
```bash
pytest tests/stress/test_concurrent_stress.py -v
```

---

## 长期架构改进建议

### 选项 A：废弃自定义 db_path（推荐）

- 所有代码统一使用 `get_db()`（从环境变量 `AGENTOS_DB_PATH` 读取路径）
- 测试用 `monkeypatch` 或 `reset_db_path()` 切换数据库
- 删除所有 `db_path` 参数

### 选项 B：明确连接所有权

- 创建 `OwnedConnection` 和 `SharedConnection` 两种类型
- 只有 `OwnedConnection.close()` 可以调用
- `SharedConnection.close()` 抛出异常或警告

### 选项 C：迁移到 PostgreSQL

- 如果数据库负载大，考虑迁移到 PostgreSQL
- 使用 `agentos/core/database.py` 的 `create_engine()`
- 支持真正的连接池（SQLAlchemy QueuePool）

---

## 检查清单

修复完成后，确保：

- [ ] 所有 `get_db()` 返回的连接都没有 `close()` 调用
- [ ] 所有 `sqlite3.connect()` 创建的连接都在 `finally` 中 `close()`
- [ ] Repository 类要么完全用 `get_db()`，要么完全自己管理连接（不混用）
- [ ] 启用追踪模式运行主流程，日志无 🚨
- [ ] 通过所有集成测试和压测
- [ ] 更新相关文档和代码注释

---

## 参考资料

- `agentos/core/db/registry_db.py` - 连接池实现
- `agentos/core/db/writer.py` - 写操作串行化
- `agentos/core/database.py` - 多数据库支持
- SQLite 并发最佳实践：https://www.sqlite.org/wal.html
