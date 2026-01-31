# "数据库被关闭" 问题 - 完整排查和修复指南

## 🎯 问题确认

你说的完全正确！**Engine 覆盖不全**导致了这个问题。

### 问题根因

AgentOS 有统一的数据库架构：
- ✅ `get_db()` - 返回 thread-local 连接池（读操作）
- ✅ `SQLiteWriter` - 单线程串行化写操作
- ✅ 核心业务代码使用了 204 次 `get_db()`

**但是**，有 **数十个文件** 违反了连接管理规则：

```python
# ❌ 错误模式（在多个文件中发现）
def _get_conn(self):
    if self.db_path:
        conn = sqlite3.connect(...)  # 自己创建
    else:
        conn = get_db()  # 线程共享单例
    return conn

def save_data(self):
    conn = self._get_conn()
    conn.execute("INSERT ...")
    conn.commit()
    conn.close()  # 💥 如果 conn 来自 get_db()，会关闭线程共享连接！
```

### 发生场景

同一线程内：
1. API 请求处理器调用 `get_db()` → 拿到线程连接 A
2. 调用 `RouterPersistence.save()` → 内部 `_get_conn()` 返回**同一个连接 A**
3. `save()` 执行完调用 `conn.close()` → 💥 **连接 A 被关闭**
4. API 处理器继续执行 → **"database is closed"**

---

## 📋 立即行动清单

### Step 1：扫描问题点（5 分钟）

```bash
cd /Users/pangge/PycharmProjects/AgentOS

# 扫描所有潜在问题
python scripts/scan_db_close_issues.py

# 或保存为 JSON 供后续分析
python scripts/scan_db_close_issues.py --json db_issues.json
```

你会看到类似这样的报告：

```
📊 发现 47 个潜在问题:
   🔴 高风险:  18
   🟡 中风险:  23
   🟢 低风险:  6

🔴 HIGH 风险问题:
1. agentos/router/persistence.py:86
   描述: 可能关闭了 get_db() 返回的共享连接
   💡 修复建议: 检查 conn 是否来自 get_db()，如果是则删除 close()
```

### Step 2：启用运行时追踪（复现问题）

```bash
# 运行你的服务并观察日志
./scripts/debug_db_close.sh python -m agentos.webui.app

# 或运行集成测试
./scripts/debug_db_close.sh pytest tests/integration/test_projects_e2e.py -v
```

日志中搜索 `🚨`，你会看到：

```
🚨 [DB-TRACE] SHARED CONNECTION CLOSE DETECTED! 🚨
Thread: uvicorn-worker-1
Connection ID: 140234567890

🔍 CLOSE CALLED FROM:
  File "agentos/router/persistence.py", line 86, in save_route_plan
    conn.close()
  File "agentos/webui/api/tasks.py", line 123, in create_task
    router_persistence.save_route_plan(plan)

💡 FIX: Remove conn.close() if conn comes from get_db().
```

**现在你知道了：**
- 哪个文件的哪一行调用了 close
- 完整的调用栈
- 谁触发了这个问题

### Step 3：修复高优先级文件（1-2 小时）

按照扫描报告，优先修复这些文件：

#### 🔴 必须立即修复（核心业务）

1. **agentos/router/persistence.py**
2. **agentos/store/answers_store.py**
3. **agentos/store/content_store.py**
4. **agentos/core/supervisor/inbox.py**
5. **agentos/core/supervisor/poller.py**
6. **agentos/webui/api/governance.py**

修复模板见 `docs/v3/DB_CLOSE_FIX.md`

#### 快速修复示例

**之前（agentos/router/persistence.py）：**
```python
def save_route_plan(self, route_plan: RoutePlan) -> None:
    conn = self._get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET ...")
    conn.commit()
    conn.close()  # ❌
```

**之后：**
```python
from agentos.core.db.registry_db import get_db, transaction

def save_route_plan(self, route_plan: RoutePlan) -> None:
    # 如果支持自定义 db_path，需要区分
    if self.db_path:
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET ...")
            conn.commit()
        finally:
            conn.close()  # ✅ 自己创建的可以 close
    else:
        # 使用共享连接 + 事务上下文
        with transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET ...")
            # 自动 commit，不需要 close
```

或者更简单的（如果不需要支持自定义 db_path）：

```python
from agentos.core.db.registry_db import transaction

def save_route_plan(self, route_plan: RoutePlan) -> None:
    with transaction() as conn:
        conn.execute("UPDATE tasks SET ...", (...))
        # 自动 commit，不需要 close ✅
```

