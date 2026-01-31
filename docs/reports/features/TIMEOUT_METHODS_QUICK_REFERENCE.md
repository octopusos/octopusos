# Timeout 方法快速参考

## 📋 实施总结

**状态**: ✅ 已完成
**日期**: 2026-01-29
**文件**: `agentos/core/task/models.py`
**新增方法**: 3个

---

## 🎯 新增方法一览

### 1. `get_timeout_config()` - 获取超时配置

```python
def get_timeout_config(self) -> "TimeoutConfig":
    """Get timeout configuration from metadata"""
```

**功能**: 从任务元数据中获取超时配置，如果不存在则返回默认配置

**返回值**:
- `enabled=True` - 超时检测已启用
- `timeout_seconds=3600` - 超时时长 1小时
- `warning_threshold=0.8` - 告警阈值 80%

**使用示例**:
```python
task = Task(task_id="test", title="Test")
config = task.get_timeout_config()
print(f"超时时长: {config.timeout_seconds}秒")
```

---

### 2. `get_timeout_state()` - 获取超时状态

```python
def get_timeout_state(self) -> "TimeoutState":
    """Get timeout state from metadata"""
```

**功能**: 从任务元数据中获取超时状态，如果不存在则返回默认状态

**返回值**:
- `execution_start_time=None` - 执行开始时间
- `last_heartbeat=None` - 最后心跳时间
- `warning_issued=False` - 是否已发出告警

**使用示例**:
```python
task = Task(task_id="test", title="Test")
state = task.get_timeout_state()
print(f"开始时间: {state.execution_start_time}")
```

---

### 3. `update_timeout_state()` - 更新超时状态

```python
def update_timeout_state(self, timeout_state: "TimeoutState") -> None:
    """Update timeout state in metadata"""
```

**功能**: 更新任务元数据中的超时状态

**参数**:
- `timeout_state` (TimeoutState): 新的超时状态

**使用示例**:
```python
from datetime import datetime, timezone

task = Task(task_id="test", title="Test")
state = task.get_timeout_state()
state.execution_start_time = datetime.now(timezone.utc).isoformat()
task.update_timeout_state(state)
```

---

## 📍 代码位置

**文件路径**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/task/models.py`

**行号范围**: 83-105 (共23行)

**插入位置**: retry 方法之后 (在 `update_retry_state()` 和 `to_dict()` 之间)

---

## ✅ 测试结果

### 测试文件
`test_timeout_methods.py` - 6个测试用例

### 测试覆盖
1. ✅ 默认超时配置
2. ✅ 从元数据读取配置
3. ✅ 默认超时状态
4. ✅ 从元数据读取状态
5. ✅ 更新超时状态
6. ✅ 与 retry 方法集成

### 测试结果
```
============================================================
✓ ALL TESTS PASSED (6/6)
============================================================
```

---

## 🔧 依赖模块

### 主要依赖

**`agentos/core/task/timeout_manager.py`** ✅

包含:
- `TimeoutConfig` 类 - 超时配置
- `TimeoutState` 类 - 超时状态
- `TimeoutManager` 类 - 超时管理器

---

## 💡 使用场景

### 场景 1: 启动超时追踪

```python
# 在 TaskRunner 中使用
from agentos.core.task.timeout_manager import TimeoutManager

task = self.task_manager.get_task(task_id)
timeout_manager = TimeoutManager()

# 获取配置和状态
timeout_config = task.get_timeout_config()
timeout_state = task.get_timeout_state()

# 启动追踪
timeout_state = timeout_manager.start_timeout_tracking(timeout_state)
task.update_timeout_state(timeout_state)
self.task_manager.update_task(task)
```

### 场景 2: 检查超时

```python
# 在 Runner 循环中检查
timeout_config = task.get_timeout_config()
timeout_state = task.get_timeout_state()

is_timeout, warning_msg, timeout_msg = timeout_manager.check_timeout(
    timeout_config,
    timeout_state
)

if is_timeout:
    # 处理超时
    logger.error(f"任务超时: {timeout_msg}")
    exit_reason = "timeout"
    self.task_manager.update_task_exit_reason(task_id, exit_reason, status="failed")
```

### 场景 3: 更新心跳

```python
# 在每次迭代更新心跳
timeout_state = task.get_timeout_state()
timeout_state = timeout_manager.update_heartbeat(timeout_state)
task.update_timeout_state(timeout_state)
```

---

## 🎨 设计特点

### 1. 懒加载导入
使用 `from agentos.core.task.timeout_manager import ...` 避免循环依赖

### 2. 默认值处理
当元数据中不存在配置时，返回默认实例而非 None，避免空指针错误

### 3. 与 Retry 方法一致
三个 timeout 方法完全镜像 retry 方法的设计:
- `get_timeout_config()` ↔ `get_retry_config()`
- `get_timeout_state()` ↔ `get_retry_state()`
- `update_timeout_state()` ↔ `update_retry_state()`

### 4. 元数据存储
所有超时信息存储在 `task.metadata` 中:
- `metadata["timeout_config"]` - 超时配置
- `metadata["timeout_state"]` - 超时状态

---

## 📝 完成清单

- [x] 读取现有 Task 类代码
- [x] 在 retry 方法后添加 3个 timeout 方法
- [x] 验证 timeout_manager.py 模块存在
- [x] 语法检查通过
- [x] 创建测试套件 (6个测试)
- [x] 所有测试通过
- [x] 验证与 retry 方法的集成
- [x] 创建实施报告
- [x] 创建快速参考指南

---

## 🚀 下一步建议

### Phase 2.3: TaskRunner 集成

1. 在 `task_runner.py` 的 `run_task()` 方法中:
   - 启动超时追踪
   - 在主循环中检查超时
   - 更新心跳
   - 处理超时事件

### 相关文档

参考 `/Users/pangge/PycharmProjects/AgentOS/状态机100%完成落地方案.md`:
- Phase 2.1: TimeoutManager 模块
- Phase 2.2: Task 模型修改 (已完成 ✅)
- Phase 2.3: TaskRunner 修改 (下一步)

---

## 📚 参考文件

### 实施报告
`TIMEOUT_METHODS_IMPLEMENTATION_REPORT.md` - 详细实施报告 (英文)

### 测试文件
`test_timeout_methods.py` - 完整测试套件

### 源代码
`agentos/core/task/models.py` - Task 类定义

### 依赖模块
`agentos/core/task/timeout_manager.py` - 超时管理模块

---

**实施完成时间**: 2026-01-29
**验收状态**: ✅ 通过
**准备集成**: ✅ 可以开始 Phase 2.3
