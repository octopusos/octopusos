# Agent2 架构设计文档

## 系统概览

Agent2 是 AgentOS 的健康监控组件，采用循环检查 + 事件驱动的混合架构。

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agent2 Monitor                           │
│                    (agent2_monitor.py)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Main Control Loop (5s cycle)                │  │
│  │                                                           │  │
│  │  while running:                                          │  │
│  │    1. Diagnose                                           │  │
│  │    2. Evaluate Health                                    │  │
│  │    3. Fix if needed                                      │  │
│  │    4. Update Status                                      │  │
│  │    5. Sleep 5s                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Diagnosis  │  │   Decision   │  │  Fix Action  │          │
│  │              │  │              │  │              │          │
│  │ • Process    │→ │ • Failures   │→ │ • Create     │          │
│  │ • Port       │  │   Counter    │  │   Signal     │          │
│  │ • Health API │  │ • Threshold  │  │ • Wait       │          │
│  │ • Response   │  │   Check      │  │ • Reset      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                          │          │          │
                          ▼          ▼          ▼
            ┌──────────────┐ ┌──────────┐ ┌──────────────┐
            │  WebUI API   │ │ Status   │ │ Restart      │
            │  :8080/api/  │ │ File     │ │ Signal       │
            │  health      │ │ (JSON)   │ │ (JSON)       │
            └──────────────┘ └──────────┘ └──────────────┘
```

## 组件详解

### 1. 主控制循环 (Main Control Loop)

```python
def run(self):
    """主监控循环"""
    while self.running:
        try:
            self._run_monitoring_cycle()
            time.sleep(self.check_interval)
        except Exception as e:
            logger.error(f"监控循环异常: {e}")
```

**职责：**
- 维持持续监控
- 异常捕获和恢复
- 控制检查频率

**特性：**
- 非阻塞式设计
- 优雅退出支持
- 错误隔离

### 2. 诊断模块 (Diagnosis Module)

```python
def _diagnose(self) -> Dict[str, Any]:
    """诊断 WebUI 状态"""
    return {
        "timestamp": ...,
        "process_alive": self._check_process_alive(),
        "port_listening": self._check_port_listening(),
        "health_api_ok": ...,
        "response_time": ...,
    }
```

**检查项：**

#### 2.1 进程检查
```python
def _check_process_alive(self) -> bool:
    # 1. 读取 PID 文件
    # 2. 验证进程存在
    # 3. 验证进程类型
    return True/False
```

#### 2.2 端口检查
```python
def _check_port_listening(self) -> bool:
    # 1. 遍历网络连接
    # 2. 查找 8080 端口
    # 3. 验证 LISTEN 状态
    return True/False
```

#### 2.3 API 检查
```python
def _check_health_api(self):
    # 1. HTTP GET 请求
    # 2. 验证状态码
    # 3. 解析 JSON 响应
    # 4. 检查 status 字段
    return (success, data, response_time)
```

### 3. 决策模块 (Decision Module)

```
┌─────────────────────────────────────────────────┐
│             Health Evaluation Logic              │
├─────────────────────────────────────────────────┤
│                                                  │
│  All Checks Pass?                                │
│    ├─ Yes ─> health_status = "ok"               │
│    │         consecutive_failures = 0           │
│    │                                             │
│    └─ No ──> consecutive_failures++             │
│              │                                   │
│              ├─ failures < 2 ──> "warn"         │
│              │                                   │
│              └─ failures >= 2 ─> "down"         │
│                                  Trigger Fix    │
│                                                  │
└─────────────────────────────────────────────────┘
```

**决策流程：**

1. **健康判断**
   ```python
   if all_checks_pass:
       health_status = "ok"
       consecutive_failures = 0
   else:
       consecutive_failures += 1
       if consecutive_failures >= 2:
           trigger_fix()
   ```

2. **阈值控制**
   - 单次失败：标记 "warn"，继续观察
   - 连续失败：标记 "down"，触发修复
   - 恢复后：重置计数器

### 4. 修复模块 (Fix Module)

```
┌─────────────────────────────────────────────────┐
│              Fix Decision Tree                   │
├─────────────────────────────────────────────────┤
│                                                  │
│  Diagnosis                                       │
│    │                                             │
│    ├─ Process NOT alive ─────┐                  │
│    │                          │                  │
│    ├─ Port NOT listening ─────┤                  │
│    │                          ├─> Create         │
│    ├─ Health API failed ──────┤    Restart      │
│    │                          │    Signal        │
│    │                          │                  │
│    └─ Response time > 3s ─────┴─> Log Warning   │
│                                                  │
└─────────────────────────────────────────────────┘
```

**修复策略：**

```python
def _fix_issue(self, diagnosis):
    if not diagnosis["process_alive"]:
        # 进程不存在
        self._create_restart_signal("process_not_alive")

    elif not diagnosis["port_listening"]:
        # 端口未监听
        self._create_restart_signal("port_not_listening")

    elif not diagnosis["health_api_ok"]:
        # API 失败
        self._create_restart_signal("health_check_failed")

    elif diagnosis["response_time"] > 3.0:
        # 响应慢
        logger.warning("Response time alert")
