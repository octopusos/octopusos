# SQLite Threading Quick Reference

**最后更新**: 2026-01-29
**适用范围**: Phase 2.5+

---

## 快速开始

### 1. 初始化 ConnectionFactory

在应用启动时调用一次：

```python
from agentos.store import init_factory

# 初始化全局连接工厂
init_factory("/path/to/database.db")
```

### 2. 获取线程本地连接（读操作）

在任意线程中：

```python
from agentos.store import get_thread_connection

# 获取当前线程的连接（自动复用）
conn = get_thread_connection()

# 执行读操作
cursor = conn.execute("SELECT * FROM tasks WHERE status = ?", ("pending",))
tasks = cursor.fetchall()
```

### 3. 执行写操作

使用 SQLiteWriter：

```python
from agentos.store import get_writer

writer = get_writer()

def insert_task(conn):
    cursor = conn.execute(
        "INSERT INTO tasks (task_id, title, status) VALUES (?, ?, ?)",
        ("task-001", "Process data", "pending")
    )
    return cursor.lastrowid

# 提交写操作
task_id = writer.submit(insert_task, timeout=5.0)
```

---

## 核心概念

### Thread-Local Connections

- 每个线程自动获取自己的连接
- 线程内复用同一连接
- 避免跨线程共享连接

```python
# Thread 1
conn1 = get_thread_connection()  # 创建连接 A

# Thread 2
conn2 = get_thread_connection()  # 创建连接 B

# conn1 != conn2 (不同的连接对象)
```

### Single-Writer Pattern

- 所有写操作通过 SQLiteWriter 序列化
- 避免锁冲突
- 自动重试机制

```python
writer = get_writer()

# 多个线程可以同时调用，但写入会序列化执行
for i in range(100):
    threading.Thread(target=lambda: writer.submit(my_write)).start()
```

---

## 常见模式

### 模式 1: 后台线程读取

```python
import threading
from agentos.store import get_thread_connection

def background_reader():
    # ✅ 在线程内获取连接
    conn = get_thread_connection()

    while running:
        cursor = conn.execute("SELECT * FROM tasks WHERE status = 'pending'")
        tasks = cursor.fetchall()
        # 处理任务...

thread = threading.Thread(target=background_reader)
thread.start()
```

### 模式 2: 后台线程写入

```python
import threading
from agentos.store import get_writer

def background_writer():
    writer = get_writer()

    while running:
        def do_write(conn):
            cursor = conn.execute(
                "UPDATE tasks SET status = 'completed' WHERE task_id = ?",
                (task_id,)
            )
            return cursor.rowcount

        writer.submit(do_write, timeout=5.0)

thread = threading.Thread(target=background_writer)
thread.start()
```

### 模式 3: 事务处理

```python
from agentos.store import get_writer

def atomic_operation(conn):
    # 在 SQLiteWriter 中自动处理事务
    conn.execute("INSERT INTO tasks ...")
    conn.execute("UPDATE counters ...")
    # 自动 commit 或 rollback

writer = get_writer()
writer.submit(atomic_operation, timeout=10.0)
```

### 模式 4: RecoverySweep 集成

```python
from agentos.core.recovery import RecoverySweep
from agentos.store import get_db

# 方式 1: 使用 ConnectionFactory (推荐)
from agentos.store import init_factory
init_factory("/path/to/db.sqlite")
sweep = RecoverySweep(scan_interval_seconds=60)
sweep.start()

# 方式 2: 传入连接（向后兼容）
conn = get_db()
sweep = RecoverySweep(conn, scan_interval_seconds=60)
sweep.start()
# 注意: 后台线程会创建自己的连接
```

---

## 最佳实践

### ✅ DO

1. **使用 ConnectionFactory 获取读连接**

```python
conn = get_thread_connection()
cursor = conn.execute("SELECT ...")
```

2. **使用 SQLiteWriter 执行写操作**

```python
writer = get_writer()
writer.submit(my_write_function, timeout=5.0)
```

3. **在后台线程中获取线程本地连接**

```python
def worker_thread():
    conn = get_thread_connection()  # ✅ 线程内获取
    # 使用 conn...
```

4. **清理线程本地连接（可选）**

```python
from agentos.store import close_thread_connection

def worker_thread():
    try:
        conn = get_thread_connection()
        # 使用 conn...
    finally:
        close_thread_connection()  # 清理
```

### ❌ DON'T

1. **跨线程共享连接**

```python
# ❌ 错误
conn = get_thread_connection()  # 主线程
threading.Thread(target=lambda: conn.execute(...)).start()  # 错误！
```

2. **在主线程创建连接传给后台线程**

```python
# ❌ 错误
conn = sqlite3.connect("db.sqlite")  # 主线程

def worker():
    conn.execute(...)  # 错误！跨线程使用

threading.Thread(target=worker).start()
```

3. **直接执行写操作（绕过 SQLiteWriter）**

