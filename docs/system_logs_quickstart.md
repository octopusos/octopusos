# System Logs 快速入门

## 快速开始

### 1. 基本使用

系统会自动捕获所有 ERROR 和 CRITICAL 级别的日志:

```python
import logging

logger = logging.getLogger(__name__)

# 自动捕获到 System Logs
logger.error("Something went wrong")

# 带异常堆栈
try:
    risky_operation()
except Exception:
    logger.error("Operation failed", exc_info=True)
```

### 2. 查看日志

访问 WebUI:
```
http://localhost:8080/control
```

点击 "Logs" 标签查看系统日志。

### 3. API 查询

```bash
# 获取所有错误日志
curl "http://localhost:8080/api/logs?level=error"

# 按任务过滤
curl "http://localhost:8080/api/logs?task_id=task_123"

# 限制返回数量
curl "http://localhost:8080/api/logs?limit=50"
```

## 配置

### 环境变量

```bash
# 启用持久化 (默认: false)
export AGENTOS_LOGS_PERSIST=true

# 设置内存大小 (默认: 5000)
export AGENTOS_LOGS_MAX_SIZE=10000

# 设置捕获级别 (默认: ERROR)
export AGENTOS_LOGS_LEVEL=WARNING

# 设置数据库路径 (默认: store/registry.sqlite)
export AGENTOS_DB_PATH=/path/to/logs.db
```

## 高级用法

### 手动设置上下文

在自定义代码中添加上下文信息:

```python
from agentos.core.logging import set_log_context, clear_log_context

# 设置上下文
set_log_context(task_id="my_task", session_id="my_session")

try:
    # 此处的所有日志会自动包含上下文
    do_work()
finally:
    # 清除上下文
    clear_log_context()
```

### 编程式查询

```python
from agentos.core.logging.store import LogStore

# 获取全局 log_store (需要从 app 中获取)
logs = log_store.query(
    task_id="task_123",
    level="error",
    limit=100
)

for log in logs:
    print(f"[{log.level}] {log.message}")
    if log.task_id:
        print(f"  Task: {log.task_id}")
```

## 故障排查

### 日志未显示

1. 检查日志级别是否为 ERROR 或更高
2. 验证 LogStore 是否初始化:
   ```python
   # 查看启动日志
   tail -f logs/agentos.log | grep "System logs"
   ```

### 性能问题

1. 减少内存大小:
   ```bash
   export AGENTOS_LOGS_MAX_SIZE=1000
   ```

2. 禁用持久化:
   ```bash
   export AGENTOS_LOGS_PERSIST=false
   ```

### 日志过多

1. 提高捕获级别:
   ```bash
   export AGENTOS_LOGS_LEVEL=CRITICAL
   ```

## 常见问题

### Q: 日志会占用多少内存?

A: 默认 5000 条,约 25MB。可通过 `AGENTOS_LOGS_MAX_SIZE` 调整。

### Q: 持久化日志存在哪里?

A: 默认在 `store/registry.sqlite` 的 `task_audits` 表中。

### Q: 可以捕获 INFO 级别的日志吗?

A: 可以,设置 `export AGENTOS_LOGS_LEVEL=INFO`。但建议只捕获错误以节省资源。

### Q: 日志会影响性能吗?

A: 影响极小 (< 1ms per log)。持久化是异步的,不会阻塞主线程。

### Q: 如何清空日志?

A: 重启应用(如果未启用持久化),或手动清空数据库。

## 示例场景

### 场景 1: 调试任务失败

1. 导航到 Logs 页面
2. 在 "Task ID" 过滤框输入任务 ID
3. 查看错误日志和堆栈追踪

### 场景 2: 监控系统错误

1. 设置 Tail 模式 (自动刷新)
2. 过滤 level=error
3. 实时观察新错误

### 场景 3: 下载日志用于分析

1. 设置过滤条件
2. 点击 "Download" 按钮
3. 获得 JSON 格式的日志文件

## 更多信息

- 完整实施报告: `SYSTEM_LOGS_IMPLEMENTATION.md`
- 源代码: `agentos/core/logging/`
- API 文档: `agentos/webui/api/logs.py`