```

### 5. 状态管理 (State Management)

```
┌──────────────────────────────────────────┐
│        State File Structure              │
├──────────────────────────────────────────┤
│                                          │
│  agent2_status.json                      │
│  {                                       │
│    "status": "monitoring",               │
│    "last_check": "2026-01-27T...",      │
│    "health_status": "ok",               │
│    "consecutive_failures": 0,           │
│    "fixes": [                           │
│      {                                  │
│        "timestamp": "...",              │
│        "issue": "...",                  │
│        "action": "...",                 │
│        "result": "..."                  │
│      }                                  │
│    ]                                    │
│  }                                       │
│                                          │
└──────────────────────────────────────────┘
```

**状态转换：**

```
initializing ──> monitoring ──> fixing ──> monitoring
                     │                        │
                     └─────── error ──────────┘
                              │
                           stopped
```

### 6. 通信机制 (Communication)

#### 6.1 与 WebUI 通信

```
Agent2                          WebUI
  │                              │
  ├─── GET /api/health ────────>│
  │                              │
  │<──── 200 OK ─────────────────┤
  │      { status: "ok" }        │
  │                              │
```

**请求格式：**
```http
GET http://127.0.0.1:8080/api/health
Timeout: 5s
```

**响应格式：**
```json
{
  "status": "ok",
  "timestamp": "2026-01-27T10:30:45+00:00",
  "uptime_seconds": 3600.5,
  "components": {
    "database": "ok",
    "process": "ok"
  },
  "metrics": {
    "cpu_percent": 2.5,
    "memory_mb": 128.5,
    "pid": 12345
  }
}
```

#### 6.2 与 Agent1 通信

```
Agent2                          Agent1
  │                              │
  ├─ Write restart_signal ──────>│
  │  {                           │
  │    "timestamp": "...",       │
  │    "reason": "...",          │
  │    "requested_by": "agent2"  │
  │  }                           │
  │                              │
  │                         Read Signal
  │                              │
  │                        Restart WebUI
  │                              │
  │<── Delete restart_signal ────┤
  │                              │