```python
# ❌ 不推荐（可能导致锁冲突）
conn = get_thread_connection()
conn.execute("INSERT INTO tasks ...")
conn.commit()

# ✅ 推荐
writer = get_writer()
writer.submit(lambda c: c.execute("INSERT INTO tasks ..."))
```

---

## 迁移指南

### 从旧代码迁移

**旧代码**:

```python
from agentos.store import get_db

# 每次调用创建新连接
conn1 = get_db()
conn2 = get_db()
# conn1 != conn2 (两个不同的连接)
```

**新代码**:

```python
from agentos.store import init_factory, get_thread_connection

# 应用启动时初始化
init_factory("/path/to/db.sqlite")

# 线程内复用连接
conn1 = get_thread_connection()
conn2 = get_thread_connection()
# conn1 == conn2 (同一连接)
```

**兼容性**: `get_db()` 仍然可用，未来可能重定向到 `get_thread_connection()`

---

## 故障排查

### 错误 1: SQLite objects created in a thread can only be used in that same thread

**原因**: 跨线程共享连接

**解决**:

```python
# ❌ 错误
conn = get_thread_connection()  # 主线程
threading.Thread(target=lambda: conn.execute(...)).start()

# ✅ 正确
def worker():
    conn = get_thread_connection()  # 线程内获取
    conn.execute(...)

threading.Thread(target=worker).start()
```

### 错误 2: ConnectionFactory not initialized

**原因**: 未调用 `init_factory()`

**解决**:

```python
from agentos.store import init_factory

# 应用启动时初始化
init_factory("/path/to/database.db")
```

### 错误 3: database is locked

**原因**: 多线程同时写入

**解决**: 使用 SQLiteWriter

```python
from agentos.store import get_writer

writer = get_writer()
writer.submit(my_write_function, timeout=5.0)
```

---

## 性能优化

### 连接复用

**旧方式** (每次创建新连接):

```python
for i in range(1000):
    conn = get_db()  # 创建 1000 个连接
    conn.execute("SELECT ...")
    conn.close()
```

**新方式** (复用连接):

```python
conn = get_thread_connection()  # 创建 1 个连接
for i in range(1000):
    conn.execute("SELECT ...")  # 复用同一连接
```

### 批量写入

使用 SQLiteWriter 的事务批处理：

```python
writer = get_writer()

def batch_insert(conn):
    for item in items:
        conn.execute("INSERT INTO tasks VALUES (?)", (item,))
    # 一次性 commit

writer.submit(batch_insert, timeout=30.0)
```

---

## API 参考

### init_factory()

初始化全局连接工厂。

```python
init_factory(
    db_path: str,
    busy_timeout: int = 5000,
    enable_wal: bool = True,
    enable_foreign_keys: bool = True
) -> ConnectionFactory
```

### get_thread_connection()

获取当前线程的连接。

```python
get_thread_connection() -> sqlite3.Connection
```

**返回**: 线程本地连接（自动复用）
**异常**: `RuntimeError` 如果未初始化工厂

### close_thread_connection()

关闭当前线程的连接。

```python
close_thread_connection() -> None
```

### get_writer()

获取全局 SQLiteWriter 实例。

```python
get_writer() -> SQLiteWriter
```

### SQLiteWriter.submit()

提交写操作。

```python
writer.submit(
    fn: Callable[[Connection], Any],
    timeout: float = 10.0
) -> Any
```

**参数**:
- `fn`: 接受连接的写操作函数
- `timeout`: 超时时间（秒）

**返回**: 函数返回值
**异常**: `TimeoutError` 如果超时

---

## 测试示例

### 测试线程本地连接

```python
import threading
from agentos.store import init_factory, get_thread_connection

def test_thread_local_connections():
    init_factory(":memory:")

    connections = {}

    def get_conn_id(thread_id):
        conn = get_thread_connection()
        connections[thread_id] = id(conn)

    threads = []
    for i in range(10):
        t = threading.Thread(target=get_conn_id, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # 验证每个线程的连接都不同
    conn_ids = list(connections.values())
    assert len(set(conn_ids)) == 10
```

### 测试并发写入

```python
from agentos.store import get_writer

def test_concurrent_writes():
    writer = get_writer()

    def write_data(thread_id):
        def do_write(conn):
            cursor = conn.execute(
                "INSERT INTO test (id, value) VALUES (?, ?)",
                (thread_id, f"value_{thread_id}")
            )
            return cursor.lastrowid

        writer.submit(do_write, timeout=5.0)

    threads = []
    for i in range(100):
        t = threading.Thread(target=write_data, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # 验证所有数据都写入
    # ...
```

---

## 相关文档

- **详细报告**: `PHASE2.5_SQLITE_CONCURRENCY_FIX_REPORT.md`
- **测试代码**: `tests/integration/test_sqlite_threading.py`
- **实现代码**: `agentos/store/connection_factory.py`
- **RecoverySweep**: `agentos/core/recovery/recovery_sweep.py`

---

**维护者**: AgentOS Core Team
**支持**: Phase 2.5+