### Step 4：回归测试

```bash
# 再次运行追踪模式，确保日志无 🚨
export AGENTOS_DEBUG_DB_CLOSE=true
python -m agentos.webui.app

# 运行集成测试
pytest tests/integration/ -v

# 并发压测
pytest tests/stress/test_concurrent_stress.py -v
```

---

## 🛠 已创建的工具

### 1. 运行时追踪器
- **文件**: `agentos/core/db/_connection_wrapper.py`
- **启用**: 设置环境变量 `AGENTOS_DEBUG_DB_CLOSE=true`
- **功能**: 每次 `conn.close()` 被调用时，打印完整调用栈

### 2. 启动脚本
- **文件**: `scripts/debug_db_close.sh`
- **用法**: `./scripts/debug_db_close.sh <command>`
- **示例**: `./scripts/debug_db_close.sh python -m agentos.webui.app`

### 3. 静态扫描器
- **文件**: `scripts/scan_db_close_issues.py`
- **用法**: `python scripts/scan_db_close_issues.py`
- **功能**: 扫描所有 Python 文件，检测潜在问题

### 4. 修复文档
- **文件**: `docs/v3/DB_CLOSE_FIX.md`
- **内容**:
  - 问题根源详解
  - 修复模板（Repository 类、简单函数）
  - 完整的修复清单（按优先级）
  - 长期架构改进建议

---

## 📊 影响范围

根据 `grep` 统计：

| 模式 | 文件数 | 描述 | 优先级 |
|------|--------|------|--------|
| `get_db()` 调用 | 52 | 核心业务代码使用统一接口 | ✅ 已做好 |
| `conn.close()` 调用 | 80+ | 需要逐个审查是否误关闭共享连接 | 🔴 高 |
| `sqlite3.connect()` | 50+ | 大部分在测试/脚本中（OK），少数在业务代码（需检查） | 🟡 中 |

---

## 🎓 核心规则

记住这两条：

### 规则 1：从 `get_db()` 拿的连接，永远不要 close

```python
conn = get_db()
conn.execute("SELECT ...")
# ✅ 不要 close，让线程池管理
```

### 规则 2：只有自己创建的连接才能 close

```python
conn = sqlite3.connect("/path/to/custom.db")
try:
    conn.execute("INSERT ...")
    conn.commit()
finally:
    conn.close()  # ✅ 必须 close
```

---

## 🔥 快速开始

```bash
# 1. 扫描问题
python scripts/scan_db_close_issues.py

# 2. 启用追踪复现
./scripts/debug_db_close.sh python -m agentos.webui.app

# 3. 查看日志，搜索 🚨

# 4. 根据 docs/v3/DB_CLOSE_FIX.md 修复

# 5. 再次追踪验证
./scripts/debug_db_close.sh pytest tests/integration/ -v
```

---

## ❓ 常见问题

### Q1: 我可以禁用追踪吗？
A: 可以。追踪默认关闭，只在设置 `AGENTOS_DEBUG_DB_CLOSE=true` 时启用。修复完成后可以移除环境变量。

### Q2: 追踪会影响性能吗？
A: 会有轻微影响（每次连接创建/关闭时记录栈）。只建议在开发/调试时启用，生产环境应关闭。

### Q3: 可以自动修复吗？
A: 静态扫描只能检测潜在问题，无法 100% 确定。建议手动审查并修复，因为需要判断连接来源。未来可以开发自动化脚本。

### Q4: 测试代码也要修复吗？
A: 测试代码优先级低。`agentos/core/db/registry_db.py` 注释明确允许测试文件使用 `sqlite3.connect()`。但为了代码一致性，也建议统一。

### Q5: 长期方案是什么？
A: 见 `docs/v3/DB_CLOSE_FIX.md` 的"长期架构改进建议"。推荐：
   - 短期：修复所有高优先级文件
   - 中期：废弃自定义 `db_path`，统一用 `get_db()`
   - 长期：如果负载大，迁移到 PostgreSQL + 真正的连接池

---

## 📞 需要帮助？

1. 查看详细文档：`docs/v3/DB_CLOSE_FIX.md`
2. 运行扫描器：`python scripts/scan_db_close_issues.py`
3. 启用追踪：`./scripts/debug_db_close.sh <your-command>`
4. 查看示例修复：搜索 Git 历史中的相关 commit

---

**总结：你的判断完全正确！Engine 确实实现了，但覆盖不全导致部分代码绕过统一接口，手动管理连接时关闭了共享连接。现在有了完整的工具链来定位和修复。**