```

**信号文件位置：**
```
~/.agentos/multi_agent/restart_signal
```

## 数据流图

```
┌─────────────────────────────────────────────────────┐
│                   Data Flow                          │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────┐                                       │
│  │  Start   │                                       │
│  └────┬─────┘                                       │
│       │                                             │
│       ▼                                             │
│  ┌──────────────┐                                  │
│  │  Initialize  │                                  │
│  │  • Config    │                                  │
│  │  • Dirs      │                                  │
│  │  • Signals   │                                  │
│  └──────┬───────┘                                  │
│         │                                           │
│         ▼                                           │
│  ┌──────────────────┐                              │
│  │  Monitor Loop    │◄────────────┐                │
│  └──────┬───────────┘             │                │
│         │                          │                │
│         ▼                          │                │
│  ┌──────────────────┐             │                │
│  │  Diagnose        │             │                │
│  │  1. Process      │             │                │
│  │  2. Port         │             │                │
│  │  3. Health API   │             │                │
│  └──────┬───────────┘             │                │
│         │                          │                │
│         ▼                          │                │
│  ┌──────────────────┐             │                │
│  │  Evaluate        │             │                │
│  │  Health Status   │             │                │
│  └──────┬───────────┘             │                │
│         │                          │                │
│    ┌────┴─────┐                   │                │
│    │          │                   │                │
│    ▼          ▼                   │                │
│  [OK]      [FAIL]                 │                │
│    │          │                   │                │
│    │          ▼                   │                │
│    │    ┌─────────────┐           │                │
│    │    │ Failures++  │           │                │
│    │    └──────┬──────┘           │                │
│    │           │                  │                │
│    │      ┌────┴─────┐            │                │
│    │      │          │            │                │
│    │      ▼          ▼            │                │
│    │    [<2]      [>=2]           │                │
│    │      │          │            │                │
│    │      │          ▼            │                │
│    │      │    ┌──────────┐       │                │
│    │      │    │   Fix    │       │                │
│    │      │    │  Issue   │       │                │
│    │      │    └─────┬────┘       │                │
│    │      │          │            │                │
│    │      │          ▼            │                │
│    │      │    ┌──────────────┐   │                │
│    │      │    │ Create       │   │                │
│    │      │    │ Restart      │   │                │
│    │      │    │ Signal       │   │                │
│    │      │    └──────┬───────┘   │                │
│    │      │           │           │                │
│    ▼      ▼           ▼           │                │
│  ┌────────────────────────┐       │                │
│  │   Update Status File   │       │                │
│  └────────┬───────────────┘       │                │
│           │                       │                │
│           ▼                       │                │
│  ┌────────────────┐               │                │
│  │  Sleep 5s      │               │                │
│  └────────┬───────┘               │                │
│           │                       │                │
│           └───────────────────────┘                │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## 时序图

### 正常监控流程

```
Time  Agent2              WebUI               Status File
 │                                                   │
 0s   │                      │                       │
 │    ├─ Check Process ────>│                       │
 │    │<─ OK ───────────────┤                       │
 │    │                      │                       │
 │    ├─ Check Port ────────>│                       │
 │    │<─ Listening ─────────┤                       │
 │    │                      │                       │
 │    ├─ GET /health ───────>│                       │
 │    │<─ 200 OK ────────────┤                       │
 │    │   {status: "ok"}     │                       │
 │    │                      │                       │
 │    ├────────────────────────────── Update ──────>│
 │    │                      │        {status: "ok"} │
 │    │                      │                       │
 5s   │  [Sleep 5s]          │                       │
 │    │                      │                       │
10s   │  [Next cycle...]     │                       │
```

### 故障恢复流程

```
Time  Agent2              WebUI               Agent1         Status File
 │                                                                  │
 0s   │                      │                    │                 │
 │    ├─ Check Process ────>│                    │                 │
 │    │<─ FAIL ─────────────┤                    │                 │
 │    │                      │                    │                 │
 │    ├────────────────────────────── Update ─────────────────────>│
 │    │                      │         {failures: 1, status: "warn"}│
 │    │                      │                    │                 │
 5s   │  [Sleep 5s]          │                    │                 │
 │    │                      │                    │                 │
10s   │                      │                    │                 │
 │    ├─ Check Process ────>│                    │                 │
 │    │<─ FAIL ─────────────┤                    │                 │
 │    │                      │                    │                 │
 │    │ [Trigger Fix]        │                    │                 │
 │    │                      │                    │                 │
 │    ├─────────────────────────── Create Signal ───────────────>  │
 │    │                      │                 restart_signal       │
 │    │                      │                    │                 │
 │    ├────────────────────────────── Update ─────────────────────>│
 │    │                      │     {fixes: [...], status: "fixing"} │
 │    │                      │                    │                 │
15s   │  [Wait for Agent1]   │                    │                 │
 │    │                      │         ┌──────────┤                 │
 │    │                      │         │ Detect   │                 │
 │    │                      │         │ Signal   │                 │
 │    │                      │         └──────────>                 │
 │    │                      │                    │                 │
20s   │                      │<───── Restart ─────┤                 │
 │    │                      │                    │                 │
 │    │                      │         ┌──────────┤                 │
 │    │                      │         │ Delete   │                 │
 │    │                      │         │ Signal   │                 │
 │    │                      │         └──────────>                 │
 │    │                      │                    │                 │
25s   │                      │                    │                 │
 │    ├─ Check Process ────>│                    │                 │
 │    │<─ OK ───────────────┤                    │                 │
 │    │                      │                    │                 │
 │    ├────────────────────────────── Update ─────────────────────>│
 │    │                      │    {failures: 0, status: "monitoring"}│
```

## 错误处理架构

```
┌─────────────────────────────────────────────┐
│           Error Handling Strategy            │
├─────────────────────────────────────────────┤
│                                              │
│  Exception Type          Handling Strategy   │
│  ├─ ConnectionError  ──> Log + Continue     │
│  ├─ Timeout          ──> Log + Continue     │
│  ├─ JSONDecodeError  ──> Log + Continue     │
│  ├─ FileNotFoundError ─> Create + Continue  │
│  ├─ PermissionError  ──> Log + Exit         │
│  └─ Exception        ──> Log + Continue     │
│                                              │
│  Isolation Levels:                          │
│  1. Per-check try-catch                     │
│  2. Diagnosis-level try-catch               │
│  3. Cycle-level try-catch                   │
│  4. Main-level try-catch                    │
│                                              │
└─────────────────────────────────────────────┘
```

## 配置参数

```python
# 核心配置
WEBUI_URL = "http://127.0.0.1:8080"
HEALTH_ENDPOINT = "/api/health"
CHECK_INTERVAL = 5  # 秒
MAX_RETRY = 3
TIMEOUT = 5  # 秒
FAILURE_THRESHOLD = 2
RESPONSE_TIME_WARNING = 3.0  # 秒

# 文件路径
BASE_DIR = "~/.agentos"
MULTI_AGENT_DIR = "~/.agentos/multi_agent"
PID_FILE = "~/.agentos/multi_agent/agent2.pid"
LOG_FILE = "~/.agentos/multi_agent/agent2.log"
STATUS_FILE = "~/.agentos/multi_agent/agent2_status.json"
RESTART_SIGNAL = "~/.agentos/multi_agent/restart_signal"
```

## 性能优化

### 1. 资源使用优化

```python
# 使用连接池（计划中）
import urllib3
http = urllib3.PoolManager(maxsize=1)

# 避免频繁文件 I/O
# 状态更新批量写入（当前每次都写，可优化为缓存）

# 日志异步写入（可选）
from logging.handlers import QueueHandler
```

### 2. 检查优化

```python
# 快速失败策略
# 1. 先检查进程（最快）
# 2. 再检查端口（较快）
# 3. 最后检查 API（较慢）

# 如果进程不存在，直接跳过后续检查
if not process_alive:
    return fast_fail_diagnosis()
```

### 3. 并发检查（计划中）

```python
# 使用线程池并发检查
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    process_future = executor.submit(check_process)
    port_future = executor.submit(check_port)
    api_future = executor.submit(check_api)
```

## 扩展点

### 1. 自定义检查

```python
class CustomCheck:
    def check(self) -> bool:
        # 实现自定义检查逻辑
        return True

# 注册到诊断流程
diagnosis["custom_check"] = CustomCheck().check()
```

### 2. 自定义修复

```python
class CustomFix:
    def fix(self, diagnosis):
        # 实现自定义修复逻辑
        pass

# 注册到修复流程
if condition:
    CustomFix().fix(diagnosis)
```

### 3. 插件系统（计划中）

```python
# 插件接口
class MonitorPlugin:
    def check(self) -> bool: ...
    def fix(self, issue): ...

# 插件管理器
class PluginManager:
    def load_plugins(self): ...
    def run_checks(self): ...
```

## 安全考虑

1. **文件权限**
   - 状态文件: 644
   - 日志文件: 644
   - PID 文件: 644

2. **网络安全**
   - 仅本地通信（127.0.0.1）
   - 无需认证（本地信任）

3. **进程隔离**
   - 独立进程运行
   - 信号处理
   - 优雅退出

## 总结

Agent2 采用简单而可靠的架构：
- **循环检查**: 定时轮询，简单可靠
- **状态机**: 清晰的状态转换
- **文件通信**: 简单的 IPC 机制
- **错误隔离**: 多层次异常处理
- **扩展友好**: 易于添加新功能

这种架构在保证功能完整性的同时，保持了代码的简洁和可维护性。
